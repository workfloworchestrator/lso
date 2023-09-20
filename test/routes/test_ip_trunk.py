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
                        "site_city": "City",
                        "site_name": "city",
                        "site_tier": "1",
                        "site_country": "Country",
                        "site_latitude": 1,
                        "site_longitude": 1,
                        "site_ts_address": "0.0.0.0",
                        "site_internal_id": 1,
                        "site_country_code": "xxx",
                        "owner_subscription_id": "b5146e62-da79-4791-b703-d03b0ebeebf8",
                        "site_bgp_community_id": 1,
                        "subscription_instance_id": "039e03e5-5c09-4236-8d28-cd569e04315e",
                    },
                    "router_vendor": "juniper",
                    "router_ts_port": 22222,
                    "router_access_via_ts": True,
                    "owner_subscription_id": "4a0001f1-459d-46f5-9a85-b8177e1bbc1b",
                    "router_lo_iso_address": "49.51e5.0001.0620.4009.6014.00",
                    "router_lo_ipv4_address": "0.0.0.0",
                    "router_lo_ipv6_address": "::",
                    "router_si_ipv4_network": "0.0.0.0/31",
                    "router_is_ias_connected": True,
                    "subscription_instance_id": "2242883e-a581-4ce1-919c-9c986ded57f6",
                    "router_ias_lt_ipv4_network": "0.0.0.0/31",
                    "router_ias_lt_ipv6_network": "::/126",
                },
                "iptrunk_side_ae_iface": "ae1",
                "owner_subscription_id": "c9ddbe14-e107-4749-82ac-e22091cdb132",
                "iptrunk_side_ae_members": ["ge-0/0/0", "ge-0/0/1"],
                "subscription_instance_id": "6276fac5-9d31-4c9a-9247-48f02a19f151",
                "iptrunk_side_ae_geant_a_sid": "SID-11112",
                "iptrunk_side_ae_members_description": ["first one", "second one"],
            },
            {
                "name": "IptrunkSideBlock",
                "label": None,
                "iptrunk_side_node": {
                    "name": "RouterBlock",
                    "label": None,
                    "router_fqdn": "rt2.city.country.geant.net",
                    "router_role": "p",
                    "router_site": {
                        "name": "SiteBlock",
                        "label": None,
                        "site_city": "City",
                        "site_name": "city",
                        "site_tier": "1",
                        "site_country": "Country",
                        "site_latitude": 1,
                        "site_longitude": 1,
                        "site_ts_address": "0.0.0.0",
                        "site_internal_id": 2,
                        "site_country_code": "country",
                        "owner_subscription_id": "93cba8dc-7424-44c0-8872-13159df93042",
                        "site_bgp_community_id": 2,
                        "subscription_instance_id": "6bf4f274-6496-438d-9dba-9c3984d0ec07",
                    },
                    "router_vendor": "juniper",
                    "router_ts_port": 11111,
                    "router_access_via_ts": True,
                    "owner_subscription_id": "9cb1fc7d-9608-42ce-aacc-2a97f9620a91",
                    "router_lo_iso_address": "49.51e5.0001.0620.4009.6066.00",
                    "router_lo_ipv4_address": "0.0.0.0",
                    "router_lo_ipv6_address": "::",
                    "router_si_ipv4_network": "0.0.0.0/31",
                    "router_is_ias_connected": True,
                    "subscription_instance_id": "6d09394e-658b-4e55-8b1f-8b812d59f5a1",
                    "router_ias_lt_ipv4_network": "0.0.0.0/31",
                    "router_ias_lt_ipv6_network": "::/126",
                },
                "iptrunk_side_ae_iface": "ae1",
                "owner_subscription_id": "c9ddbe14-e107-4749-82ac-e22091cdb132",
                "iptrunk_side_ae_members": ["ge-0/0/0", "ge-0/0/1"],
            },
        ],
    },
    "status": "provisioning",
}

_MIGRATION_OBJECT = {
    "new_node": {
        "description": "Router rt1.luc.it.geant.net",
        "router": {
            "router_access_via_ts": "true",
            "router_fqdn": "rt1.luc.it.geant.net",
            "router_role": "pe",
            "router_is_ias_connected": "false",
            "router_lo_ipv4_address": "62.40.96.7",
            "router_lo_ipv6_address": "2001:798:aa:1::49",
            "router_lo_iso_address": "49.51e5.0001.0620.4009.6007.00",
            "router_site": {
                "name": "SiteBlock",
                "label": "null",
                "site_city": "Lucca",
                "site_name": "luc",
                "site_tier": "1",
                "site_country": "Italy",
                "site_latitude": "10.0",
                "site_longitude": "43.0",
                "site_ts_address": "172.16.100.151",
                "site_internal_id": 133,
                "site_country_code": "IT",
                "owner_subscription_id": "f4bacf38-39bb-4553-8e74-190699bd9b4e",
                "site_bgp_community_id": 33,
                "subscription_instance_id": "2cf443a2-4039-4402-ab75-73ff1a1096f5",
            },
            "router_ts_port": 22111,
            "router_vendor": "juniper",
        },
        "status": "provisioning",
    },
    "new_lag_interface": "ae1",
    "new_lag_member_interfaces": ["ge-0/0/0", "ge-0/0/1"],
    "replace_index": 0,
}


@responses.activate
def test_ip_trunk_provisioning(client: TestClient) -> None:
    responses.put(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "process_id": "cb5f6c71-63d7-4857-9124-4fc6e7ef3f41",
        "tt_number": "TT123456789",
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
        "process_id": "cb5f6c71-63d7-4857-9124-4fc6e7ef3f41",
        "tt_number": "TT123456789",
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

    params = {
        "callback": TEST_CALLBACK_URL,
        "process_id": "cb5f6c71-63d7-4857-9124-4fc6e7ef3f41",
        "tt_number": "TT123456789",
        "dry_run": True,
        "verb": "terminate",
        "subscription": _SUBSCRIPTION_OBJECT,
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
def test_ip_trunk_migration(client: TestClient) -> None:
    responses.put(url=TEST_CALLBACK_URL, status=204)

    params = {
        "callback": TEST_CALLBACK_URL,
        "dry_run": True,
        "process_id": "cb5f6c71-63d7-4857-9124-4fc6e7ef3f41",
        "tt_number": "TT123456789",
        "verb": "migrate",
        "config_object": "trunk_interface",
        "subscription": _SUBSCRIPTION_OBJECT,
        "new_side": _MIGRATION_OBJECT,
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
