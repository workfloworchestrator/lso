import enum
import threading
# from typing import Optional

import ansible_runner
from pydantic import BaseModel


class PlaybookJobStatus(enum.StrEnum):
    OK = enum.auto()
    ERROR = enum.auto()

class PlaybookLaunchResponse(BaseModel):
    status: PlaybookJobStatus
    job_id: str = ''
    info: str = ''


def playbook_launch_success(job_id: str) -> PlaybookLaunchResponse:
    return PlaybookLaunchResponse(status=PlaybookJobStatus.OK, job_id=job_id)


def playbook_launch_error(reason: str) -> PlaybookLaunchResponse:
    return PlaybookLaunchResponse(status=PlaybookJobStatus.ERROR, info=reason)


def _run_playbook_proc(
        playbook: str,
        extra_vars: dict,
        inventory: str,
        callback: str,
        private_data_dir: str = '/opt/geant-gap-ansible',  # TODO???
):
    r = ansible_runner.run(
        private_data_dir=private_data_dir,
        playbook=playbook,
        inventory=inventory,
        extravars=extra_vars)

    # TODO: add callback logic
    output = r.stdout.read().splitlines()
    return_code = r.rc


def run_playbook(
        playbook: str,
        extra_vars: dict,
        inventory: str,
        callback: str) -> PlaybookLaunchResponse:
    t = threading.Thread(
        target=_run_playbook_proc,
        kwargs={
            'playbook': playbook,
            'inventory': inventory,
            'extra_vars': extra_vars,
            'callback': callback
        })
    t.start()

    return playbook_launch_success(job_id='1234')  # TODO: handle real id's
