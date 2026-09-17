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
"""Every router goes through the policy, and the policy is told enough to treat them differently.

`/api/execute/` and `/api/playbook/` run code on the host, `/api/files/` reads and deletes from disk, and
`/api/version` reports a version number. They do not carry equal risk, so a deployer has to be able to tell
them apart without LSO having to change any endpoint.
"""

from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from lso.app import create_app
from lso.auth import Authentication, Authorization
from test.utils import auth_settings

JOB_ID = uuid4()

#: One request per router, plus the two file operations that change or disclose something on disk.
REQUESTS = [
    pytest.param("GET", "/api/version", None, id="version"),
    pytest.param("POST", "/api/playbook/", {"playbook_name": "x.yaml", "inventory": "localhost"}, id="playbook"),
    pytest.param("POST", "/api/execute/", {"executable_name": "x.sh"}, id="execute"),
    pytest.param("GET", f"/api/files/{JOB_ID}", None, id="files-list"),
    pytest.param("GET", f"/api/files/{JOB_ID}/output.txt", None, id="files-download"),
    pytest.param("DELETE", f"/api/files/{JOB_ID}/delete", None, id="files-delete"),
]


class AnyCaller(Authentication):
    """Identifies every request as the same caller, so these tests are about authorization alone."""

    async def authenticate(self, request, token=None):
        return {"sub": "caller"}


class FixedVerdict(Authorization):
    """Answers every request the same way."""

    def __init__(self, *, verdict):
        self.verdict = verdict

    async def authorize(self, request, user):
        return self.verdict


class RecordingPolicy(Authorization):
    """Allows everything, and records what it was told about each request."""

    def __init__(self):
        self.seen = []

    async def authorize(self, request, user):
        self.seen.append((request.method, request.url.path, dict(request.path_params), dict(request.query_params)))
        return True


def app_with(*, verdict):
    app = create_app()
    app.register_authentication(AnyCaller())
    app.register_authorization(FixedVerdict(verdict=verdict))
    return app


@pytest.mark.parametrize(("method", "url", "body"), REQUESTS)
def test_every_route_can_be_denied(method, url, body):
    """A policy reaches every endpoint, including the file operations added after this was first designed."""
    with auth_settings(active=True, authorization_active=True):
        response = TestClient(app_with(verdict=False)).request(method, url, json=body)

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize(("method", "url", "body"), REQUESTS)
@pytest.mark.parametrize("verdict", [True, None], ids=["allowed", "bypassed"])
def test_allowing_leaves_the_endpoint_exactly_as_it_was(method, url, body, verdict):
    """An allowed or bypassed request gets the same answer an unconfigured LSO would have given.

    Comparing against that baseline, rather than against a hard-coded status, is what shows the dependency
    changes nothing about the endpoint itself: whether the response is a success, a 422 or a 404, it is
    unchanged.
    """
    with auth_settings(active=False, authorization_active=False):
        baseline = TestClient(create_app()).request(method, url, json=body)

    with auth_settings(active=True, authorization_active=True):
        secured = TestClient(app_with(verdict=verdict)).request(method, url, json=body)

    assert secured.status_code == baseline.status_code


def test_a_policy_can_treat_the_risky_endpoints_differently():
    """The point of the feature: reading a version number is not running a playbook."""

    class ReadOnly(Authorization):
        async def authorize(self, request, user):
            return not request.url.path.startswith(("/api/execute", "/api/playbook"))

    app = create_app()
    app.register_authentication(AnyCaller())
    app.register_authorization(ReadOnly())

    with auth_settings(active=True, authorization_active=True):
        client = TestClient(app)

        assert client.get("/api/version").status_code == status.HTTP_200_OK
        assert client.get(f"/api/files/{JOB_ID}").status_code == status.HTTP_200_OK
        assert client.post("/api/execute/", json={}).status_code == status.HTTP_403_FORBIDDEN
        assert client.post("/api/playbook/", json={}).status_code == status.HTTP_403_FORBIDDEN


def test_the_policy_is_told_enough_to_decide():
    """Method, path, path parameters and query string all reach the policy.

    Without the path parameters a policy could not, for example, restrict a caller to its own jobs.
    """
    policy = RecordingPolicy()
    app = create_app()
    app.register_authentication(AnyCaller())
    app.register_authorization(policy)

    with auth_settings(active=True, authorization_active=True):
        TestClient(app).get(f"/api/files/{JOB_ID}?verbose=1")

    method, path, path_params, query_params = policy.seen[0]

    assert method == "GET"
    assert path == f"/api/files/{JOB_ID}"
    assert path_params == {"job_id": str(JOB_ID)}
    assert query_params == {"verbose": "1"}


def test_a_policy_may_read_the_request_body():
    """Reading the body to decide does not stop the endpoint parsing it afterwards.

    A policy that has to look at which playbook is being run needs the body, and FastAPI keeps it available
    once read, so doing so must not break the endpoint behind it.
    """

    class InspectsBody(Authorization):
        def __init__(self):
            self.seen = []

        async def authorize(self, request, user):
            self.seen.append(await request.json())
            return True

    policy = InspectsBody()
    app = create_app()
    app.register_authentication(AnyCaller())
    app.register_authorization(policy)
    body = {"executable_name": "nonexistent.sh"}

    with auth_settings(active=False, authorization_active=False):
        baseline = TestClient(create_app()).post("/api/execute/", json=body)

    with auth_settings(active=True, authorization_active=True):
        response = TestClient(app).post("/api/execute/", json=body)

    assert policy.seen == [body]
    assert response.status_code == baseline.status_code


@pytest.mark.parametrize("url", ["/api/doc", "/api/redoc", "/api/openapi.json"])
def test_the_documentation_endpoints_stay_public(url):
    """Accepted behaviour, pinned here so that changing it is a deliberate act rather than an accident.

    FastAPI serves these itself, outside the dependency system, so a router dependency cannot reach them.
    That is not a gap waiting to be closed: LSO's API schema is published with the project, so a caller who
    reads it learns nothing they could not read on the project website.
    """
    with auth_settings(active=True, authorization_active=True):
        response = TestClient(app_with(verdict=False)).get(url)

    assert response.status_code == status.HTTP_200_OK
