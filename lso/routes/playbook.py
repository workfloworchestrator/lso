# Copyright 2023-2025 GÉANT Vereniging.
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

"""The API endpoint from which Ansible playbooks can be executed."""

import json
import tempfile
import uuid
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from typing import Annotated, Any

import ansible_runner
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from fastapi import APIRouter, HTTPException, status
from pydantic import AfterValidator, BaseModel, HttpUrl

from lso.playbook import get_playbook_path, run_playbook

router = APIRouter()


def _inventory_validator(inventory: dict[str, Any] | str) -> dict[str, Any] | str:
    """Validate the provided inventory format.

    Attempts to parse the inventory to verify its validity. If the inventory cannot be parsed or the inventory
    format is incorrect, an HTTP 422 error is raised.

    :param inventory: The inventory to validate, can be a dictionary or a string.
    :return: The validated inventory if no errors are found.
    :raises HTTPException: If parsing fails or the format is incorrect.
    """
    if not ansible_runner.utils.isinventory(inventory):
        detail = "Invalid inventory provided. Should be a string, or JSON object."
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail)

    loader = DataLoader()
    output = StringIO()
    with tempfile.NamedTemporaryFile(mode="w+") as temp_inv, redirect_stderr(output):
        json.dump(inventory, temp_inv, ensure_ascii=False)
        temp_inv.flush()

        inventory_manager = InventoryManager(loader=loader, sources=[temp_inv.name], parse=True)
        inventory_manager.parse_source(temp_inv.name)

    output.seek(0)
    error_messages = output.readlines()
    if error_messages:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=error_messages)

    return inventory


def _playbook_path_validator(playbook_name: Path) -> Path:
    playbook_path = get_playbook_path(playbook_name)
    if not Path.exists(playbook_path):
        msg = f"Filename '{playbook_path}' does not exist."
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)

    return playbook_path


PlaybookInventory = Annotated[dict[str, Any] | str, AfterValidator(_inventory_validator)]
PlaybookName = Annotated[Path, AfterValidator(_playbook_path_validator)]


class PlaybookRunResponse(BaseModel):
    """PlaybookRunResponse domain model schema."""

    job_id: uuid.UUID


class PlaybookRunParams(BaseModel):
    """Parameters for executing an Ansible playbook."""

    #: The filename of a playbook that's executed. It should be present inside the directory defined in the
    #: configuration option ``ANSIBLE_PLAYBOOKS_ROOT_DIR``.
    playbook_name: PlaybookName
    #: The address where LSO should call back to upon completion.
    callback: HttpUrl
    #: The inventory to run the playbook against. This inventory can also include any host vars, if needed. When
    #: including host vars, it should be a dictionary. Can be a simple string containing hostnames when no host vars are
    #: needed. In the latter case, multiple hosts should be separated with a ``\n`` newline character only.
    inventory: PlaybookInventory
    #: Extra variables that should get passed to the playbook. This includes any required configuration objects
    #: from the workflow orchestrator, commit comments, whether this execution should be a dry run, a trouble ticket
    #: number, etc. Which extra vars are required solely depends on what inputs the playbook requires.
    extra_vars: dict[str, Any] = {}


@router.post("/", response_model=PlaybookRunResponse, status_code=status.HTTP_201_CREATED)
def run_playbook_endpoint(params: PlaybookRunParams) -> PlaybookRunResponse:
    """Launch an Ansible playbook to modify or deploy a subscription instance.

    The response will contain either a job ID, or error information.

    :param PlaybookRunParams params: Parameters for executing a playbook.
    :return JSONResponse: Response from the Ansible runner, including a run ID.
    """
    job_id = run_playbook(
        playbook_path=params.playbook_name,
        extra_vars=params.extra_vars,
        inventory=params.inventory,
        callback=params.callback,
    )

    return PlaybookRunResponse(job_id=job_id)
