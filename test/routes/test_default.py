from importlib import metadata

import jsonschema
import responses
from fastapi import status
from starlette.testclient import TestClient

from lso.routes.default import API_VERSION, Version


@responses.activate
def test_ip_trunk_modification(client: TestClient) -> None:
    rv = client.get("/api/version/")
    assert rv.status_code == status.HTTP_200_OK, rv.text
    response = rv.json()

    jsonschema.validate(response, Version.model_json_schema())

    assert response["api"] == API_VERSION, response["api"]
    assert response["module"] == metadata.version("goat-lso"), response["module"]
