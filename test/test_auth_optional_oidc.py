# Copyright 2023-2026 GÉANT Vereniging.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""OIDC and OPA are an optional extra, and plain LSO must not pay for them.

The import-hygiene checks run in a fresh interpreter rather than inspecting this one. Whether `oauth2_lib`
is in `sys.modules` here depends on what the rest of the suite imported and in which order, so asserting on
it directly would prove nothing in the CI job that does install the extra.
"""

import importlib.util
import subprocess
import sys

import pytest

OAUTH2_LIB_INSTALLED = importlib.util.find_spec("oauth2_lib") is not None

needs_extra = pytest.mark.skipif(not OAUTH2_LIB_INSTALLED, reason="needs the [oidc] extra")
needs_no_extra = pytest.mark.skipif(OAUTH2_LIB_INSTALLED, reason="only meaningful without the [oidc] extra")


def run_python(source: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, check=False)  # noqa: S603


@pytest.mark.parametrize("module", ["lso.app", "lso.auth", "lso.security", "lso.config"])
def test_the_core_modules_do_not_reach_for_oauth2_lib(module: str):
    """Importing LSO must not drag in the heavier security stack, installed or not.

    A stray `import lso.oidc` anywhere in `lso` would turn the optional extra into a hard requirement
    without anything failing, because the extra is installed in most CI jobs.
    """
    result = run_python(f"import {module}, sys; assert 'oauth2_lib' not in sys.modules")

    assert result.returncode == 0, result.stderr


def test_the_application_starts_without_the_extra():
    """The default install has to be able to serve requests, which is the whole point of keeping it out."""
    result = run_python(
        "import os; os.environ['TESTING'] = 'true'\n"
        "from fastapi.testclient import TestClient\n"
        "from lso.app import create_app\n"
        "assert TestClient(create_app()).get('/api/version').status_code == 200"
    )

    assert result.returncode == 0, result.stderr


@needs_no_extra
def test_importing_the_adapter_without_the_extra_says_what_is_missing():
    """The failure has to name the package, so the fix is obvious: install `orchestrator-lso[oidc]`."""
    result = run_python("import lso.oidc")

    assert result.returncode != 0
    assert "oauth2_lib" in result.stderr
    assert "ModuleNotFoundError" in result.stderr or "ImportError" in result.stderr


@needs_extra
def test_the_adapters_satisfy_the_lso_contracts():
    from lso.auth import Authentication, Authorization  # noqa: PLC0415
    from lso.oidc import OIDCAuthentication, OPAAuthorizationAdapter  # noqa: PLC0415

    assert issubclass(OIDCAuthentication, Authentication)
    assert issubclass(OPAAuthorizationAdapter, Authorization)


@needs_extra
def test_the_adapters_delegate_to_oauth2_lib():
    """The adapter is a pass-through, apart from the user type OPA insists on.

    oauth2-lib declares the user as an `OIDCUserModel` even though it copes with `None`, so an
    unauthenticated caller becomes an empty model. It spreads into the OPA input the same way, and a real
    OIDC user arrives as an `OIDCUserModel` already, so nothing about a decision changes.
    """
    import asyncio  # noqa: PLC0415

    from oauth2_lib.fastapi import OIDCUserModel  # noqa: PLC0415

    from lso.oidc import OIDCAuthentication, OPAAuthorizationAdapter  # noqa: PLC0415

    class FakeOIDC:
        def __init__(self):
            self.calls = []

        async def authenticate(self, request, token=None):
            self.calls.append((request, token))
            return {"sub": "oidc-user"}

    class FakeOPA:
        def __init__(self):
            self.calls = []

        async def authorize(self, request, user):
            self.calls.append((request, user))
            return True

    oidc, opa = FakeOIDC(), FakeOPA()

    assert asyncio.run(OIDCAuthentication(oidc).authenticate("request", "token")) == {"sub": "oidc-user"}
    assert oidc.calls == [("request", "token")]

    adapter = OPAAuthorizationAdapter(opa)

    assert asyncio.run(adapter.authorize("request", {"sub": "u"})) is True
    assert opa.calls[-1] == ("request", {"sub": "u"})
    assert isinstance(opa.calls[-1][1], OIDCUserModel)

    assert asyncio.run(adapter.authorize("request", None)) is True
    assert opa.calls[-1][1] == {}


@needs_extra
def test_an_oidc_user_reaches_opa_unchanged():
    """A model that is already an `OIDCUserModel` must not be copied into a different object."""
    import asyncio  # noqa: PLC0415

    from oauth2_lib.fastapi import OIDCUserModel  # noqa: PLC0415

    from lso.oidc import OPAAuthorizationAdapter  # noqa: PLC0415

    class FakeOPA:
        def __init__(self):
            self.seen = None

        async def authorize(self, request, user):
            self.seen = user
            return True

    opa = FakeOPA()
    user = OIDCUserModel(sub="someone")
    asyncio.run(OPAAuthorizationAdapter(opa).authorize("request", user))

    assert opa.seen is user


@needs_extra
@pytest.mark.parametrize("active", [True, False], ids=["on", "off"])
def test_lso_switches_are_applied_to_oauth2_lib(active: bool):  # noqa: FBT001
    """`LSO_OAUTH2_ACTIVE` is the only switch, even once oauth2-lib is in play.

    oauth2-lib keeps switches of its own and bypasses when they are false, so a deployer would otherwise
    have to hold two settings in step to avoid running wide open. Copying LSO's across removes the question.
    """
    from oauth2_lib.settings import oauth2lib_settings  # noqa: PLC0415

    from lso.oidc import oidc_authentication  # noqa: PLC0415
    from test.utils import auth_settings  # noqa: PLC0415

    originals = (oauth2lib_settings.OAUTH2_ACTIVE, oauth2lib_settings.OAUTH2_AUTHORIZATION_ACTIVE)
    oauth2lib_settings.OAUTH2_ACTIVE = not active
    oauth2lib_settings.OAUTH2_AUTHORIZATION_ACTIVE = not active

    try:
        with auth_settings(active=active, authorization_active=active):
            oidc_authentication()

            assert oauth2lib_settings.OAUTH2_ACTIVE is active
            assert oauth2lib_settings.OAUTH2_AUTHORIZATION_ACTIVE is active
    finally:
        oauth2lib_settings.OAUTH2_ACTIVE, oauth2lib_settings.OAUTH2_AUTHORIZATION_ACTIVE = originals


@needs_extra
def test_a_shared_env_cannot_switch_lso_oidc_into_a_bypass():
    """The trap this closes: `OAUTH2_ACTIVE=false` in an `.env` that LSO shares with another application.

    Left alone, oauth2-lib would return `None` from every authentication, LSO would read that as "no
    opinion", and the deployment would allow everything while believing it was protected.
    """
    from oauth2_lib.settings import oauth2lib_settings  # noqa: PLC0415

    from lso.oidc import opa_authorization  # noqa: PLC0415
    from test.utils import auth_settings  # noqa: PLC0415

    originals = (oauth2lib_settings.OAUTH2_ACTIVE, oauth2lib_settings.OAUTH2_AUTHORIZATION_ACTIVE)
    oauth2lib_settings.OAUTH2_ACTIVE = False  # as another application left it

    try:
        with auth_settings(active=True, authorization_active=True):
            opa_authorization()

            assert oauth2lib_settings.OAUTH2_ACTIVE is True
    finally:
        oauth2lib_settings.OAUTH2_ACTIVE, oauth2lib_settings.OAUTH2_AUTHORIZATION_ACTIVE = originals
