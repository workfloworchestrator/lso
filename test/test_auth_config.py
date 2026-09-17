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
"""What happens at startup for each combination of switches and registered implementations.

A deployment that asks for authentication and gets none would be worse than one that never asked, because
it believes it is protected. So LSO refuses to start instead of booting into a silent bypass.

The check runs in the application lifespan, which `TestClient` only executes when it is entered as a context
manager. Every test here therefore uses `with TestClient(app):`; without it these assertions would pass
while proving nothing.
"""

import logging

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from lso.app import create_app
from lso.auth import Authentication, Authorization, SharedSecretAuth
from test.utils import auth_settings


class AnyCaller(Authentication):
    async def authenticate(self, request, token=None):
        return {"sub": "caller"}


class AllowAll(Authorization):
    async def authorize(self, request, user):
        return True


def recapture(caplog: pytest.LogCaptureFixture) -> None:
    """Reinstate pytest's log capture after an app was built.

    `create_app()` calls `environment.setup_logging()`, whose `dictConfig` replaces the root handlers and so
    throws away the one `caplog` installed for this test. Without this, every assertion about a log message
    reads an empty string, and an assertion that something is *absent* would pass without proving anything.
    """
    logging.getLogger().addHandler(caplog.handler)
    caplog.set_level(logging.WARNING)


def test_an_unconfigured_application_starts():
    """The default has nothing to check, and nothing to complain about."""
    with auth_settings(), TestClient(create_app()) as client:
        assert client.get("/api/version").status_code == status.HTTP_200_OK


def test_authentication_without_an_implementation_refuses_to_start():
    """Booting here would leave a deployment that asked for authentication running with none."""
    app = create_app()

    with (
        auth_settings(active=True),
        pytest.raises(RuntimeError, match="no authentication is registered"),
        TestClient(app),
    ):
        pass


def test_the_refusal_says_how_to_fix_it():
    """Whoever hits this is mid-deployment and needs the answer, not a diagnosis."""
    app = create_app()

    with auth_settings(active=True), pytest.raises(RuntimeError) as failure, TestClient(app):
        pass

    message = str(failure.value)

    assert "LSO_API_KEY" in message
    assert "register_authentication" in message
    assert "LSO_OAUTH2_ACTIVE=false" in message


def test_authorization_without_authentication_refuses_to_start():
    """A policy with no authenticated caller to judge would see `None` every time and could not decide."""
    app = create_app()
    app.register_authorization(AllowAll())

    with (
        auth_settings(active=False, authorization_active=True),
        pytest.raises(RuntimeError, match="no authenticated"),
        TestClient(app),
    ):
        pass


def test_authorization_without_an_implementation_refuses_to_start():
    """Same reasoning as authentication: asked for, not provided, so do not pretend."""
    app = create_app()
    app.register_authentication(AnyCaller())

    with (
        auth_settings(active=True, authorization_active=True),
        pytest.raises(RuntimeError, match="no authorization is registered"),
        TestClient(app),
    ):
        pass


def test_a_fully_configured_application_starts():
    """The configuration a deployer is aiming for."""
    app = create_app()
    app.register_authentication(AnyCaller())
    app.register_authorization(AllowAll())

    with auth_settings(active=True, authorization_active=True), TestClient(app) as client:
        assert client.get("/api/version").status_code == status.HTTP_200_OK


def test_authentication_alone_starts():
    """Restricting LSO to known callers, with no per-route policy, is a supported configuration."""
    app = create_app()
    app.register_authentication(AnyCaller())

    with auth_settings(active=True, authorization_active=False), TestClient(app) as client:
        assert client.get("/api/version").status_code == status.HTTP_200_OK


def test_a_configured_key_satisfies_the_check():
    """Setting `LSO_API_KEY` is registering an implementation, so the startup check has to see it that way."""
    app = create_app()

    with auth_settings(active=True, api_key="s3cr3t"), TestClient(app):
        assert isinstance(app.auth_manager.authentication, SharedSecretAuth)


def test_registering_without_switching_on_is_called_out(caplog: pytest.LogCaptureFixture):
    """The quiet mistake: code written to enforce authentication, and a switch left at its default.

    LSO allows everything in that state, which is correct, because the switch is the authority. But somebody
    who registered an implementation plainly meant to enforce it, so leaving no trace would be unkind.
    """
    app = create_app()
    app.register_authentication(AnyCaller())
    recapture(caplog)

    with auth_settings(active=False), TestClient(app) as client:
        assert client.get("/api/version").status_code == status.HTTP_200_OK

    assert "LSO_OAUTH2_ACTIVE is false" in caplog.text
    assert "every request is allowed" in caplog.text


def test_registering_authorization_without_switching_on_is_called_out(caplog: pytest.LogCaptureFixture):
    """Same again for the policy, which can be left behind on its own when only authentication is enabled."""
    app = create_app()
    app.register_authentication(AnyCaller())
    app.register_authorization(AllowAll())
    recapture(caplog)

    with auth_settings(active=True, authorization_active=False), TestClient(app):
        pass

    assert "LSO_OAUTH2_AUTHORIZATION_ACTIVE is false" in caplog.text


def test_an_unconfigured_application_says_nothing(caplog: pytest.LogCaptureFixture):
    """No warning without a reason for one, or the warning stops meaning anything."""
    app = create_app()
    recapture(caplog)

    with auth_settings(), TestClient(app):
        pass

    assert "every request is allowed" not in caplog.text


def test_an_enforcing_application_says_nothing(caplog: pytest.LogCaptureFixture):
    """Nothing to warn about when the registered implementations are actually in use."""
    app = create_app()
    app.register_authentication(AnyCaller())
    app.register_authorization(AllowAll())
    recapture(caplog)

    with auth_settings(active=True, authorization_active=True), TestClient(app):
        pass

    assert "every request is allowed" not in caplog.text
