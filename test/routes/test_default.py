from importlib import metadata

import jsonschema
import responses
from starlette.testclient import TestClient

from lso.routes.default import API_VERSION, Version


@responses.activate
def test_ip_trunk_modification(client: TestClient) -> None:
    rv = client.get("/api/version/")
    assert rv.status_code == 200
    response = rv.json()

    jsonschema.validate(response, Version.model_json_schema())

    assert response["api"] == API_VERSION
    assert response["module"] == metadata.version("goat-lso")
