import jsonschema

from lso.routes.device import NodeProvisioningParams
from lso.routes.common import PlaybookLaunchResponse


def test_nominal_node_provisioning(client):
    params = {
        'callback': 'http://fqdn:12345',
        'data': {
            'device': {
                'fqdn': 'test.example.com',
                'lo_ipv4_address': '1.2.3.4',
                'lo_ipv6_address': '2001:db8::1',
                'lo_iso_address': '1.2.3.4.5.6',
                'snmp_location': 'city,country[1.2,3.4]',
                'si_ipv4_network': '1.2.3.0/24',
                'ias_lt_ipv4_network': '1.2.3.0/24',
                'ias_lt_ipv6_network': '2001:db8::/64',
                'site_country_code': 'FR'
            }
        }
    }

    rv = client.post(f'/api/device', json=params)
    assert rv.status_code == 200

    response = rv.json()
    jsonschema.validate(response, PlaybookLaunchResponse.schema())
    assert response['status'] == 'OK'
