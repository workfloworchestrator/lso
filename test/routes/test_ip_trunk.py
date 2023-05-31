import time
from unittest.mock import patch

import jsonschema
import responses

from lso.playbook import PlaybookLaunchResponse

_SUBSCRIPTION_OBJECT = {
            'subscription_id': '0',
            'description': 'IP trunk, geant_s_sid:GS-00000',
            'iptrunk': {
                'geant_s_sid': 'GS-00000',
                'iptrunk_description': 'A description for this trunk',
                'iptrunk_isis_metric': 9000,
                'iptrunk_minimum_links': 1,
                'iptrunk_sideA_ae_geant_a_sid': 'GA-00000',
                'iptrunk_sideA_ae_iface': 'ae0',
                'iptrunk_sideA_ae_members': [
                    'ge-0/0/0'
                ],
                'iptrunk_sideA_ae_members_description': [
                    'this is the first interface on side A'
                ],
                'iptrunk_sideA_node': {
                    'device_fqdn': 'rtx.city.country.geant.net',
                    'device_ias_lt_ipv4_network': '1.0.0.0/31',
                    'device_ias_lt_ipv6_network': 'dead:beef::3/126',
                    'device_lo_ipv4_address': '1.0.0.0',
                    'device_lo_ipv6_address': 'dead:beef::',
                    'device_lo_iso_address': '00.0000.0000.0000.0000.0000.00',
                    'device_role': 'p',
                    'device_si_ipv4_network': '0.0.1.0/31',
                    'device_site': {
                        'name': 'SiteBlock',
                        'label': None,
                        'site_city': 'City',
                        'site_name': 'city',
                        'site_tier': '1',
                        'site_country': 'Country',
                        'site_latitude': 0.0,
                        'site_longitude': 0.0,
                        'site_internal_id': 0,
                        'site_country_code': 'XX',
                        'owner_subscription_id': '0',
                        'site_bgp_community_id': 0,
                        'subscription_instance_id': '0'
                    },
                    'device_ts_address': '127.0.0.1',
                    'device_ts_port': 22,
                    'device_vendor': 'vendor',
                    'owner_subscription_id': '0',
                    'subscription_instance_id': '0'
                },
                'iptrunk_sideB_ae_geant_a_sid': 'GA-00002',
                'iptrunk_sideB_ae_iface': 'ae0',
                'iptrunk_sideB_ae_members': [
                    'ge-0/0/0'
                ],
                'iptrunk_sideB_ae_members_description': [
                    'this is the first interface side B'
                ],
                'iptrunk_sideB_node': {
                    'device_fqdn': 'rtx.town.country.geant.net',
                    'device_ias_lt_ipv4_network': '0.0.0.0/31',
                    'device_ias_lt_ipv6_network': 'deaf:beef::1/126',
                    'device_lo_ipv4_address': '0.0.0.0',
                    'device_lo_ipv6_address': 'dead:beef::2',
                    'device_lo_iso_address': '00.0000.0000.0000.0000.0000.00',
                    'device_role': 'p',
                    'device_si_ipv4_network': '0.1.0.0/31',
                    'device_site': {
                        'name': 'SiteBlock',
                        'label': None,
                        'site_city': 'Town',
                        'site_name': 'town',
                        'site_tier': '1',
                        'site_country': 'Country',
                        'site_latitude': 0.0,
                        'site_longitude': 0.0,
                        'site_internal_id': 1,
                        'site_country_code': 'xx',
                        'owner_subscription_id': '0',
                        'site_bgp_community_id': 2,
                        'subscription_instance_id': '0'
                    },
                    'device_ts_address': '127.0.0.2',
                    'device_ts_port': 22,
                    'device_vendor': 'vendor',
                    'owner_subscription_id': '0',
                    'subscription_instance_id': '0'
                },
                'iptrunk_speed': '1',
                'iptrunk_type': 'Dark_fiber'
            },
            'status': 'provisioning'
        }


@responses.activate
def test_ip_trunk_provisioning(client):
    callback_url = 'http://fqdn.xyz.abc:12345/'
    responses.add(
        method=responses.POST,
        url=callback_url)

    params = {
        'callback': callback_url,
        'dry_run': True,
        'object': 'trunk_interface',
        'verb': 'deploy',
        'subscription': _SUBSCRIPTION_OBJECT
    }

    with patch('lso.playbook.ansible_runner.run') as _run:
        rv = client.post('/api/ip_trunk/', json=params)
        assert rv.status_code == 200
        response = rv.json()
        # wait a second for the run thread to finish
        time.sleep(1)
        _run.assert_called()

    jsonschema.validate(response, PlaybookLaunchResponse.schema())
    # responses.assert_call_count(callback_url, 1)

    assert response['status'] == 'ok'


@responses.activate
def test_ip_trunk_modification(client):
    callback_url = 'http://fqdn.xyz.abc:12345/'
    responses.add(
        method=responses.PUT,
        url=callback_url)

    params = {
        'callback': callback_url,
        'dry_run': True,
        'verb': 'modify',
        'subscription': _SUBSCRIPTION_OBJECT,
        'old_subscription': _SUBSCRIPTION_OBJECT
    }

    with patch('lso.playbook.ansible_runner.run') as _run:
        rv = client.put('/api/ip_trunk/', json=params)
        assert rv.status_code == 200
        response = rv.json()
        # wait a second for the run thread to finish
        time.sleep(1)
        _run.assert_called()

    jsonschema.validate(response, PlaybookLaunchResponse.schema())
    # responses.assert_call_count(callback_url, 1)

    assert response['status'] == 'ok'


@responses.activate
def test_ip_trunk_modification(client):
    callback_url = 'http://fqdn.xyz.abc:12345/'
    responses.add(
        method=responses.DELETE,
        url=callback_url)

    params = {
        'callback': callback_url,
        'dry_run': True,
        'verb': 'terminate',
        'subscription': _SUBSCRIPTION_OBJECT
    }

    with patch('lso.playbook.ansible_runner.run') as _run:
        rv = client.request(url='/api/ip_trunk/',
                            method=responses.DELETE,
                            json=params)
        assert rv.status_code == 200
        response = rv.json()
        # wait a second for the run thread to finish
        time.sleep(1)
        _run.assert_called()

    jsonschema.validate(response, PlaybookLaunchResponse.schema())
    # responses.assert_call_count(callback_url, 1)

    assert response['status'] == 'ok'
