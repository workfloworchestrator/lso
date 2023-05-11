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


class IPTrunkParams(BaseModel):
    callback: HttpUrl
    subscription: dict
    verb: str


class IPTrunkProvisioningParams(IPTrunkParams):
    dry_run: Optional[bool] = True
    object: str


class IPTrunkModifyParams(IPTrunkParams):
    dry_run: Optional[bool] = True
    old_subscription: dict


class IPTrunkCheckParams(IPTrunkParams):
    check_name: str


@router.post('/')
def provision_ip_trunk(params: IPTrunkProvisioningParams) \
        -> PlaybookLaunchResponse:
    """
    Launch a playbook to provision a new IP trunk service.
    The response will contain either a job ID, or error information.
    """
    extra_vars = {
        'wfo_device_json': params.subscription,
        'dry_run': str(params.dry_run),
        'verb': params.verb,
        'object': params.object
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir,
                                'playbooks/trunk.yaml'),
        inventory=[params.subscription['something']['a_side'],
                   params.subscription['somewhere']['b_side']],
        extra_vars=extra_vars,
        callback=params.callback
    )


@router.put('/')
def modify_ip_trunk(params: IPTrunkModifyParams) -> PlaybookLaunchResponse:
    """
    Launch a playbook that modifies an existing IP trunk service.
    """
    extra_vars = {
        'wfo_ip_trunk_json': params.subscription,
        'wfo_old_ip_trunk_json': params.old_subscription,
        'dry_run': str(params.dry_run),
        'verb': params.verb,
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir,
                                f'playbooks/update_trunk.yaml'),
        inventory=[params.subscription['something']['a_side'],
                   params.subscription['somewhere']['b_side']],
        extra_vars=extra_vars,
        callback=params.callback
    )


@router.post('/perform_check')
def check_ip_trunk(params: IPTrunkCheckParams) -> PlaybookLaunchResponse:
    """
    Launch a playbook that performs a check on an IP trunk service instance.
    """
    extra_vars = {
        'wfo_ip_trunk_json': params.subscription,
        'verb': params.verb
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir,
                                f'playbooks/{params.check_name}.yaml'),
        inventory=[params.subscription['something']['a_side'],
                   params.subscription['somewhere']['b_side']],
        extra_vars=extra_vars,
        callback=params.callback
    )
