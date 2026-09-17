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
"""The shared secret: the one implementation that works with no extra package and no code.

Most LSO deployments have a single client calling LSO. This is what makes the feature usable
there, so it is worth holding to the standards of anything else that compares a secret.
"""

import asyncio
import logging

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from lso.app import create_app
from lso.auth import Authentication, SharedSecretAuth
from lso.config import Config, settings
from test.utils import auth_settings

#: Not a credential for anything: a literal the tests compare against.
SECRET = "correct-horse-battery-staple"  # noqa: S105


def authenticate(auth: SharedSecretAuth, token):
    return asyncio.run(auth.authenticate(None, token))


def test_the_right_secret_identifies_a_caller():
    assert authenticate(SharedSecretAuth([SECRET]), SECRET) == {"sub": "api-key", "name": "shared-secret"}


def test_the_caller_is_distinguishable_from_nobody():
    """The user must not be empty or `None`.

    Authorization receives `None` when authentication is switched off. If this returned `None` too, a policy
    could not tell a caller that proved it holds the secret from a request on an unprotected deployment, and
    would have to allow both or deny both.
    """
    user = authenticate(SharedSecretAuth([SECRET]), SECRET)

    assert user
    assert user is not None


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(None, id="no-token"),
        pytest.param("", id="empty"),
        pytest.param("wrong", id="wrong"),
        pytest.param(SECRET + "x", id="right-prefix"),
        pytest.param(SECRET[:-1], id="truncated"),
        pytest.param(SECRET.upper(), id="wrong-case"),
    ],
)
def test_anything_but_the_secret_is_rejected(token):
    with pytest.raises(HTTPException) as rejection:
        authenticate(SharedSecretAuth([SECRET]), token)

    assert rejection.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_a_missing_token_looks_exactly_like_a_wrong_one():
    """Otherwise the responses tell a caller whether a secret is configured at all.

    Same status and same message either way, so probing the endpoint reveals nothing.
    """
    auth = SharedSecretAuth([SECRET])

    with pytest.raises(HTTPException) as missing:
        authenticate(auth, None)
    with pytest.raises(HTTPException) as wrong:
        authenticate(auth, "wrong")

    assert (missing.value.status_code, missing.value.detail) == (wrong.value.status_code, wrong.value.detail)


@pytest.mark.parametrize(
    "secret_values",
    [
        pytest.param([], id="none-given"),
        pytest.param([""], id="empty-string"),
        pytest.param(["", ""], id="all-empty"),
    ],
)
def test_it_refuses_to_be_built_without_a_usable_secret(secret_values):
    """An unset environment variable arriving as an empty string must never become a secret.

    Silently accepting it would produce something that looks configured and authenticates nobody, or worse,
    matches an empty token.
    """
    with pytest.raises(ValueError, match="at least one non-empty secret"):
        SharedSecretAuth(secret_values)


def test_several_secrets_are_accepted_at_once():
    """This is how a secret is rotated without downtime: run with both, move the callers, drop the old one."""
    auth = SharedSecretAuth(["old-secret", "new-secret"])

    assert authenticate(auth, "old-secret")
    assert authenticate(auth, "new-secret")


def test_empty_values_are_dropped_rather_than_accepted():
    """A blank entry alongside a real one must not become a secret that a blank token matches."""
    auth = SharedSecretAuth(["", SECRET])

    with pytest.raises(HTTPException):
        authenticate(auth, "")

    assert authenticate(auth, SECRET)


def test_the_secret_stays_out_of_the_settings_representation():
    """Held as a `SecretStr`, so it cannot reach a log line or a traceback by accident."""
    with auth_settings(active=True, api_key=SECRET):
        assert SECRET not in repr(settings)
        assert SECRET not in str(settings.LSO_API_KEY)
        assert settings.LSO_API_KEY.get_secret_value() == SECRET


def test_the_secret_stays_out_of_responses_and_logs(caplog: pytest.LogCaptureFixture):
    app = create_app()
    # `create_app()` reconfigures logging through `dictConfig`, which replaces the root handlers and throws
    # away the one pytest installed. Put it back, or every assertion below reads an empty string and an
    # assertion that the secret is absent passes without proving anything at all.
    logging.getLogger().addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG)

    with auth_settings(active=True, api_key=SECRET), TestClient(app) as client:
        allowed = client.get("/api/version", headers={"Authorization": f"Bearer {SECRET}"})
        rejected = client.get("/api/version", headers={"Authorization": "Bearer wrong"})

    # Something LSO definitely logs on this path, so the absences below are evidence rather than an artefact
    # of capturing nothing.
    assert "Registered shared-secret authentication" in caplog.text

    assert SECRET not in allowed.text
    assert SECRET not in rejected.text
    assert SECRET not in caplog.text


def test_a_configured_key_protects_the_running_application():
    """End to end, and without the deployer writing any code: two environment variables are enough."""
    app = create_app()

    with auth_settings(active=True, api_key=SECRET), TestClient(app) as client:

        def version(token: str | None) -> int:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            return client.get("/api/version", headers=headers).status_code

        assert version(None) == status.HTTP_401_UNAUTHORIZED
        assert version("nope") == status.HTTP_401_UNAUTHORIZED
        assert version(SECRET) == status.HTTP_200_OK


def test_it_is_registered_only_when_nothing_else_was():
    """An explicitly registered implementation wins. Convenience must not override an instruction."""

    class Custom(Authentication):
        async def authenticate(self, request, token=None):
            return {"sub": "custom"}

    app = create_app()
    custom = Custom()
    app.register_authentication(custom)

    with auth_settings(active=True, api_key=SECRET), TestClient(app):
        assert app.auth_manager.authentication is custom


def test_the_key_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch):
    """`LSO_API_KEY` is the documented name, so it has to be the one that binds."""
    monkeypatch.setenv("LSO_API_KEY", SECRET)

    assert Config().LSO_API_KEY.get_secret_value() == SECRET
