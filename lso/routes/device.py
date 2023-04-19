"""
Routes for handling device/base_config-related requests
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lso.routes import common
from gso.products.product_types.device import DeviceBlockProvisioning

router = APIRouter()


@router.post('/')
async def provision_node(device: DeviceBlockProvisioning) -> JSONResponse:
    """
    runs the base_config playbook

    :return: A `JSONResponse` that will report on successful executing of a
    """

    extra_vars = {
        'lo_ipv4_address': str(device.device.lo_ipv4_address),
        'lo_ipv6_address': str(device.device.lo_ipv6_address),
        'lo_iso_address': device.device.lo_iso_address,
        'snmp_location': device.device.snmp_location,
        'si_ipv4_network': str(device.device.si_ipv4_network),
        'lt_ipv4_network': str(device.device.ias_lt_ipv4_network),
        'lt_ipv6_network': str(device.device.ias_lt_ipv6_network),
        'site_country_code': device.device.site_country_code,
        'verb': 'deploy'}

    return common.run_playbook(
        playbook = 'base_config.yaml',  # TODO: config
        inventory = device.device.fqdn,
        extra_vars = extra_vars)
