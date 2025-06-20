"""FastAPI route for running arbitrary executables."""

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from pydantic import AfterValidator, BaseModel, HttpUrl

from lso.execute import get_executable_path, run_executable_async, run_executable_sync
from lso.schema import ExecutableRunResponse

router = APIRouter()


def _executable_path_validator(executable_name: Path) -> Path:
    """Validate that the executable exists, is a file, and is marked as executable."""
    executable_path = get_executable_path(executable_name)
    if not executable_path.exists():
        msg = f"Executable '{executable_path}' does not exist."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    if not executable_path.is_file():
        msg = f"Executable '{executable_name}' is not a valid file."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    if not executable_path.stat().st_mode & 0o111:
        msg = f"Executable '{executable_name}' is not marked as executable."
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
    return executable_path


ExecutableName = Annotated[Path, AfterValidator(_executable_path_validator)]


class ExecutableRunParams(BaseModel):
    """Request parameters for running an arbitrary executable."""

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

    job_id = uuid.uuid4()
    result = run_executable_sync(str(params.executable_name), params.args)
    return ExecutableRunResponse(job_id=job_id, result=result)
