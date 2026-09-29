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
"""How the request dependencies behave: what allows, what denies, and what is handed between the stages."""

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from lso.app import create_app
from lso.auth import Authentication, Authorization
from test.utils import auth_settings

VERSION_URL = "/api/version"


class RecordingAuthentication(Authentication):
    """Identifies a fixed caller, and remembers what it was asked."""

    def __init__(self, user=None, raises=None):
        self.user = user if user is not None else {"sub": "caller"}
        self.raises = raises
        self.calls = []

    async def authenticate(self, request, token=None):
        self.calls.append(token)
        if self.raises:
            raise self.raises
        return self.user


class RecordingAuthorization(Authorization):
    """Returns a fixed verdict, and remembers the user it was given."""

    def __init__(self, *, verdict=True, raises=None):
        self.verdict = verdict
        self.raises = raises
        self.seen_users = []

    async def authorize(self, request, user):
        self.seen_users.append(user)
        if self.raises:
            raise self.raises
        return self.verdict


def secured_app(authentication=None, authorization=None):
    """Build an app with these implementations registered.

    A fresh app per call. Registering on the shared `client` fixture would leave the implementation in force
    for every test that ran afterwards.
    """
    app = create_app()
    app.register_authentication(authentication or RecordingAuthentication())
    app.register_authorization(authorization or RecordingAuthorization())
    return app


@pytest.mark.parametrize(
    ("verdict", "expected_status"),
    [
        pytest.param(True, status.HTTP_200_OK, id="allowed"),
        pytest.param(False, status.HTTP_403_FORBIDDEN, id="denied"),
        pytest.param(None, status.HTTP_200_OK, id="bypassed"),
    ],
)
def test_the_verdict_decides_the_response(verdict, expected_status):
    """`True` allows, `False` denies with a 403, and `None` bypasses.

    `None` letting the request through is the part worth pinning down. It means the implementation had no
    opinion, not that it said no, so testing truthiness instead of `is False` in the dependency would turn
    every bypass into a denial without any test noticing.
    """
    with auth_settings(active=True, authorization_active=True):
        response = TestClient(secured_app(authorization=RecordingAuthorization(verdict=verdict))).get(VERSION_URL)

    assert response.status_code == expected_status


def test_a_denial_says_so():
    """The body names the reason, so a caller is not left guessing why a working request stopped working."""
    with auth_settings(active=True, authorization_active=True):
        response = TestClient(secured_app(authorization=RecordingAuthorization(verdict=False))).get(VERSION_URL)

    assert response.json()["detail"] == "Not authorized"


