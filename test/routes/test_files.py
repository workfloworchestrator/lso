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
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from lso.config import settings


@pytest.fixture(autouse=True)
def job_files_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Confine `JOB_FILES_ROOT_DIR` to a fresh directory for every test in this module."""
    monkeypatch.setattr(settings, "JOB_FILES_ROOT_DIR", str(tmp_path))
    return tmp_path


def test_list_files_returns_empty_list_for_unknown_job(client: TestClient) -> None:
    job_id = uuid4()

    response = client.get(f"/api/files/{job_id}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"job_id": str(job_id), "files": []}


def test_list_files_returns_files(client: TestClient, job_files_root: Path) -> None:
    job_id = uuid4()
    job_dir = job_files_root / str(job_id)
    job_dir.mkdir()
    (job_dir / "b.txt").write_text("second")
    (job_dir / "a.txt").write_text("first")
    (job_dir / "subdir").mkdir()

    response = client.get(f"/api/files/{job_id}")

    assert response.status_code == status.HTTP_200_OK
    assert set(response.json()["files"]) == {"a.txt", "b.txt"}


def test_list_files_includes_files_in_subdirectories(client: TestClient, job_files_root: Path) -> None:
    job_id = uuid4()
    job_dir = job_files_root / str(job_id)
    (job_dir / "subdir").mkdir(parents=True)
    (job_dir / "result.txt").write_text("top-level")
    (job_dir / "subdir" / "nested.txt").write_text("nested")

    response = client.get(f"/api/files/{job_id}")

    assert response.status_code == status.HTTP_200_OK
    assert set(response.json()["files"]) == {"result.txt", "subdir/nested.txt"}


def test_download_file_returns_content(client: TestClient, job_files_root: Path) -> None:
    job_id = uuid4()
    job_dir = job_files_root / str(job_id)
    job_dir.mkdir()
    (job_dir / "result.txt").write_text("done\n")

    response = client.get(f"/api/files/{job_id}/result.txt")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == "done\n"


def test_download_file_in_subdirectory_returns_content(client: TestClient, job_files_root: Path) -> None:
    job_id = uuid4()
    job_dir = job_files_root / str(job_id)
    (job_dir / "subdir").mkdir(parents=True)
    (job_dir / "subdir" / "nested.txt").write_text("nested\n")

    response = client.get(f"/api/files/{job_id}/subdir/nested.txt")

    assert response.status_code == status.HTTP_200_OK
    assert response.text == "nested\n"


def test_download_file_rejects_escape_into_root_dir(client, job_files_root: Path) -> None:
    job_id = uuid4()
    root_dir = job_files_root
    (root_dir / "secret.txt").write_text("not yours\n")

    response = client.get(f"/api/files/{job_id}/..%2Fsecret.txt")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"detail": "Path '../secret.txt' is outside the configured root directory."}


def test_download_file_missing_returns_404(client: TestClient) -> None:
    job_id = uuid4()

    response = client.get(f"/api/files/{job_id}/does-not-exist.txt")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": f"File 'does-not-exist.txt' does not exist for job '{job_id}'"}


def test_delete_files_removes_job_dir(client: TestClient, job_files_root: Path) -> None:
    job_id = uuid4()
    job_dir = job_files_root / str(job_id)
    job_dir.mkdir()
    (job_dir / "result.txt").write_text("data")

    response = client.delete(f"/api/files/{job_id}/delete")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not job_dir.exists()

    listing = client.get(f"/api/files/{job_id}")
    assert listing.json() == {"job_id": str(job_id), "files": []}


def test_delete_files_is_a_noop_for_unknown_job(client: TestClient) -> None:
    job_id = uuid4()

    response = client.delete(f"/api/files/{job_id}/delete")

    assert response.status_code == status.HTTP_204_NO_CONTENT
