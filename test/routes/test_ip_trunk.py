import time
from unittest.mock import patch

import jsonschema
import responses
from starlette.testclient import TestClient

from lso.playbook import PlaybookLaunchResponse
from test.routes import TEST_CALLBACK_URL, test_ansible_runner_run

_SUBSCRIPTION_OBJECT = {
    "subscription_id": "0",
    "description": "IP trunk, geant_s_sid:GS-00000",
    "iptrunk": {
        "geant_s_sid": "GS-00000",
        "iptrunk_description": "A description for this trunk",
        "iptrunk_isis_metric": 9000,
        "iptrunk_minimum_links": 1,
        "iptrunk_sideA_ae_geant_a_sid": "GA-00000",
        "iptrunk_sideA_ae_iface": "ae0",
        "iptrunk_sideA_ae_members": ["ge-0/0/0"],
        "iptrunk_sideA_ae_members_description": ["this is the first interface on side A"],
        "iptrunk_sideA_node": {
            "router_fqdn": "rtx.city.country.geant.net",
            "router_ias_lt_ipv4_network": "1.0.0.0/31",
            "router_ias_lt_ipv6_network": "dead:beef::3/126",
            "router_lo_ipv4_address": "1.0.0.0",
            "router_lo_ipv6_address": "dead:beef::",
            "router_lo_iso_address": "00.0000.0000.0000.0000.0000.00",
            "router_role": "p",
            "router_si_ipv4_network": "0.0.1.0/31",
            "router_site": {
                "name": "SiteBlock",
                "label": None,
                "site_city": "City",
                "site_name": "city",
                "site_tier": "1",
                "site_country": "Country",
                "site_latitude": 0.0,
                "site_longitude": 0.0,
                "site_internal_id": 0,
                "site_country_code": "XX",
                "owner_subscription_id": "0",
                "site_bgp_community_id": 0,
                "subscription_instance_id": "0",
                "site_ts_address": "127.0.0.2",
            },
            "router_ts_port": 22,
            "router_vendor": "vendor",
            "owner_subscription_id": "0",
            "subscription_instance_id": "0",
        },
        "iptrunk_sideB_ae_geant_a_sid": "GA-00002",
        "iptrunk_sideB_ae_iface": "ae0",
        "iptrunk_sideB_ae_members": ["ge-0/0/0"],
        "iptrunk_sideB_ae_members_description": ["this is the first interface side B"],
        "iptrunk_sideB_node": {
            "router_fqdn": "rtx.town.country.geant.net",
            "router_ias_lt_ipv4_network": "0.0.0.0/31",
            "router_ias_lt_ipv6_network": "deaf:beef::1/126",
            "router_lo_ipv4_address": "0.0.0.0",
            "router_lo_ipv6_address": "dead:beef::2",
            "router_lo_iso_address": "00.0000.0000.0000.0000.0000.00",
            "router_role": "p",
            "router_si_ipv4_network": "0.1.0.0/31",
            "router_site": {
                "name": "SiteBlock",
                "label": None,
                "site_city": "Town",
                "site_name": "town",
                "site_tier": "1",
                "site_country": "Country",
                "site_latitude": 0.0,
                "site_longitude": 0.0,
                "site_internal_id": 1,
                "site_country_code": "xx",
                "owner_subscription_id": "0",
                "site_bgp_community_id": 2,
                "subscription_instance_id": "0",
                "site_ts_address": "127.0.0.2",
            },
            "router_ts_port": 22,
            "router_vendor": "vendor",
            "owner_subscription_id": "0",
            "subscription_instance_id": "0",
        },
        "iptrunk_speed": "1",
        "iptrunk_type": "Dark_fiber",
    },
    "status": "provisioning",
}


@responses.activate
def test_ip_trunk_provisioning(client: TestClient) -> None:
    responses.put(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "dry_run": True,
        "object": "trunk_interface",
        "verb": "deploy",
        "subscription": _SUBSCRIPTION_OBJECT,
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
def test_ip_trunk_modification(client: TestClient) -> None:
    responses.put(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "dry_run": True,
        "verb": "modify",
        "subscription": _SUBSCRIPTION_OBJECT,
        "old_subscription": _SUBSCRIPTION_OBJECT,
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
def test_ip_trunk_deletion(client: TestClient) -> None:
    responses.put(url=TEST_CALLBACK_URL, status=204)

    params = {"callback": TEST_CALLBACK_URL, "dry_run": True, "verb": "terminate", "subscription": _SUBSCRIPTION_OBJECT}

    with patch("lso.playbook.ansible_runner.run", new=test_ansible_runner_run) as _:
        rv = client.request(url="/api/ip_trunk/", method=responses.DELETE, json=params)
        assert rv.status_code == 200
        response = rv.json()
        # wait a second for the run thread to finish
        time.sleep(1)

    jsonschema.validate(response, PlaybookLaunchResponse.model_json_schema())
    responses.assert_call_count(TEST_CALLBACK_URL, 1)

    assert response["status"] == "ok"
