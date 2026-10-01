# Copyright 2026 GÉANT Vereniging.
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

"""Regression tests for GHSA-q989-pw6r-9r58.

`get_executable_path` and `get_playbook_path` used to build their result by joining their configured root
directory with a caller-supplied name using `pathlib`'s `/` operator. That operator discards the root entirely
when the right-hand side is absolute, so a request naming `/bin/sh` ran `/bin/sh`. Both functions must now
reject every name that resolves outside of its root.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from nwastdlib.file_utils import SAFE_NAME_PATTERN

from lso.config import settings
from lso.execute import get_executable_path
from lso.playbook import get_playbook_path

#: Both entry points share one containment helper, so every case below is checked against both of them.
RESOLVERS = [
    pytest.param(get_executable_path, "EXECUTABLES_ROOT_DIR", id="executable"),
    pytest.param(get_playbook_path, "ANSIBLE_PLAYBOOKS_ROOT_DIR", id="playbook"),
]


@pytest.mark.parametrize(("resolver", "root_setting"), RESOLVERS)
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("/bin/sh", id="absolute-path"),
        pytest.param("../../../../bin/sh", id="parent-traversal"),
    ],
)
def test_name_resolving_outside_root_is_rejected(
    resolver: Callable[[Path], Path],
    root_setting: str,
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, root_setting, str(tmp_path))

    with pytest.raises(HTTPException) as exc:
        resolver(Path(name))

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(
    ("endpoint", "field"),
    [
        pytest.param("/api/execute/", "executable_name", id="execute"),
        pytest.param("/api/playbook/", "playbook_name", id="playbook"),
    ],
)
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("innocent;id", id="semicolon"),
        pytest.param("$(id)", id="command-substitution"),
    ],
)
def test_name_with_disallowed_characters_is_rejected(client: TestClient, endpoint: str, field: str, name: str) -> None:
    """Names are held to an allowlist of characters, declared on the field rather than checked by hand.

    Nothing reachable today turns a shell metacharacter in a name into behaviour: an executable becomes
    `argv[0]` of a subprocess started without a shell. This keeps that true should a call site ever gain one.
    Being a constraint on the shape of the request, it is a 422 like any other validation failure, not the
    400 that failing containment returns.
    """
    response = client.post(endpoint, json={field: name, "inventory": "localhost"})

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    assert "not allowed" in response.text


def test_allowlist_is_published_in_the_openapi_schema(client: TestClient) -> None:
    """The constraint is declarative, so a caller can see it without reading the source."""
    schema = client.app.openapi()["components"]["schemas"]  # ty: ignore[unresolved-attribute]

    for model, field in (("ExecutableRunParams", "executable_name"), ("PlaybookRunParams", "playbook_name")):
        assert schema[model]["properties"][field]["pattern"] == SAFE_NAME_PATTERN.pattern
