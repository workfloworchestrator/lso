"""
Routes for handling device/base_config-related requests
"""
import ipaddress
import os
from typing import Optional

from pydantic import BaseModel, HttpUrl
from fastapi import APIRouter

from lso import playbook, config

router = APIRouter()
config_params = config.load()


class InterfaceAddress(BaseModel):
    """
    Set of one IPv4 and one IPv6 address.

    :param v4: IPv4 address
    :type v4: ipaddress.IPv4Address, optional
    :param v6: IPv6 address
    :type v6: ipaddress.IPv6Address, optional
    """
    #: IPv4 address.
    v4: Optional[ipaddress.IPv4Address] = None
    #: IPv6 address.
    v6: Optional[ipaddress.IPv6Address] = None


class InterfaceNetwork(BaseModel):
    """
    Set of one IPv4 and one IPv6 subnet, should be given in CIDR notation.

    :param v4: IPv4 subnet
    :type v4: ipaddress.IPv4Network, optional
    :param v6: IPv6 subnet
    :type v6: ipaddress.IPv6Network, optional
    """
    #: IPv4 subnet.
    v4: Optional[ipaddress.IPv4Network] = None
    #: IPv6 subnet.
    v6: Optional[ipaddress.IPv6Network] = None


class NodeProvisioningParams(BaseModel):
    """
    Parameters for node provisioning

    :param callback:
    :type callback: pydantic.HttpUrl
    :param device:
    :type device: :class:`DeviceParams`
    :param dry_run:
    :type dry_run: bool, optional
    """
    #: Callback URL that is reported back to WFO, this will allow for the
    #: workflow to continue once the playbook has been executed.
    callback: HttpUrl
    #: Parameters for the new device.
    device: dict
    #: Whether this playbook execution should be a dry run, or run for real.
    #: defaults to ``True`` for obvious reasons, also making it an optional
    #: parameter.
    dry_run: Optional[bool] = True


@router.post('/')
async def provision_node(params: NodeProvisioningParams) \
        -> playbook.PlaybookLaunchResponse:
    """
    Launches a playbook to provision a new node.
    The response will contain either a job id or error information.

    :param params: Parameters for provisioning a new node
    :type params: :class:`NodeProvisioningParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`PlaybookLaunchResponse`
    """
    extra_vars = {
        'wfo_device_json': params.device,
        'dry_run': str(params.dry_run),
        'verb': 'deploy',
        'commit_comment': 'Deployed with LSO & Ansible B)'
    }

    if params.device['device_type'] == 'router':
        playbook_path = \
            os.path.join(config_params.ansible_playbooks_root_dir,
                         'playbooks/ROUTERS_PLAYBOOKS/deploy_base_config.yaml')
    else:
        raise ValueError(f'Cannot find playbook path for device type '
                         f"{params.device['device_type']}!!")

    return playbook.run_playbook(
        playbook_path=playbook_path,
        inventory=f"{params.device['device']['device_fqdn']}",
        extra_vars=extra_vars,
        callback=params.callback)
