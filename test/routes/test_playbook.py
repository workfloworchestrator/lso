import time
from collections.abc import Callable
from unittest.mock import patch

import responses
from fastapi import status
from fastapi.testclient import TestClient

TEST_CALLBACK_URL = "https://fqdn.abc.xyz/api/resume"


@responses.activate
def test_playbook_endpoint_dict_inventory_success(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    responses.put(url=TEST_CALLBACK_URL, status=201)

    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {
            "_meta": {
                "vars": {
                    "host1.local": {
                        "foo": "bar",
                    },
                    "host2.local": {
                        "hello": "world",
                    },
                },
            },
            "all": {
                "hosts": {
                    "host1.local": None,
                    "host2.local": None,
                },
            },
        },
        "extra_vars": {
            "dry_run": True,
            "commit_comment": "I am a robot!",
        },
    }

    with patch("lso.playbook.ansible_runner.run", new=mocked_ansible_runner_run) as _:
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_201_CREATED
        response = rv.json()
        # wait one second for the run thread to finish
        time.sleep(1)

    assert isinstance(response, dict)
    assert isinstance(response["job_id"], str)
    responses.assert_call_count(TEST_CALLBACK_URL, 1)


@responses.activate
def test_playbook_endpoint_str_inventory_success(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    responses.put(url=TEST_CALLBACK_URL, status=201)

    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {
            "all": {
                "hosts": "host1.local\nhost2.local\nhost3.local",
            },
        },
    }

    with patch("lso.playbook.ansible_runner.run", new=mocked_ansible_runner_run) as _:
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_201_CREATED
        response = rv.json()
        # wait one second for the run thread to finish
        time.sleep(1)

    assert isinstance(response, dict)
    assert isinstance(response["job_id"], str)
    responses.assert_call_count(TEST_CALLBACK_URL, 1)


@responses.activate
def test_playbook_endpoint_invalid_host_vars(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {
            "_meta": {
                "host_vars": {
                    "host1.local": {
                        "foo": "bar",
                    },
                    "host2.local": {
                        "hello": "world",
                    },
                },
            },
            "all": {
                "hosts": "host1.local\nhost2.local\nhost3.local",
            },
        },
    }

    with patch("lso.playbook.ansible_runner.run", new=mocked_ansible_runner_run) as _:
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response = rv.json()
        # wait one second for the run thread to finish
        time.sleep(1)

    assert isinstance(response, dict)
    assert response["detail"] == [
        '[WARNING]: Skipping unexpected key (host_vars) in group (_meta), only "vars",\n',
        '"children" and "hosts" are valid\n',
    ]
    responses.assert_call_count(TEST_CALLBACK_URL, 0)


@responses.activate
def test_playbook_endpoint_invalid_hosts(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {
            "_meta": {
                "vars": {
                    "host1.local": {
                        "foo": "bar",
                    },
                },
            },
            "all": {
                "hosts": ["host1.local", "host2.local", "host3.local"],
            },
        },
    }

    with patch("lso.playbook.ansible_runner.run", new=mocked_ansible_runner_run) as _:
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response = rv.json()
        # wait one second for the run thread to finish
        time.sleep(1)

    assert isinstance(response, dict)
    assert any('Invalid "hosts" entry for "all" group' in detail for detail in response["detail"])
    responses.assert_call_count(TEST_CALLBACK_URL, 0)
