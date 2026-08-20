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

from lso.config import settings
from lso.execute import get_executable_path
from lso.playbook import get_playbook_path
from lso.schema import SAFE_NAME_PATTERN

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
        pytest.param("/etc/passwd", id="absolute-path-to-unrelated-file"),
        pytest.param("../../../../bin/sh", id="parent-traversal"),
        pytest.param("nested/../../../bin/sh", id="traversal-through-subdirectory"),
        # Rejecting this with a 400 rather than a 404/410 is what keeps the endpoints from reporting whether an
        # arbitrary path exists: containment has to be decided before the path is ever inspected.
        pytest.param("/nonexistent-a1b2c3/nope", id="absolute-path-that-does-not-exist"),
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
        pytest.param("innocent id", id="space"),
        pytest.param("innocent|id", id="pipe"),
        pytest.param("$(id)", id="command-substitution"),
        pytest.param("`id`", id="backticks"),
        pytest.param("innocent\nid", id="newline"),
        pytest.param("innocent&id", id="ampersand"),
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


@pytest.mark.parametrize(("resolver", "root_setting"), RESOLVERS)
@pytest.mark.parametrize(
    "name",
    [
        pytest.param("deploy.yaml", id="plain"),
        pytest.param("deploy_node-v2.yaml", id="underscore-and-hyphen"),
        pytest.param("nested/deploy.yaml", id="subdirectory"),
    ],
)
def test_ordinary_names_are_accepted(
    resolver: Callable[[Path], Path],
    root_setting: str,
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The allowlist must not reject the names deployments actually use."""
    monkeypatch.setattr(settings, root_setting, str(tmp_path))

    assert resolver(Path(name)) == tmp_path.resolve() / name


@pytest.mark.parametrize(("resolver", "root_setting"), RESOLVERS)
def test_symlink_pointing_out_of_root_is_rejected(
    resolver: Callable[[Path], Path],
    root_setting: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.sh"
    outside.touch()
    (root / "innocent.sh").symlink_to(outside)
    monkeypatch.setattr(settings, root_setting, str(root))

    with pytest.raises(HTTPException) as exc:
        resolver(Path("innocent.sh"))

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.parametrize(("resolver", "root_setting"), RESOLVERS)
def test_symlinked_root_still_accepts_contained_name(
    resolver: Callable[[Path], Path],
    root_setting: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A root directory that is itself a symlink must not reject names that genuinely sit inside it.

    Containment is decided between two resolved paths. Comparing a resolved candidate against an unresolved
    root would reject every legitimate request as soon as the root, or any of its parents, is a symlink --
    routine in a container, and the case for temporary directories on macOS.
    """
    real_root = tmp_path / "real"
    real_root.mkdir()
    (real_root / "hello.sh").touch()
    linked_root = tmp_path / "linked"
    linked_root.symlink_to(real_root, target_is_directory=True)
    monkeypatch.setattr(settings, root_setting, str(linked_root))

    assert resolver(Path("hello.sh")) == real_root.resolve() / "hello.sh"
