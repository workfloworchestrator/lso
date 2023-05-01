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


class InterfaceNetwork(pydantic.BaseModel):
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


class DeviceParams(pydantic.BaseModel):
    """
    Parameters of an API call that deploys a new device in the network.
    This device can either be a router or a switch, from the different vendors
    that are supported.

    :param fqdn:
    :type fqdn: str
    :param lo_address:
    :type lo_address: :class:`InterfaceAddress`
    :param lo_iso_address:
    :type lo_iso_address: str
    :param si_ipv4_network:
    :type si_ipv4_network: ipaddress.IPv4Network
    :param ias_lt_network:
    :type ias_lt_network: :class:`InterfaceNetwork`
    :param site_country_code:
    :type site_country_code: str
    :param site_city:
    :type site_city: str
    :param site_latitude:
    :type site_latitude: str
    :type site_longitude:
    :type site_longitude: str
    :param device_type:
    :type device_type: str
    :param device_vendor:
    :type device_vendor: str
    """
    #: FQDN of a device, TODO: add some validation
    fqdn: str
    #: Loopback interface address of a device, should be an
    #: :class:`InterfaceAddress` object.
    lo_address: InterfaceAddress
    #: Loopback ISO address.
    lo_iso_address: str
    #: SI IPv4 network, as an `ipaddress.IPv4Network`.
    si_ipv4_network: ipaddress.IPv4Network
    #: IAS LT network, stored as an :class:`InterfaceNetwork`.
    ias_lt_network: InterfaceNetwork
    #: Country code where the device is located.
    site_country_code: str
    #: City where the device is located.
    site_city: str
    #: Latitude of the device site.
    site_latitude: str
    #: Longitude of the device site.
    site_longitude: str
    #: Type of device, either ``router`` or ``switch``.
    device_type: str
    #: The device vendor, for specific configuration.
    device_vendor: str


class NodeProvisioningParams(pydantic.BaseModel):
    """
    Parameters for node provisioning

    :param callback:
    :type callback: pydantic.HttpUrl
    :param device:
    :type device: :class:`DeviceParams`
    :param ansible_host:
    :type ansible_host: ipaddress.IPv4Address or ipaddress.IPv6Address
    :param ansible_port:
    :type ansible_port: int
    :param dry_run:
    :type dry_run: bool, optional
    """
    #: Callback URL that is reported back to WFO, this will allow for the
    #: workflow to continue once the playbook has been executed.
    callback: pydantic.HttpUrl  # TODO: NAT-151
    #: Parameters for the new device.
    device: DeviceParams
    #: Host address that ansible should point to, most likely a terminal
    #: server.
    ansible_host: ipaddress.IPv4Address | ipaddress.IPv6Address
    #: Similar to the ``ansible_host``, but for a port number.
    ansible_port: int
    #: Whether this playbook execution should be a dry run, or run for real.
    #: defaults to ``True`` for obvious reasons, also making it an optional
    #: parameter.
    dry_run: Optional[bool] = True


@router.post('/')
async def provision_node(params: NodeProvisioningParams) \
        -> common.PlaybookLaunchResponse:
    """
    Launches a playbook to provision a new node.
    The response will contain either a job id or error information.

    :param params: Parameters for provisioning a new node
    :type params: :class:`NodeProvisioningParams`
    :return: Response from the Ansible runner, including a run ID.
    :rtype: :class:`PlaybookLaunchResponse`
    """
    extra_vars = {
        'lo_ipv4_address': str(params.device.lo_address.v4),
        'lo_ipv6_address': str(params.device.lo_address.v6),
        'lo_iso_address': params.device.lo_iso_address,
        'si_ipv4_network': str(params.device.si_ipv4_network),
        'ias_lt_ipv4_network': str(params.device.ias_lt_network.v4),
        'ias_lt_ipv6_network': str(params.device.ias_lt_network.v6),
        'site_country_code': params.device.site_country_code,
        'snmp_location': f'{params.device.site_city},'
                         f'{params.device.site_country_code}'
                         f'[{params.device.site_latitude},'
                         f'{params.device.site_longitude}]',
        'site_city': params.device.site_city,
        'site_latitude': params.device.site_latitude,
        'site_longitude': params.device.site_longitude,
        'device_type': params.device.device_type,
        'device_vendor': params.device.device_vendor,
        'dry_run': str(params.dry_run),
        'verb': 'deploy'
    }

    return common.run_playbook(
        playbook='base_config.yaml',
        inventory=f'{params.ansible_host}:{params.ansible_port}',
        extra_vars=extra_vars,
        callback=params.callback)
