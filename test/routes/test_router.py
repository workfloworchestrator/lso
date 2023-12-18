import time
from collections.abc import Callable
from unittest.mock import patch

import responses
from faker import Faker
from fastapi import status
from fastapi.testclient import TestClient

TEST_CALLBACK_URL = "https://fqdn.abc.xyz/api/resume"


@responses.activate
def test_router_provisioning(client: TestClient, faker: Faker, mocked_ansible_runner_run: Callable) -> None:
    responses.post(url=TEST_CALLBACK_URL, status=status.HTTP_200_OK)

    params = {
        "callback": TEST_CALLBACK_URL,
        "dry_run": faker.pybool(),
        "process_id": faker.uuid4(),
        "tt_number": faker.pystr(),
        "verb": "deploy",
        "subscription": {
            "router": {
                "ts_address": faker.ipv4(),
                "ts_port": str(faker.pyint()),
                "router_fqdn": "bogus.fqdn.org",
                "lo_address": {"v4": faker.ipv4(), "v6": faker.ipv6()},
                "lo_iso_address": "1.2.3.4.5.6",
                "snmp_location": "city,country[1.2,3.4]",
                "si_ipv4_network": faker.ipv4() + "/24",
                "ias_lt_network": {
                    "v4": faker.ipv4() + "/24",
                    "v6": faker.ipv6() + "/64",
                },
                "site_country_code": faker.country_code(),
                "site_city": faker.city(),
                "site_latitude": float(faker.latitude()),
                "site_longitude": float(faker.longitude()),
            },
            "router_type": "router",
            "router_vendor": "vendor",
        },
    }

    with patch("lso.playbook.ansible_runner.run", new=mocked_ansible_runner_run) as _:
        rv = client.post("/api/router/", json=params)
        assert rv.status_code == status.HTTP_201_CREATED
        response = rv.json()
        # wait two seconds for the run thread to finish
        time.sleep(2)

    assert isinstance(response, dict)
    assert isinstance(response["job_id"], str)
    responses.assert_call_count(TEST_CALLBACK_URL, 1)