def test_authentication_failure_reaches_the_caller():
    """A 401 raised by the implementation is what the caller gets, not a 500."""
    rejecting = RecordingAuthentication(raises=HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated"))

    with auth_settings(active=True, authorization_active=True):
        response = TestClient(secured_app(authentication=rejecting)).get(VERSION_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"


def test_an_implementation_can_set_its_own_detail():
    """Raising `HTTPException` directly is how a policy explains itself, so it must pass through untouched."""
    fussy = RecordingAuthorization(raises=HTTPException(status.HTTP_403_FORBIDDEN, "playbooks are read-only here"))

    with auth_settings(active=True, authorization_active=True):
        response = TestClient(secured_app(authorization=fussy)).get(VERSION_URL)

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["detail"] == "playbooks are read-only here"


def test_the_authenticated_user_reaches_the_policy():
    """Authorization judges the caller authentication identified, so the two stages have to be connected."""
    user = {"sub": "someone", "groups": ["operators"]}
    policy = RecordingAuthorization()

    with auth_settings(active=True, authorization_active=True):
        TestClient(secured_app(authentication=RecordingAuthentication(user), authorization=policy)).get(VERSION_URL)

    assert policy.seen_users == [user]


def test_an_implementation_may_name_the_user_argument_differently():
    """LSO passes the user positionally, so the parameter name is the implementation's choice.

    A policy written as `authorize(self, request, user_info)` must work. If the dependency passed `user=user`
    instead, this policy would fail with a `TypeError` on every request.
    """

    class RenamedArgument(Authorization):
        async def authorize(self, request, user_info):
            return user_info["sub"] == "someone"

    def get_version(user):
        return TestClient(secured_app(RecordingAuthentication(user), RenamedArgument())).get(VERSION_URL)

    with auth_settings(active=True, authorization_active=True):
        assert get_version({"sub": "someone"}).status_code == status.HTTP_200_OK
        assert get_version({"sub": "nobody"}).status_code == status.HTTP_403_FORBIDDEN


def test_the_bearer_token_reaches_authentication():
    """The token is taken off the `Authorization` header and handed over."""
    authentication = RecordingAuthentication()

    with auth_settings(active=True):
        client = TestClient(secured_app(authentication=authentication))
        client.get(VERSION_URL, headers={"Authorization": "Bearer a-token"})

    assert authentication.calls == ["a-token"]


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-header"),
        pytest.param({"Authorization": "Basic dXNlcjpwYXNz"}, id="wrong-scheme"),
        pytest.param({"Authorization": "nonsense"}, id="malformed"),
    ],
)
def test_a_missing_or_unusable_token_is_the_implementations_decision(headers):
    """The extractor never rejects a request by itself.

    It runs with `auto_error=False` on purpose. Were it left at the default, FastAPI would reject anything
    without a bearer header before LSO's own code ran, which would break every deployment that leaves
    authentication switched off. What a missing token means is for the implementation to decide, so it must
    be reached with `None`.
    """
    authentication = RecordingAuthentication()

    with auth_settings(active=True):
        response = TestClient(secured_app(authentication=authentication)).get(VERSION_URL, headers=headers)

    assert authentication.calls == [None]
    assert response.status_code == status.HTTP_200_OK


def test_switching_authentication_off_stops_it_running():
    """The switch is honoured by the dependency, so an implementation cannot keep running after it is off.

    A custom implementation that forgets to check the switch itself would otherwise stay in force. Checking
    here makes `LSO_OAUTH2_ACTIVE=false` mean what it says whatever is registered.
    """
    authentication = RecordingAuthentication()
    authorization = RecordingAuthorization(verdict=False)

    with auth_settings(active=False, authorization_active=False):
        response = TestClient(secured_app(authentication, authorization)).get(VERSION_URL)

    assert response.status_code == status.HTTP_200_OK
    assert authentication.calls == []
    assert authorization.seen_users == []


def test_authentication_can_run_without_authorization():
    """Restricting LSO to known callers, without a per-route policy, is a legitimate configuration."""
    authentication = RecordingAuthentication()
    authorization = RecordingAuthorization(verdict=False)

    with auth_settings(active=True, authorization_active=False):
        response = TestClient(secured_app(authentication, authorization)).get(VERSION_URL)

    assert response.status_code == status.HTTP_200_OK
    assert authentication.calls == [None]
    assert authorization.seen_users == []


def test_a_denied_request_is_not_told_its_body_was_invalid():
    """Authorization runs before the body is validated, so a rejected caller learns nothing about the API.

    A 422 here would confirm which fields exist and what they must look like, to somebody who is not allowed
    to call the endpoint at all.
    """
    with auth_settings(active=True, authorization_active=True):
        client = TestClient(secured_app(authorization=RecordingAuthorization(verdict=False)))
        response = client.post("/api/execute/", json={"executable_name": 12345, "nonsense": True})

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_registering_replaces_the_default():
    """`register_authentication` and `register_authorization` are the supported way in."""
    authentication, authorization = RecordingAuthentication(), RecordingAuthorization()
    app = create_app()
    app.register_authentication(authentication)
    app.register_authorization(authorization)

    assert app.auth_manager.authentication is authentication
    assert app.auth_manager.authorization is authorization


def test_one_application_cannot_change_another():
    """The manager hangs off the application, not off the module, so tests and apps stay independent."""
    configured = secured_app(authorization=RecordingAuthorization(verdict=False))
    untouched = create_app()

    with auth_settings(active=True, authorization_active=True):
        assert TestClient(configured).get(VERSION_URL).status_code == status.HTTP_403_FORBIDDEN
        assert TestClient(untouched).get(VERSION_URL).status_code == status.HTTP_200_OK
