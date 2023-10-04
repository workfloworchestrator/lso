import time
from unittest.mock import patch

import jsonschema
import pytest
import responses
from faker import Faker
from starlette.testclient import TestClient

from lso.playbook import PlaybookLaunchResponse
from test.routes import TEST_CALLBACK_URL, test_ansible_runner_run


@pytest.fixture(scope="session")
def subscription_object(faker: Faker) -> dict:
    return {
        "subscription_id": faker.pyint(),
        "description": "IP trunk, geant_s_sid:GS-00000",
        "iptrunk": {
            "geant_s_sid": "GS-00000",
            "iptrunk_description": faker.pystr(),
            "iptrunk_isis_metric": faker.pyint(),
            "iptrunk_minimum_links": 1,
            "iptrunk_sides": [
                {
                    "name": "IptrunkSideBlock",
                    "label": None,
                    "iptrunk_side_node": {
                        "name": "RouterBlock",
                        "label": None,
                        "router_fqdn": "rt1.city.country.geant.net",
                        "router_role": "p",
                        "router_site": {
                            "name": "SiteBlock",
                            "label": None,
                            "site_city": faker.city(),
                            "site_name": "city",
                            "site_tier": "1",
                            "site_country": faker.country(),
                            "site_latitude": float(faker.latitude()),
                            "site_longitude": float(faker.longitude()),
                            "site_ts_address": faker.ipv4(),
                            "site_internal_id": faker.pyint(),
                            "site_country_code": faker.country_code(),
                            "owner_subscription_id": faker.uuid4(),
                            "site_bgp_community_id": faker.pyint(),
                            "subscription_instance_id": faker.uuid4(),
                        },
                        "router_vendor": "juniper",
                        "router_ts_port": faker.pyint(),
                        "router_access_via_ts": faker.pybool(),
                        "owner_subscription_id": faker.uuid4(),
                        "router_lo_iso_address": "49.51e5.0001.0620.4009.6014.00",
                        "router_lo_ipv4_address": faker.ipv4(),
                        "router_lo_ipv6_address": faker.ipv6(),
                        "router_si_ipv4_network": faker.ipv4() + "/31",
                        "router_is_ias_connected": faker.pybool(),
                        "subscription_instance_id": faker.uuid4(),
                        "router_ias_lt_ipv4_network": faker.ipv4() + "/31",
                        "router_ias_lt_ipv6_network": faker.ipv6() + "/126",
                    },
                    "iptrunk_side_ae_iface": "ae1",
                    "owner_subscription_id": faker.uuid4(),
                    "iptrunk_side_ae_members": ["ge-0/0/0", "ge-0/0/1"],
                    "subscription_instance_id": faker.uuid4(),
                    "iptrunk_side_ae_geant_a_sid": "SID-11112",
                    "iptrunk_side_ae_members_description": [faker.pystr(), faker.pystr()],
                },
                {
                    "name": "IptrunkSideBlock",
                    "label": None,
                    "iptrunk_side_node": {
                        "name": "RouterBlock",
                        "label": None,
                        "router_fqdn": "rt1.city.country.geant.net",
                        "router_role": "p",
                        "router_site": {
                            "name": "SiteBlock",
                            "label": None,
                            "site_city": faker.city(),
                            "site_name": "city",
                            "site_tier": "1",
                            "site_country": faker.country(),
                            "site_latitude": float(faker.latitude()),
                            "site_longitude": float(faker.longitude()),
                            "site_ts_address": faker.ipv4(),
                            "site_internal_id": faker.pyint(),
                            "site_country_code": faker.country_code(),
                            "owner_subscription_id": faker.uuid4(),
                            "site_bgp_community_id": faker.pyint(),
                            "subscription_instance_id": faker.uuid4(),
                        },
                        "router_vendor": "juniper",
                        "router_ts_port": faker.pyint(),
                        "router_access_via_ts": faker.pybool(),
                        "owner_subscription_id": faker.uuid4(),
                        "router_lo_iso_address": "49.51e5.0001.0620.4009.6014.00",
                        "router_lo_ipv4_address": faker.ipv4(),
                        "router_lo_ipv6_address": faker.ipv6(),
                        "router_si_ipv4_network": faker.ipv4() + "/31",
                        "router_is_ias_connected": faker.pybool(),
                        "subscription_instance_id": faker.uuid4(),
                        "router_ias_lt_ipv4_network": faker.ipv4() + "/31",
                        "router_ias_lt_ipv6_network": faker.ipv6() + "/126",
                    },
                    "iptrunk_side_ae_iface": "ae1",
                    "owner_subscription_id": faker.uuid4(),
                    "iptrunk_side_ae_members": ["ge-0/0/0", "ge-0/0/1"],
                    "subscription_instance_id": faker.uuid4(),
                    "iptrunk_side_ae_geant_a_sid": "SID-11112",
                    "iptrunk_side_ae_members_description": [faker.pystr(), faker.pystr()],
                },
            ],
        },
        "status": "provisioning",
    }


