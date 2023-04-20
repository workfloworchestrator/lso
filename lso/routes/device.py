"""
Routes for handling device/base_config-related requests
"""
from fastapi import APIRouter
import pydantic

from lso.routes import common
from gso.products.product_types.device import DeviceBlockProvisioning

router = APIRouter()


class NodeProvisioningParams(pydantic.BaseModel):
    # TODO: define and document callback spec
    callback: pydantic.HttpUrl
    data: DeviceBlockProvisioning


@router.post('/')
async def provision_node(params: NodeProvisioningParams) \
        -> common.PlaybookLaunchResponse:
    """
    Launches a playbook to provision a new node.
    The response will contain either a job id or error information.

    :param device: NodeProvisioningParams
    :return: PlaybookLaunchResponse
    """
    device = params.data.device
    extra_vars = {
        'lo_ipv4_address': str(device.lo_ipv4_address),
        'lo_ipv6_address': str(device.lo_ipv6_address),
        'lo_iso_address': device.lo_iso_address,
        'snmp_location': device.snmp_location,
        'si_ipv4_network': str(device.si_ipv4_network),
        'lt_ipv4_network': str(device.ias_lt_ipv4_network),
        'lt_ipv6_network': str(device.ias_lt_ipv6_network),
        'site_country_code': device.site_country_code,
        'verb': 'deploy'}

    return common.run_playbook(
        playbook='base_config.yaml',
        inventory=device.fqdn,
        extra_vars=extra_vars,
        callback=params.callback)
