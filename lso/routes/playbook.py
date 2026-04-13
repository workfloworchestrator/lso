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

"""The API endpoint from which Ansible playbooks can be executed."""

import json
import tempfile
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

import ansible_runner
from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from fastapi import APIRouter, HTTPException, status
from pydantic import AfterValidator, BaseModel, HttpUrl

from lso.playbook import get_playbook_path, run_playbook

router = APIRouter()


def _inventory_validator(inventory: dict[str, Any] | str) -> dict[str, Any] | str:
    """Validate the provided inventory format.

    Attempts to parse the inventory to verify its validity.

    Args:
        inventory (dict[str, Any] | str): The inventory to validate, can be a dictionary or a string.

    Returns:
        The validated inventory, if no errors are found.

    Raises:
        HTTPException: Raises HTTP error 422 (unprocessable content) if the inventory can't be parsed or the inventory
        format is incorrect.

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
    """Validate the provided path to an Ansible playbook.

    Returns:
        A `Path` object, if the path is valid.

    Raises:
        HTTPException: Raises HTTP 410 if the file doesn't exist.

    """
    playbook_path = get_playbook_path(playbook_name)
    if not Path.exists(playbook_path):
        msg = f"Filename '{playbook_path}' does not exist."
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=msg)

    return playbook_path


PlaybookInventory = Annotated[dict[str, Any] | str, AfterValidator(_inventory_validator)]
PlaybookName = Annotated[Path, AfterValidator(_playbook_path_validator)]


class PlaybookRunResponse(BaseModel):
    """`PlaybookRunResponse` domain model schema.

    Attributes:
        job_id (UUID): The UUID generated for a Playbook execution.

    """

    job_id: UUID


class PlaybookRunParams(BaseModel):
    r"""Parameters for executing an Ansible playbook.

    Attributes:
        playbook_name (PlaybookName): The filename of a playbook that's executed. It should be present inside the
            directory defined in the configuration option ``ANSIBLE_PLAYBOOKS_ROOT_DIR``.
        callback (HttpUrl, optional): The address where LSO should call back to upon completion.
        progress (HttpUrl, optional): The address where LSO should send progress updates as the playbook executes.
        progress_is_incremental (bool, optional): Whether progress updates should be incremental or not.
        inventory (PlaybookInventory): The inventory to run the playbook against. This inventory can also include any
            host vars, if needed. When including host vars, it should be a dictionary. Can be a simple string containing
            hostnames when no host vars are needed. In the latter case, multiple hosts should be separated with a `\n`
            newline character only.
        extra_vars (dict[str, Any]): Extra variables that should get passed to the playbook.
            This includes any required configuration objects from the workflow orchestrator, commit comments, whether
            this execution should be a dry run, a trouble ticket number, etc. Which extra vars are required solely
            depends on what inputs the playbook requires.

    !!! danger "Inventory format"
        Note the fact if the collection of all hosts is a dictionary, and not a list of strings, Ansible expects each
        host to be a key-value pair. The key is the FQDN of a host, and the value always `null`. This is not the case
        when providing the inventory as a list of strings.

    ??? example
        ```JSON
        {
            "playbook_name": "hello_world.yaml",
            "callback": "https://wfo.company.cool:8080/api/resume-workflow/",
            "progress": "https://logging.awesome.yeah:8080/playbooks/",
            "progress_is_incremental": false,
            "inventory": {
                "all": {
                    "hosts": {
                        "host1.local": {
                            "foo": "bar"
                        },
                        "host2.local": {
                            "key": "value"
                        },
                        "host3.local": null
                    }
                }
            },
            "extra_vars": {
                "weather": {
                    "today": "Sunny",
                    "tomorrow": "Overcast"
                }
            }
        }
        ```

    """

    playbook_name: PlaybookName
    callback: HttpUrl | None = None
    progress: HttpUrl | None = None
    progress_is_incremental: bool = True
    inventory: PlaybookInventory
    extra_vars: dict[str, Any] = {}


@router.post("/", response_model=PlaybookRunResponse, status_code=status.HTTP_201_CREATED)
def run_playbook_endpoint(params: PlaybookRunParams) -> PlaybookRunResponse:
    """Launch an Ansible playbook to modify or deploy a subscription instance.

    The response will contain either a job ID, or error information.

    Args:
        params: Parameters for executing a playbook.

    Returns:
        Response from the Ansible runner, including a run ID.

    """
    job_id = run_playbook(
        playbook_path=params.playbook_name,
        extra_vars=params.extra_vars,
        inventory=params.inventory,
        callback=params.callback,
        progress=params.progress,
        progress_is_incremental=params.progress_is_incremental,
    )

    return PlaybookRunResponse(job_id=job_id)
