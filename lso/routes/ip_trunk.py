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
    #: The address where LSO should call back to upon completion.
    callback: HttpUrl
    #: A dictionary representation of the IP trunk
    #: subscription that is to be provisioned.
    subscription: dict


class IPTrunkProvisioningParams(IPTrunkParams):
    """Additional parameters for provisioning an IPtrunk."""
    #: Whether this playbook execution should be a dry run, or run for real.
    #: defaults to ``True`` for obvious reasons, also making it an optional
    #: parameter.
    dry_run: Optional[bool] = True
    #: The type of object that is changed.
    object: str


class IPTrunkModifyParams(IPTrunkParams):
    """Additional parameters for modifying an IPtrunk."""
    #: Whether this playbook execution should be a dry run, or run for real.
    #: defaults to ``True`` for obvious reasons, also making it an optional
    #: parameter.
    dry_run: Optional[bool] = True
    #: The old subscription object, represented as a dictionary. This allows
    #: for calculating the difference in subscriptions.
    old_subscription: dict


class IPTrunkCheckParams(IPTrunkParams):
    """Additional parameters for checking an IPtrunk."""
    #: The name of the check that is to be performed.
    check_name: str


class IPTrunkDeleteParams(IPTrunkParams):
    """Additional parameters for deleting an IPtrunk."""
    #: Whether this playbook execution should be a dry run, or run for real.
    #: defaults to ``True`` for obvious reasons, also making it an optional
    #: parameter.
    dry_run: Optional[bool] = True


@router.post('/')
def provision_ip_trunk(params: IPTrunkProvisioningParams) \
        -> PlaybookLaunchResponse:
    """
    Launch a playbook to provision a new IP trunk service.
    The response will contain either a job ID, or error information.

    :param params: The parameters that define the new subscription object that
        is to be deployed.
    :type params: :class:`IPTrunkProvisioningParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {
        'wfo_trunk_json': params.subscription,
        'dry_run': str(params.dry_run),
        'verb': 'deploy',
        'config_object': params.object,
        'commit_comment': f'IPtrunk '
                          f"{params.subscription['iptrunk']['geant_s_sid']} "
                          f"({params.subscription['subscription_id']}) - "
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

    :param params: The parameters that define the change in configuration.
    :type params: :class:`IPTrunkModifyParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {
        'wfo_trunk_json': params.subscription,
        'old_wfo_trunk_json': params.old_subscription,
        'dry_run': str(params.dry_run),
        'verb': 'modify',
        'commit_comment': f'IPtrunk '
                          f"{params.subscription['iptrunk']['geant_s_sid']} "
                          f"({params.subscription['subscription_id']})"
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


@router.delete('/')
def delete_ip_trunk(params: IPTrunkDeleteParams) -> PlaybookLaunchResponse:
    """
    Launch a playbook that deletes an existing IP trunk service.

    :param params: Parameters that define the subscription that should get
        terminated.
    :type params: :class:`IPTrunkDeleteParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
    """
    extra_vars = {
        'wfo_trunk_json': params.subscription,
        'dry_run': str(params.dry_run),
        'verb': 'terminate',
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

    :param params: Parameters that define the check that is going to be
        executed, including on which relevant subscription.
    :type params: :class:`IPTrunkCheckParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`lso.playbook.PlaybookLaunchResponse`
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
