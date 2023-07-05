import time
from unittest.mock import patch

import jsonschema
import responses

from lso.playbook import PlaybookLaunchResponse
from test.routes import TEST_CALLBACK_URL, test_ansible_runner_run


@responses.activate
def test_router_provisioning(client):
    responses.put(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "dry_run": True,
        "verb": "deploy",
        "subscription": {
            "device": {
                "ts_address": "127.0.0.1",
                "ts_port": "1234",
                "device_fqdn": "bogus.fqdn.org",
                "lo_address": {"v4": "1.2.3.4", "v6": "2001:db8::1"},
                "lo_iso_address": "1.2.3.4.5.6",
                "snmp_location": "city,country[1.2,3.4]",
                "si_ipv4_network": "1.2.3.0/24",
                "ias_lt_network": {"v4": "1.2.3.0/24", "v6": "2001:db8::/64"},
                "site_country_code": "XX",
                "site_city": "NOWHERE",
                "site_latitude": "0.000",
                "site_longitude": "0.000",
            },
            "device_type": "router",
            "device_vendor": "vendor",
        },
    }

    with patch("lso.playbook.ansible_runner.run", new=test_ansible_runner_run) as _:
        rv = client.post("/api/device/", json=params)
        assert rv.status_code == 200
        response = rv.json()
        # wait two seconds for the run thread to finish
        time.sleep(2)

    jsonschema.validate(response, PlaybookLaunchResponse.schema())
    responses.assert_call_count(TEST_CALLBACK_URL, 1)

    assert response["status"] == "ok"
