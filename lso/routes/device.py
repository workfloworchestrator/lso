"""
Routes for handling device/base_config-related requests
"""
import ipaddress
from typing import Optional

import pydantic
from fastapi import APIRouter

from lso.routes import common

router = APIRouter()


class InterfaceAddress(pydantic.BaseModel):
    v4: Optional[ipaddress.IPv4Address] = None
    v6: Optional[ipaddress.IPv6Address] = None


class InterfaceNetwork(pydantic.BaseModel):
    v4: Optional[ipaddress.IPv4Network] = None
    v6: Optional[ipaddress.IPv6Network] = None


class DeviceParams(pydantic.BaseModel):
    fqdn: str  # TODO: add some validation
    lo_address: InterfaceAddress
    lo_iso_address: str
    si_ipv4_network: ipaddress.IPv4Network
    ias_lt_network: InterfaceNetwork
    site_country_code: str
    snmp_location: str


class NodeProvisioningParams(pydantic.BaseModel):
    callback: pydantic.HttpUrl  # TODO: NAT-151
    device: DeviceParams
    ansible_host: ipaddress.IPv4Address | ipaddress.IPv6Address
    ansible_port: int


@router.post('/')
async def provision_node(params: NodeProvisioningParams) \
        -> common.PlaybookLaunchResponse:
    """
    Launches a playbook to provision a new node.
    The response will contain either a job id or error information.

    :param params: NodeProvisioningParams
    :return: PlaybookLaunchResponse
    """
    extra_vars = {
        'lo_ipv4_address': str(params.device.lo_address.v4),
        'lo_ipv6_address': str(params.device.lo_address.v6),
        'lo_iso_address': params.device.lo_iso_address,
        'snmp_location': params.device.snmp_location,
        'si_ipv4_network': str(params.device.si_ipv4_network),
        'lt_ipv4_network': str(params.device.ias_lt_network.v4),
        'lt_ipv6_network': str(params.device.ias_lt_network.v6),
        'site_country_code': params.device.site_country_code,
        'verb': 'deploy'}

    return common.run_playbook(
        playbook='base_config.yaml',
        inventory=f'{params.ansible_host}:{params.ansible_port}',
        extra_vars=extra_vars,
        callback=params.callback)
