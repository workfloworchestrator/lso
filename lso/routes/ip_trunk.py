"""
Routes for handling events related to the IP trunk service.
"""
from os import path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl

from lso import config
from lso.playbook import PlaybookLaunchResponse, run_playbook

router = APIRouter()
config_params = config.load()


class IPTrunkProvisioningParams(BaseModel):
    callback: HttpUrl
    trunk: dict
    dry_run: Optional[bool] = True
    object: str
    verb: str


@router.post('/')
def provision_ip_trunk(params: IPTrunkProvisioningParams) \
        -> PlaybookLaunchResponse:
    """
    Launch a playbook to provision a new IP trunk service.
    The response will contain either a job ID, or error information.
    """
    extra_vars = {
        'wfo_device_json': params.trunk,
        'dry_run': str(params.dry_run),
        'verb': params.verb,
        'object': params.object
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir,
                                'playbooks/trunk.yaml'),
        inventory=[params.trunk['something']['a_side'],
                   params.trunk['somewhere']['b_side']],
        extra_vars=extra_vars,
        callback=params.callback
    )
