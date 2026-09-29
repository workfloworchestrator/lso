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
"""An LSO that was never configured for this must behave exactly as it did before."""

import os
from uuid import uuid4

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from lso.app import create_app
from lso.config import Config
from test.utils import auth_settings

JOB_ID = uuid4()

REQUESTS = [
    pytest.param("GET", "/api/version", None, id="version"),
    pytest.param("POST", "/api/playbook/", {"playbook_name": "x.yaml", "inventory": "localhost"}, id="playbook"),
    pytest.param("POST", "/api/execute/", {"executable_name": "x.sh"}, id="execute"),
    pytest.param("GET", f"/api/files/{JOB_ID}", None, id="files-list"),
    pytest.param("DELETE", f"/api/files/{JOB_ID}/delete", None, id="files-delete"),
]


def test_security_is_off_unless_asked_for():
    """The defaults are what make the upgrade a non-event."""
    defaults = Config()

    assert defaults.LSO_OAUTH2_ACTIVE is False
    assert defaults.LSO_OAUTH2_AUTHORIZATION_ACTIVE is False
    assert defaults.LSO_API_KEY is None


@pytest.mark.parametrize(("method", "url", "body"), REQUESTS)
def test_no_credentials_are_needed(method, url, body):
    """Nothing answers 401 or 403 on an unconfigured deployment."""
    with auth_settings():
        response = TestClient(create_app()).request(method, url, json=body)

    assert response.status_code not in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_an_unprefixed_switch_does_not_reach_lso(monkeypatch: pytest.MonkeyPatch):
    """`OAUTH2_ACTIVE` without the prefix must not arm LSO.

    Services in one deployment often share a single `.env`. If LSO read the unprefixed name, a value set for
    another application would make LSO demand credentials, although nobody changed LSO's configuration. The
    `LSO_` prefix is what prevents that.
    """
    monkeypatch.setenv("OAUTH2_ACTIVE", "true")
    monkeypatch.setenv("OAUTH2_AUTHORIZATION_ACTIVE", "true")

    settings = Config()

    assert settings.LSO_OAUTH2_ACTIVE is False
    assert settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE is False


def test_a_key_alone_changes_nothing():
    """Setting a secret without switching authentication on leaves the deployment open, as configured."""
    with auth_settings(active=False, api_key="s3cr3t"):
        response = TestClient(create_app()).get("/api/version")

    assert response.status_code == status.HTTP_200_OK


def test_the_application_is_still_a_fastapi_application():
    """`create_app` returns a subclass now. Anything that took the old return value still works."""
    app = create_app()

    assert isinstance(app, FastAPI)


def test_the_importable_application_still_exists():
    """`uvicorn lso.app:app`, which the example Dockerfile runs, has to keep working."""
    from lso import app as app_module  # noqa: PLC0415

    assert isinstance(app_module.app, FastAPI)


def test_the_environment_carries_no_security_settings_during_the_suite():
    """Guards the rest of this module: these assertions would be vacuous if the environment set them."""
    assert not any(name.startswith("LSO_OAUTH2") or name == "LSO_API_KEY" for name in os.environ)
