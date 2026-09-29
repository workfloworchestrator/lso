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
"""Where LSO looks for the token, and how a deployment tells it to look somewhere else."""

from fastapi import status
from fastapi.testclient import TestClient

from lso.app import create_app
from lso.auth import Authentication, HttpBearerExtractor, IdTokenExtractor
from test.utils import auth_settings

VERSION_URL = "/api/version"

#: Not a credential for anything: a literal the tests compare against.
SECRET = "correct-horse-battery-staple"  # noqa: S105


class ApiKeyHeaderExtractor(IdTokenExtractor):
    """Reads the token from `X-API-Key`, and counts how often it was asked."""

    def __init__(self):
        self.calls = 0

    async def extract(self, request):
        self.calls += 1
        return request.headers.get("X-API-Key")


class RecordingAuthentication(Authentication):
    """Identifies a fixed caller, and remembers the tokens it was given."""

    def __init__(self):
        self.tokens = []

    async def authenticate(self, request, token=None):
        self.tokens.append(token)
        return {"sub": "caller"}


def test_the_default_reads_the_bearer_header():
    """An application that registers nothing keeps the behaviour it had before the extractor was pluggable."""
    assert isinstance(create_app().auth_manager.extractor, HttpBearerExtractor)


def test_registering_replaces_the_default():
    extractor = ApiKeyHeaderExtractor()
    app = create_app()
    app.register_extractor(extractor)

    assert app.auth_manager.extractor is extractor


def test_a_registered_extractor_supplies_the_token():
    """The token authentication receives comes from the registered extractor, not from `Authorization`."""
    authentication = RecordingAuthentication()
    app = create_app()
    app.register_extractor(ApiKeyHeaderExtractor())
    app.register_authentication(authentication)

    with auth_settings(active=True):
        TestClient(app).get(VERSION_URL, headers={"X-API-Key": "from-header", "Authorization": "Bearer ignored"})

    assert authentication.tokens == ["from-header"]


def test_the_extractor_does_not_run_when_authentication_is_off():
    """Off means off: nothing from the security chain touches the request."""
    extractor = ApiKeyHeaderExtractor()
    app = create_app()
    app.register_extractor(extractor)

    with auth_settings(active=False):
        response = TestClient(app).get(VERSION_URL)

    assert response.status_code == status.HTTP_200_OK
    assert extractor.calls == 0


def test_the_openapi_schema_advertises_no_security_scheme():
    """The extractor is chosen per application at runtime, so the schema cannot know where the token goes.

    Advertising a bearer scheme would be wrong for a deployment that uses another header.
    """
    assert "securitySchemes" not in create_app().openapi().get("components", {})


def test_the_shared_secret_can_arrive_in_another_header():
    """A custom extractor works with the built-in shared secret, with no custom authentication."""
    app = create_app()
    app.register_extractor(ApiKeyHeaderExtractor())

    with auth_settings(active=True, api_key=SECRET), TestClient(app) as client:
        assert client.get(VERSION_URL, headers={"X-API-Key": SECRET}).status_code == status.HTTP_200_OK
        assert client.get(VERSION_URL, headers={"X-API-Key": "wrong"}).status_code == status.HTTP_401_UNAUTHORIZED
        bearer_only = client.get(VERSION_URL, headers={"Authorization": f"Bearer {SECRET}"})
        assert bearer_only.status_code == status.HTTP_401_UNAUTHORIZED
