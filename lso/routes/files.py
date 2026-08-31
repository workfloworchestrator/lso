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

"""API endpoints for listing, downloading, and deleting files produced by a job."""

import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from lso.config import settings
from lso.schema import SafeName
from lso.utils import resolve_within_root

router = APIRouter()


class JobFilesResponse(BaseModel):
    """Response listing the files produced by a job.

    Attributes:
        job_id (UUID): The job whose files are listed.
        files (list[str]): Names of the files produced by the job.

    """

    job_id: UUID
    files: list[str]


def _job_dir(job_id: UUID) -> Path:
    """Resolve the directory holding a job's files, confined to `JOB_FILES_ROOT_DIR`."""
    return resolve_within_root(settings.JOB_FILES_ROOT_DIR, Path(str(job_id)))


@router.get("/{job_id}")
def list_files(job_id: UUID) -> JobFilesResponse:
    """List the files produced by a job."""
    job_dir = _job_dir(job_id)
    if not job_dir.is_dir():
        return JobFilesResponse(job_id=job_id, files=[])

    files = sorted(entry.name for entry in job_dir.iterdir() if entry.is_file())
    return JobFilesResponse(job_id=job_id, files=files)


@router.get("/{job_id}/{filename}")
def download_file(job_id: UUID, filename: SafeName) -> FileResponse:
    """Download a single file produced by a job.

    Raises:
        HTTPException: Raises a 404 if the file does not exist.

    """
    file_path = resolve_within_root(settings.JOB_FILES_ROOT_DIR, Path(str(job_id)) / filename)
    if not file_path.is_file():
        msg = f"File '{filename}' does not exist for job '{job_id}'"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    return FileResponse(file_path)


@router.delete("/{job_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_files(job_id: UUID) -> None:
    """Delete all files produced by a job."""
    job_dir = _job_dir(job_id)
    if job_dir.is_dir():
        shutil.rmtree(job_dir)
