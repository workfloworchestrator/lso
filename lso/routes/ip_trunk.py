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
    """Default parameters for an IPtrunk deployment."""
    callback: HttpUrl
    subscription: dict


class IPTrunkProvisioningParams(IPTrunkParams):
    """Additional parameters for provisioning an IPtrunk."""
    dry_run: Optional[bool] = True
    object: str


class IPTrunkModifyParams(IPTrunkParams):
    """Additional parameters for modifying an IPtrunk."""
    dry_run: Optional[bool] = True
    old_subscription: dict
    verb: str


class IPTrunkCheckParams(IPTrunkParams):
    """Additional parameters for checking an IPtrunk."""
    check_name: str


class IPTrunkDeleteParams(IPTrunkParams):
    """Additional parameters for deleting an IPtrunk."""
    dry_run: Optional[bool] = True
    verb: str


@router.post('/')
def provision_ip_trunk(params: IPTrunkProvisioningParams) \
        -> PlaybookLaunchResponse:
    """
    Launch a playbook to provision a new IP trunk service.
    The response will contain either a job ID, or error information.
    """
    extra_vars = {
        'wfo_trunk_json': params.subscription,
        'dry_run': str(params.dry_run),
        'verb': 'deploy',
        'object': params.object,
        'commit_comment': f'IPtrunk '
                          f"{params.subscription['iptrunk']['geant_s_sid']} "
                          f"({params.subscription['id']}) - "
                          f'deployment of {params.object}'
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir,
                                'iptrunks.yaml'),
        inventory=str(params.subscription['iptrunk']['iptrunk_sideA_node'][
                          'device_fqdn'] + "\n" +
                      params.subscription['iptrunk']['iptrunk_sideB_node'][
                          'device_fqdn'] + "\n"),
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
        'verb': params.verb
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir,
                                'iptrunks.yaml'),
        inventory=[params.subscription['iptrunk']['iptrunk_sideA_node'][
                       'device_fqdn'],
                   params.subscription['iptrunk']['iptrunk_sideB_node'][
                       'device_fqdn']],
        extra_vars=extra_vars,
        callback=params.callback
    )


@router.delete('/')
def delete_ip_trunk(params: IPTrunkDeleteParams) -> PlaybookLaunchResponse:
    """
    Launch a playbook that deletes an existing IP trunk service.
    """
    extra_vars = {
        'wfo_trunk_json': params.subscription,
        'dry_run': str(params.dry_run),
        'verb': params.verb,
        'config_object': "trunk_deprovision",
        'commit_comment': f'IPtrunk '
                          f"{params.subscription['iptrunk']['geant_s_sid']} "
                          f"({params.subscription['subscription_id']}) "
                          f'- termination'
    }

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir,
                                'iptrunks.yaml'),
        inventory=str(params.subscription['iptrunk']['iptrunk_sideA_node'][
                          'device_fqdn'] + "\n" +
                      params.subscription['iptrunk']['iptrunk_sideB_node'][
                          'device_fqdn'] + "\n"),
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
    }  # FIXME: needs to be updated when checks become available

    return run_playbook(
        playbook_path=path.join(config_params.ansible_playbooks_root_dir,
                                f'{params.check_name}.yaml'),
        inventory=params.subscription['iptrunk']['iptrunk_sideA_node'][
            'device_fqdn'],
        extra_vars=extra_vars,
        callback=params.callback
    )
