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
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class JobStatus(StrEnum):
    """Enumeration of possible job statuses."""

    SUCCESSFUL = "successful"
    FAILED = "failed"


class InventoryValidationReason(StrEnum):
    """Why a submitted inventory was rejected.

    These values are derived from what Ansible managed to parse, never from the wording of its output, so they stay
    stable across Ansible versions.

    Attributes:
        NOT_A_MAPPING: The inventory was neither a JSON object nor a string. A request that gets this far has
            already been screened by the request schema, which rejects those types with its own 422, so callers
            should not expect to see this value; it guards against the validator being called directly.
        UNPARSABLE: Ansible could not parse the inventory at all, and understood no hosts. Returned with a 422.
        REJECTED_WITH_WARNINGS: Ansible parsed some hosts, but reported problems while doing so. Returned with
            a 422.
        VALIDATOR_UNAVAILABLE: The `ansible-inventory` command is not installed on this machine. A deployment
            problem rather than bad client input, so it is returned with a 503; the inventory itself may be fine.
        TIMEOUT: Validation did not finish within `INVENTORY_VALIDATION_TIMEOUT_SEC`. Returned with a 504.

    """

    NOT_A_MAPPING = "not_a_mapping"
    UNPARSABLE = "unparsable"
    REJECTED_WITH_WARNINGS = "rejected_with_warnings"
    VALIDATOR_UNAVAILABLE = "validator_unavailable"
    TIMEOUT = "timeout"


class InventoryProblem(BaseModel):
    """Body of the error response returned when an inventory fails validation.

    Sent with a 422 when the inventory itself is at fault, a 503 when the validator is not installed, and a 504
    when validation timed out.

    Attributes:
        error (str): Constant discriminator, so a caller can tell this body apart from other error responses.
        reason (InventoryValidationReason): Machine-readable cause. This is the part callers should branch on.
        messages (list[str]): Ansible's own diagnostics, for a human to read. The wording depends on the installed
            Ansible version and is deliberately not part of the API contract.
        parsed_groups (list[str]): Groups Ansible understood, if any.
        parsed_hosts (list[str]): Hosts Ansible understood, if any. Useful for spotting an inventory that parses
            into something other than what was intended.

    """

    error: Literal["invalid_inventory"] = "invalid_inventory"
    reason: InventoryValidationReason
    messages: list[str] = Field(default_factory=list)
    parsed_groups: list[str] = Field(default_factory=list)
    parsed_hosts: list[str] = Field(default_factory=list)


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
