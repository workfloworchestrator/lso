"""
Module that gathers common API responses and data models.
"""
import enum
import logging
import threading
import uuid

import ansible_runner
import requests
from pydantic import BaseModel

from lso import config

logger = logging.getLogger(__name__)


# enum.StrEnum is only available in python 3.11
class PlaybookJobStatus(str, enum.Enum):
    """
    Enumerator for status codes of a playbook job that is running.
    """
    #: All is well.
    OK = 'ok'
    #: We're not OK.
    ERROR = 'error'


class PlaybookLaunchResponse(BaseModel):
    """
    Running a playbook gives this response.

    :param PlaybookJobStatus status:
    :param job_id:
    :type job_id: str, optional
    :param info:
    :type info: str, optional
    """
    #: Status of a Playbook job.
    status: PlaybookJobStatus
    #: The ID assigned to a job.
    job_id: str = ''
    #: Information on a job.
    info: str = ''


def playbook_launch_success(job_id: str) -> PlaybookLaunchResponse:
    """
    Return a :class:`PlaybookLaunchResponse` for the successful start of a
    playbook execution.

    :return PlaybookLaunchResponse: A playbook launch response that is
        successful.
    """
    return PlaybookLaunchResponse(status=PlaybookJobStatus.OK, job_id=job_id)


def playbook_launch_error(reason: str) -> PlaybookLaunchResponse:
    """
    Return a :class:`PlaybookLaunchResponse` for the erroneous start of a
    playbook execution.

    :return PlaybookLaunchResponse: A playbook launch response that is
        unsuccessful.
    """
    return PlaybookLaunchResponse(status=PlaybookJobStatus.ERROR, info=reason)


def _run_playbook_proc(
        job_id: str,
        playbook: str,
        extra_vars: dict,
        inventory: str,
        callback: str
):
    """
    Internal function for running a playbook.

    :param str job_id: Identifier of the job that is executed.
    :param str playbook: Name of a playbook.
    :param dict extra_vars: Extra variables passed to the Ansible playbook
    :param str callback: Callback URL to POST to when execution is completed.
    """

    ansible_playbook_run = ansible_runner.run(
        private_data_dir=config.load().get('ansible_private_data_dir', None),
        playbook=playbook,
        inventory=inventory,
        extravars=extra_vars)

    # TODO: add callback logic, this is just a placeholder
    # TODO: NAT-151
    payload = {
        'job_id': job_id,
        'output': str(ansible_playbook_run.stdout.read()),
        'return_code': int(ansible_playbook_run.rc)
    }
    requests.post(callback, json=payload, timeout=10000)


def run_playbook(
        playbook: str,
        extra_vars: dict,
        inventory: str,
        callback: str) -> PlaybookLaunchResponse:
    """
    Run an Ansible playbook against a specified inventory.

    :param str playbook: name of the playbook that is executed.
    :param dict extra_vars: Any extra vars needed for the playbook to run.
    :param str inventory: The inventory that the playbook is executed against.
    :param str callback: Callback URL where the playbook should send a status
        update when execution is completed. This is used for WFO to continue
        with the next step in a workflow.
    :return: Result of playbook launch, this could either be successful or
        unsuccessful.
    :rtype: :class:`PlaybookLaunchResponse`
    """

    job_id = str(uuid.uuid4())
    thread = threading.Thread(
        target=_run_playbook_proc,
        kwargs={
            'job_id': job_id,
            'playbook': playbook,
            'inventory': inventory,
            'extra_vars': extra_vars,
            'callback': callback
        })
    thread.start()

    return playbook_launch_success(job_id=job_id)  # TODO: handle real id's
