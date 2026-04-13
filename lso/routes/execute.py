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

"""FastAPI route for running arbitrary executables."""

import asyncio
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import AfterValidator, BaseModel, HttpUrl

from lso.execute import get_executable_path, run_executable_async, run_executable_sync
from lso.schema import ExecutableRunResponse

router = APIRouter()


def _executable_path_validator(executable_name: Path) -> Path:
    """Validate that the executable exists, is a file, and is marked as executable.

    Returns:
        A Path object that points to the executable.

    Raises:
        HTTPException: Raises a 410 if the requested executable does not exist.
        HTTPException: Raises a 503 if the executable is not a valid file.
        HTTPException: Raises a 403 if the file is not marked as executable by the OS.

    """
    executable_path = get_executable_path(executable_name)
    if not executable_path.exists():
        msg = f"Executable '{executable_path}' does not exist."
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=msg)
    if not executable_path.is_file():
        msg = f"Executable '{executable_name}' is not a valid file."
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=msg)
    if not executable_path.stat().st_mode & 0o111:
        msg = f"Executable '{executable_name}' is not marked as executable."
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
    return executable_path


ExecutableName = Annotated[Path, AfterValidator(_executable_path_validator)]


class ExecutableRunParams(BaseModel):
    """Request parameters for running an arbitrary executable.

    Attributes:
        executable_name (ExecutableName): The absolute path to the executable.
        args (list[str], optional): A list of arguments that is provided to the script.
        callback (HttpUrl, optional): A callback URL where the execution result of the script is posted to.
        is_async (bool, optional): Whether this script should be executed asynchronously.

    """

    executable_name: ExecutableName
    args: list[str] = []
    callback: HttpUrl | None = None
    is_async: bool = True


@router.post("/", response_model=ExecutableRunResponse, status_code=status.HTTP_201_CREATED)
async def run_executable_endpoint(params: ExecutableRunParams) -> ExecutableRunResponse:
    """Dispatch a task to run an arbitrary executable."""
    if params.is_async:
        job_id = run_executable_async(params.executable_name, params.args, params.callback)
        return ExecutableRunResponse(job_id=job_id)

    job_id = uuid4()
    result = await asyncio.to_thread(run_executable_sync, str(params.executable_name), params.args)
    return ExecutableRunResponse(job_id=job_id, result=result)
