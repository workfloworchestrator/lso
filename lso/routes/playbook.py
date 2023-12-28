"""The API endpoint from which Ansible playbooks can be executed."""

import json
import tempfile
from contextlib import redirect_stderr
from io import StringIO
from typing import Annotated, Any

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import AfterValidator, BaseModel, HttpUrl

from lso.playbook import get_playbook_path, run_playbook

router = APIRouter()


def _inventory_validator(inventory: dict[str, Any] | str) -> dict[str, Any] | str:
    """Validate the format of the provided inventory by trying to parse it.

    If an inventory cannot be parsed without warnings or errors, these are returned to the user by means of an HTTP
    status 422 for 'unprocessable entity'.
    """
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_messages)

    return inventory


PlaybookInventory = Annotated[dict[str, Any] | str, AfterValidator(_inventory_validator)]


class PlaybookRunParams(BaseModel):
    """Parameters for executing an Ansible playbook."""

    #: The filename of a playbook that is executed. It should be present inside the directory defined in the
    #: configuration option ``ansible_playbooks_root_dir``.
    playbook_name: str
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


@router.post("/")
def run_playbook_endpoint(params: PlaybookRunParams) -> JSONResponse:
    """Launch an Ansible playbook to modify or deploy a subscription instance.

    The response will contain either a job ID, or error information.

    :param PlaybookRunParams params: Parameters for executing a playbook.
    :return JSONResponse: Response from the Ansible runner, including a run ID.
    """
    return run_playbook(
        playbook_path=get_playbook_path(params.playbook_name),
        extra_vars=params.extra_vars,
        inventory=params.inventory,
        callback=params.callback,
    )
