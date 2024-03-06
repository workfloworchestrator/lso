# Copyright 2023-2024 GÉANT Vereniging.
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
