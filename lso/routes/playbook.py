"""The API endpoint from which Ansible playbooks can be executed."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from lso.playbook import get_playbook_path, run_playbook

router = APIRouter()


class PlaybookRunParams(BaseModel):
    """Parameters for executing an Ansible playbook."""

    #: The filename of a playbook that is executed. It should be present inside the directory defined in the
    #: configuration option ``ansible_playbooks_root_dir``.
    playbook_name: str
    #: The address where LSO should call back to upon completion.
    callback: HttpUrl
    #: The inventory to run the playbook against. This inventory can also include any host vars, if needed. When
    #: including host vars, it should be a dictionary. Can be a simple string containing hostnames when no host vars are
    #: needed. In the latter case, multiple hosts should be separated with a newline character.
    inventory: dict[str, Any] | str
    #: Extra variables that should get passed to the playbook. This includes any required configuration objects
    #: from the workflow orchestrator, commit comments, whether this execution should be a dry run, a trouble ticket
    #: number, etc. Which extra vars are required solely depends on what inputs the playbook requires.
    extra_vars: dict


@router.post("/")
def run_playbook_endpoint(params: PlaybookRunParams) -> JSONResponse:
    """Launch an Ansible playbook to modify or deploy a subscription instance.

    The response will contain either a job ID, or error information.

    :param params :class:`PlaybookRunParams`: Parameters for executing a playbook.
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`fastapi.responses.JSONResponse`
    """
    return run_playbook(
        playbook_path=get_playbook_path(params.playbook_name),
        extra_vars=params.extra_vars,
        inventory=params.inventory,
        callback=params.callback,
    )
