import threading
from typing import Optional

import ansible_runner
from pydantic import BaseModel


class PlaybookLaunchResponse(BaseModel):
    status: str  # always 'OK' or 'ERROR'
    job_id: Optional[str] = None  # only if 'OK'
    info: Optional[str] = None  # only if 'ERROR'


def playbook_launch_success(job_id: str) -> PlaybookLaunchResponse:
    return PlaybookLaunchResponse(status='OK', job_id=job_id)


def playbook_launch_error(reason: str) -> PlaybookLaunchResponse:
    return PlaybookLaunchResponse(status='ERROR', info=reason)


# TODO: add callback logic
def _run_playbook_proc(
        playbook: str,
        extra_vars: dict,
        inventory: str,
        private_data_dir: str = '/opt/geant-gap-ansible',  # TODO
):
    r = ansible_runner.run(
        private_data_dir=private_data_dir,
        playbook=playbook,
        inventory=inventory,
        extravars=extra_vars)

    return {"dry_run_output": r.stdout.read().splitlines(), "return_code": r.rc}


def run_playbook(
        playbook: str,
        extra_vars: dict,
        inventory: str) -> PlaybookLaunchResponse:
    t = threading.Thread(
        target=_run_playbook_proc,
        kwargs={
            'playbook': playbook,
            'inventory': inventory,
            'extra_vars': extra_vars
        })
    t.start()

    return PlaybookLaunchResponse(status='OK', job_id='1234')  # TODO: handle real id's
