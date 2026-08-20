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

import re
from enum import StrEnum
from pathlib import Path
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, Field, model_validator

#: Characters a caller-supplied executable or playbook name may consist of. Such a name is only ever used as a
#: filesystem path, and for an executable as `argv[0]` of a subprocess started without a shell, so a shell
#: metacharacter in one cannot currently do anything. This allowlist keeps that true should a call site ever
#: gain a shell, and costs nothing today: ordinary names are already within it.
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")


def _reject_unsafe_name(value: str) -> str:
    """Reject a name holding characters outside `SAFE_NAME_PATTERN`.

    Raises:
        ValueError: If the name holds any other character. Pydantic turns this into the usual 422, rather
            than the 400 that the containment check raises, because this is a constraint on the shape of the
            request and not a judgement that needs the filesystem.

    """
    if not SAFE_NAME_PATTERN.match(str(value)):
        msg = f"Name '{value}' contains characters that are not allowed."
        raise ValueError(msg)

    return value


#: A file name supplied by the caller, constrained to `SAFE_NAME_PATTERN`. The constraint is declared on the
#: field so that it lands in the OpenAPI schema, while the annotated type stays `Path`. Containment within
#: the configured root directory is a separate check: it needs the filesystem, so it cannot be a pattern.
SafeName = Annotated[
    Path, BeforeValidator(_reject_unsafe_name), Field(json_schema_extra={"pattern": SAFE_NAME_PATTERN.pattern})
]


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
    status: JobStatus | None = None

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