@pytest.fixture(scope="session")
def migration_object(faker: Faker) -> dict:
    return {
        "new_node": {
            "description": "Router rt1.luc.it.geant.net",
            "router": {
                "router_access_via_ts": "true",
                "router_fqdn": "rt1.luc.it.geant.net",
                "router_role": "pe",
                "router_is_ias_connected": faker.pybool(),
                "router_lo_ipv4_address": faker.ipv4(),
                "router_lo_ipv6_address": faker.ipv6(),
                "router_lo_iso_address": "49.51e5.0001.0620.4009.6007.00",
                "router_site": {
                    "name": "SiteBlock",
                    "label": "null",
                    "site_city": faker.city(),
                    "site_name": "luc",
                    "site_tier": "1",
                    "site_country": faker.country(),
                    "site_latitude": "10.0",
                    "site_longitude": "43.0",
                    "site_ts_address": faker.ipv4(),
                    "site_internal_id": faker.pyint(),
                    "site_country_code": faker.country_code(),
                    "owner_subscription_id": faker.uuid4(),
                    "site_bgp_community_id": faker.pyint(),
                    "subscription_instance_id": faker.uuid4(),
                },
                "router_ts_port": faker.pyint(),
                "router_vendor": "juniper",
            },
            "status": "provisioning",
        },
        "new_lag_interface": "ae1",
        "new_lag_member_interfaces": ["ge-0/0/0", "ge-0/0/1"],
        "replace_index": 0,
    }


@responses.activate
def test_ip_trunk_provisioning(client: TestClient, subscription_object: dict) -> None:
    responses.post(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "process_id": "cb5f6c71-63d7-4857-9124-4fc6e7ef3f41",
        "tt_number": "TT123456789",
        "dry_run": True,
        "object": "trunk_interface",
        "verb": "deploy",
        "subscription": subscription_object,
    }

    with patch("lso.playbook.ansible_runner.run", new=test_ansible_runner_run) as _:
        rv = client.post("/api/ip_trunk/", json=params)
        assert rv.status_code == 200
        response = rv.json()
        # wait a second for the run thread to finish
        time.sleep(1)

    jsonschema.validate(response, PlaybookLaunchResponse.model_json_schema())
    responses.assert_call_count(TEST_CALLBACK_URL, 1)

    assert response["status"] == "ok"


@responses.activate
def test_ip_trunk_modification(client: TestClient, subscription_object: dict) -> None:
    responses.post(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "process_id": "cb5f6c71-63d7-4857-9124-4fc6e7ef3f41",
        "tt_number": "TT123456789",
        "dry_run": True,
        "verb": "modify",
        "subscription": subscription_object,
        "old_subscription": subscription_object,
    }

    with patch("lso.playbook.ansible_runner.run", new=test_ansible_runner_run) as _:
        rv = client.put("/api/ip_trunk/", json=params)
        assert rv.status_code == 200
        response = rv.json()
        # wait a second for the run thread to finish
        time.sleep(1)

    jsonschema.validate(response, PlaybookLaunchResponse.model_json_schema())
    responses.assert_call_count(TEST_CALLBACK_URL, 1)

    assert response["status"] == "ok"


@responses.activate
def test_ip_trunk_deletion(client: TestClient, subscription_object: dict) -> None:
    responses.post(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "process_id": "cb5f6c71-63d7-4857-9124-4fc6e7ef3f41",
        "tt_number": "TT123456789",
        "dry_run": True,
        "verb": "terminate",
        "subscription": subscription_object,
    }

    with patch("lso.playbook.ansible_runner.run", new=test_ansible_runner_run) as _:
        rv = client.request(url="/api/ip_trunk/", method=responses.DELETE, json=params)
        assert rv.status_code == 200
        response = rv.json()
        # wait a second for the run thread to finish
        time.sleep(1)

    jsonschema.validate(response, PlaybookLaunchResponse.model_json_schema())
    responses.assert_call_count(TEST_CALLBACK_URL, 1)

    assert response["status"] == "ok"


@responses.activate
def test_ip_trunk_migration(client: TestClient, subscription_object: dict, migration_object: dict) -> None:
    responses.post(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "dry_run": True,
        "process_id": "cb5f6c71-63d7-4857-9124-4fc6e7ef3f41",
        "tt_number": "TT123456789",
        "verb": "migrate",
        "config_object": "trunk_interface",
        "subscription": subscription_object,
        "new_side": migration_object,
    }

    with patch("lso.playbook.ansible_runner.run", new=test_ansible_runner_run) as _:
        rv = client.request(url="/api/ip_trunk/migrate", method=responses.POST, json=params)
        assert rv.status_code == 200
        response = rv.json()
        #  Wait a second for the run to finish
        time.sleep(1)

    jsonschema.validate(response, PlaybookLaunchResponse.model_json_schema())
    responses.assert_call_count(TEST_CALLBACK_URL, 1)

    assert response["status"] == "ok"
