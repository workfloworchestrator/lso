# Copyright 2024-2026 GÉANT Vereniging.
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

"""Module for defining the schema for running arbitrary executables."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, model_validator


class JobStatus(StrEnum):
    """Enumeration of possible job statuses."""

    SUCCESSFUL = "successful"
    FAILED = "failed"


class ExecutionResult(BaseModel):
    """Model for capturing the result of an executable run.

    Attributes:
        output (str): Captured executable output from `stdout`.
        return_code (int): Return code of the executable.
        status (JobStatus): `SUCCESSFUL` if return code is 0, `FAILED` otherwise.

    """

    output: str
    return_code: int
    status: JobStatus

    @model_validator(mode="before")
    def populate_status(cls, values: dict) -> dict:
        """Set the status based on the return code."""
        rc = values.get("return_code")
        if rc is not None:
            values["status"] = JobStatus.SUCCESSFUL if rc == 0 else JobStatus.FAILED

        return values


class ExecutableRunResponse(BaseModel):
    """Response for running an arbitrary executable.

    Attributes:
        job_id (UUID): Unique identifier for the executable run.
        result (ExecutionResult, optional): Executable result if the request was made with `is_async` set to `False`,
            `None` otherwise.

    """

    job_id: UUID
    result: ExecutionResult | None = None
