import jsonschema
import time
from unittest.mock import patch

from lso.routes.device import NodeProvisioningParams
from lso.routes.common import PlaybookLaunchResponse


def test_nominal_node_provisioning(client):
    params = {
        'callback': 'http://fqdn.xyz.abc:12345',
        'device': {
            'fqdn': 'bogus.fqdn.org',
            'lo_address': {'v4': '1.2.3.4', 'v6': '2001:db8::1'},
            'lo_iso_address': '1.2.3.4.5.6',
            'snmp_location': 'city,country[1.2,3.4]',
            'si_ipv4_network': '1.2.3.0/24',
            'ias_lt_network': {'v4': '1.2.3.0/24', 'v6': '2001:db8::/64'},
            'site_country_code': 'abcdefg'
        }
    }

    with patch('lso.routes.common.ansible_runner.run') as _run:
        rv = client.post(f'/api/device', json=params)
        # rv = client.post(f'/api/device', json=payload.json())
        assert rv.status_code == 200
        response = rv.json()
        # give a second for the run thread to finish
        time.sleep(1)
        _run.assert_called()

    jsonschema.validate(response, PlaybookLaunchResponse.schema())
    assert response['status'] == 'OK'
