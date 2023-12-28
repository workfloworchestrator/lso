"""Module that gathers common API responses and data models."""

import logging
import threading
import uuid
from pathlib import Path
from typing import Any

import ansible_runner
import requests
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import HttpUrl

from lso import config
from lso.config import DEFAULT_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def get_playbook_path(playbook_name: str) -> Path:
    """Get the path of a playbook on the local filesystem."""
    config_params = config.load()
    return Path(config_params.ansible_playbooks_root_dir) / playbook_name


def playbook_launch_success(job_id: str) -> JSONResponse:
    """Return a :class:`PlaybookLaunchResponse` for the successful start of a playbook execution.

    :return JSONResponse: A playbook launch response that's successful.
    """
    return JSONResponse(content={"job_id": job_id}, status_code=status.HTTP_201_CREATED)


def playbook_launch_error(reason: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> JSONResponse:
    """Return a :class:`PlaybookLaunchResponse` for the erroneous start of a playbook execution.

    :param str reason: The reason why a request has failed.
    :param status status_code: The HTTP status code that should be associated with this request. Defaults to HTTP 400:
                               Bad request.
    :return JSONResponse: A playbook launch response that's unsuccessful.
    """
    return JSONResponse(content={"error": reason}, status_code=status_code)


def _run_playbook_proc(
    job_id: str,
    playbook_path: str,
    extra_vars: dict,
    inventory: dict[str, Any] | str,
    callback: str,
) -> None:
    """Run a playbook, internal function.

    :param str job_id: Identifier of the job that's executed.
    :param str playbook_path: Ansible playbook to be executed.
    :param dict extra_vars: Extra variables passed to the Ansible playbook.
    :param str callback: Callback URL to return output to when execution is completed.
    :param dict[str, Any] | str inventory: Ansible inventory to run the playbook against.
    """
    ansible_playbook_run = ansible_runner.run(
        playbook=playbook_path,
        inventory=inventory,
        extravars=extra_vars,
    )

    payload = {
        "status": ansible_playbook_run.status,
        "job_id": job_id,
        "output": ansible_playbook_run.stdout.readlines(),
        "return_code": int(ansible_playbook_run.rc),
    }

    request_result = requests.post(callback, json=payload, timeout=DEFAULT_REQUEST_TIMEOUT)
    if not status.HTTP_200_OK <= request_result.status_code < status.HTTP_300_MULTIPLE_CHOICES:
        msg = f"Callback failed: {request_result.text}"
        logger.error(msg)


def run_playbook(
    playbook_path: Path,
    extra_vars: dict[str, Any],
    inventory: dict[str, Any] | str,
    callback: HttpUrl,
) -> JSONResponse:
    """Run an Ansible playbook against a specified inventory.

    :param Path playbook_path: playbook to be executed.
    :param dict[str, Any] extra_vars: Any extra vars needed for the playbook to run.
    :param dict[str, Any] | str inventory: The inventory that the playbook is executed against.
    :param HttpUrl callback: Callback URL where the playbook should send a status update when execution is completed.
                             This is used for workflow-orchestrator to continue with the next step in a workflow.
    :return: Result of playbook launch, this could either be successful or unsuccessful.
    :rtype: :class:`fastapi.responses.JSONResponse`
    """
    if not Path.exists(playbook_path):
        msg = f"Filename '{playbook_path}' does not exist."
        return playbook_launch_error(reason=msg, status_code=status.HTTP_404_NOT_FOUND)

    if not ansible_runner.utils.isinventory(inventory):
        msg = "Invalid inventory provided. Should be a string, or JSON object."
        return playbook_launch_error(reason=msg, status_code=status.HTTP_400_BAD_REQUEST)

    job_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=_run_playbook_proc,
        kwargs={
            "job_id": job_id,
            "playbook_path": str(playbook_path),
            "inventory": inventory,
            "extra_vars": extra_vars,
            "callback": callback,
        },
    )
    thread.start()

    return playbook_launch_success(job_id=job_id)
