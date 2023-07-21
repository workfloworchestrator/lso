"""Module that gathers common API responses and data models."""
import enum
import json
import logging
import threading
import uuid

import ansible_runner
import requests
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)


# enum.StrEnum is only available in python 3.11
class PlaybookJobStatus(str, enum.Enum):
    """Enumerator for status codes of a playbook job that's running."""

    #: All is well.
    OK = "ok"
    #: An error has occurred.
    ERROR = "error"


class PlaybookLaunchResponse(BaseModel):
    """Running a playbook gives this response.

    :param PlaybookJobStatus status:
    :param job_id:
    :type job_id: str, optional
    :param info:
    :type info: str, optional
    """

    #: Status of a Playbook job.
    status: PlaybookJobStatus
    #: The ID assigned to a job.
    job_id: str = ""
    #: Information on a job.
    info: str = ""


def playbook_launch_success(job_id: str) -> PlaybookLaunchResponse:
    """Return a :class:`PlaybookLaunchResponse` for the successful start of a playbook execution.

    :return PlaybookLaunchResponse: A playbook launch response that's
        successful.
    """
    return PlaybookLaunchResponse(status=PlaybookJobStatus.OK, job_id=job_id)


def playbook_launch_error(reason: str) -> PlaybookLaunchResponse:
    """Return a :class:`PlaybookLaunchResponse` for the erroneous start of a playbook execution.

    :return PlaybookLaunchResponse: A playbook launch response that's
        unsuccessful.
    """
    return PlaybookLaunchResponse(status=PlaybookJobStatus.ERROR, info=reason)


def _run_playbook_proc(job_id: str, playbook_path: str, extra_vars: dict, inventory: list[str], callback: str) -> None:
    """Run a playbook, internal function.

    :param str job_id: Identifier of the job that's executed.
    :param str playbook_path: Ansible playbook to be executed.
    :param dict extra_vars: Extra variables passed to the Ansible playbook.
    :param str callback: Callback URL to PUT to when execution is completed.
    :param [str] inventory: Ansible inventory to run the playbook against.
    """
    ansible_playbook_run = ansible_runner.run(
        playbook=playbook_path,
        inventory=inventory,
        extravars=extra_vars,
        json_mode=True,
    )

    # Process playbook JSON stdout
    json_output = ansible_playbook_run.stdout
    json_content = json_output.read()

    parsed_output = []
    for line in json_content.strip().splitlines():
        try:
            task_output = json.loads(line)
            task_output.pop("stdout", None)
            parsed_output.append(task_output)
        except json.JSONDecodeError:
            parsed_output.append({"invalid_json": line})

    payload = [
        {
            "pp_run_results": {
                "status": ansible_playbook_run.status,
                "job_id": job_id,
                "output": parsed_output,
                "return_code": int(ansible_playbook_run.rc),
            },
            "confirm": "ACCEPTED",
        }
    ]

    request_result = requests.put(callback, json=payload, timeout=10000)
    assert request_result.status_code == 204


def run_playbook(playbook_path: str, extra_vars: dict, inventory: str, callback: HttpUrl) -> PlaybookLaunchResponse:
    """Run an Ansible playbook against a specified inventory.

    :param str playbook_path: playbook to be executed.
    :param dict extra_vars: Any extra vars needed for the playbook to run.
    :param [str] inventory: The inventory that the playbook is executed
                            against.
    :param :class:`HttpUrl` callback: Callback URL where the playbook should send a status
        update when execution is completed. This is used for
        workflow-orchestrator to continue with the next step in a workflow.
    :return: Result of playbook launch, this could either be successful or
        unsuccessful.
    :rtype: :class:`PlaybookLaunchResponse`
    """

    job_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=_run_playbook_proc,
        kwargs={
            "job_id": job_id,
            "playbook_path": playbook_path,
            "inventory": inventory,
            "extra_vars": extra_vars,
            "callback": callback,
        },
    )
    thread.start()

    return playbook_launch_success(job_id=job_id)
