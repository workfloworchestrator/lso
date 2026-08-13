# Copyright 2023-2024 GÉANT Vereniging.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import subprocess
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses
from fastapi import status
from fastapi.testclient import TestClient

from lso.config import ExecutorType
from lso.playbook import get_playbook_path
from lso.schema import InventoryValidationReason
from test.utils import temporary_executor

TEST_CALLBACK_URL = "https://fqdn.abc.xyz/api/resume"
TEST_PROGRESS_URL = "https://fqdn.abc.xyz/api/progress"


@responses.activate
@pytest.mark.parametrize("callback", [TEST_CALLBACK_URL, None])
@pytest.mark.parametrize("progress", [TEST_PROGRESS_URL, None])
def test_playbook_endpoint_dict_inventory_success(
    client: TestClient, mocked_ansible_runner_run: Callable, callback: str | None, progress: str | None
) -> None:
    params = {
        "playbook_name": "placeholder.yaml",
        "inventory": {
            "all": {"hosts": {"host1.local": {"foo": "bar"}, "host2.local": None}},
        },
        "extra_vars": {"dry_run": True, "commit_comment": "I am a robot!"},
    }

    if callback:
        responses.post(url=callback, status=status.HTTP_200_OK)
        params["callback"] = callback
    if progress:
        responses.post(url=progress, status=status.HTTP_200_OK)
        params["progress"] = progress

    with patch("lso.tasks.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_201_CREATED
        response = rv.json()

    assert isinstance(response, dict)
    assert isinstance(response["job_id"], str)


@responses.activate
def test_playbook_endpoint_str_inventory_success(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    responses.post(url=TEST_CALLBACK_URL, status=status.HTTP_200_OK)

    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {"all": {"hosts": "host1.local\nhost2.local\nhost3.local"}},
    }

    with patch("lso.tasks.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_201_CREATED
        response = rv.json()

    assert isinstance(response, dict)
    assert isinstance(response["job_id"], str)


@responses.activate
def test_playbook_endpoint_invalid_host_vars(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {
            "_meta": {"host_vars": {"host1.local": {"foo": "bar"}, "host2.local": {"hello": "world"}}},
            "all": {"hosts": "host1.local\nhost2.local\nhost3.local"},
        },
    }

    with patch("lso.tasks.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        response = rv.json()

    assert isinstance(response, dict)
    detail = response["detail"]
    assert detail["error"] == "invalid_inventory"
    # Ansible skips the unexpected key but still parses the hosts, so this is a warning rather than a total failure.
    assert detail["reason"] == InventoryValidationReason.REJECTED_WITH_WARNINGS
    assert detail["parsed_hosts"]
    # The wording belongs to Ansible and varies by version, so only assert that it was passed through.
    assert any("host_vars" in message for message in detail["messages"])
    responses.assert_call_count(TEST_CALLBACK_URL, 0)


@responses.activate
def test_playbook_endpoint_invalid_hosts(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {
            "_meta": {"vars": {"host1.local": {"foo": "bar"}}},
            "all": {"hosts": ["host1.local", "host2.local", "host3.local"]},
        },
    }

    with patch("lso.tasks.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        response = rv.json()

    assert isinstance(response, dict)
    detail = response["detail"]
    assert detail["error"] == "invalid_inventory"
    # A list of hosts is rejected outright, so Ansible ends up understanding no hosts at all.
    assert detail["reason"] == InventoryValidationReason.UNPARSABLE
    assert detail["parsed_hosts"] == []
    assert detail["messages"]
    responses.assert_call_count(TEST_CALLBACK_URL, 0)


@responses.activate
def test_run_playbook_threadpool_execution(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    """Test that the playbook runs with ThreadPoolExecutor when ExecutorType is THREADPOOL."""
    with temporary_executor(ExecutorType.THREADPOOL):
        # Simulate a successful callback.
        responses.post(url=TEST_CALLBACK_URL, status=status.HTTP_200_OK)

        params = {
            "playbook_name": "placeholder.yaml",
            "extra_vars": {"dry_run": True},
            "inventory": {
                "_meta": {"vars": {"host1.local": {"foo": "bar"}}},
                "all": {"hosts": {"host1.local": None}},
            },
            "callback": TEST_CALLBACK_URL,
        }

        with (
            patch("lso.tasks.run_playbook_proc_task", new=mocked_ansible_runner_run),
            patch("lso.playbook.get_thread_pool") as mock_get_thread_pool,
        ):
            mock_executor = MagicMock()
            mock_get_thread_pool.return_value = mock_executor
            rv = client.post("/api/playbook/", json=params)

            assert rv.status_code == status.HTTP_201_CREATED
            response = rv.json()

        assert isinstance(response, dict)
        assert isinstance(response["job_id"], str)
        mock_executor.submit.assert_called_once()


@responses.activate
def test_run_playbook_celery_execution(client: TestClient) -> None:
    """Test that the playbook runs with Celery when ExecutorType is WORKER."""
    with temporary_executor(ExecutorType.WORKER):
        responses.post(url=TEST_CALLBACK_URL, status=status.HTTP_200_OK)

        params = {
            "playbook_name": "placeholder.yaml",
            "callback": TEST_CALLBACK_URL,
            "inventory": {
                "_meta": {"vars": {"host1.local": {"foo": "bar"}}},
                "all": {"hosts": {"host1.local": None}},
            },
            "extra_vars": {"dry_run": True},
        }

        with patch("lso.tasks.run_playbook_proc_task.delay") as mock_celery_delay:
            rv = client.post("/api/playbook/", json=params)
            assert rv.status_code == status.HTTP_201_CREATED
            response = rv.json()

        assert isinstance(response, dict)
        assert isinstance(response["job_id"], str)
        mock_celery_delay.assert_called_once()


@pytest.mark.parametrize("executor_type", [ExecutorType.THREADPOOL, ExecutorType.WORKER])
def test_run_playbook_invalid_inventory(client: TestClient, executor_type: ExecutorType) -> None:
    """Test playbook execution with invalid inventory."""
    with temporary_executor(executor_type):
        params = {
            "playbook_name": "placeholder.yaml",
            "callback": TEST_CALLBACK_URL,
            "inventory": {
                "_meta": {"vars": {"host1.local": {"foo": "bar"}}},
                "all": {"hosts": ["host1.local", "host2.local"]},  # Invalid format
            },
            "extra_vars": {"dry_run": True},
        }

        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@responses.activate
def test_playbook_endpoint_bare_string_inventory(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    """A newline-separated string of hostnames is a valid inventory.

    Validation only understands the group-dictionary shape, so LSO expands the string itself before handing it over.
    """
    responses.post(url=TEST_CALLBACK_URL, status=status.HTTP_200_OK)

    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": "host1.local\nhost2.local\nhost3.local",
    }

    with patch("lso.tasks.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_201_CREATED


def test_playbook_endpoint_inventory_of_wrong_type(client: TestClient) -> None:
    """An inventory that is neither an object nor a string never reaches Ansible.

    The request schema turns this away on its own, so the rejection carries pydantic's own error body rather than
    an `InventoryProblem`. What matters here is that no subprocess is started for it.
    """
    params = {"playbook_name": "placeholder.yaml", "inventory": 42}

    with patch("lso.routes.playbook.shutil.which") as mock_which:
        rv = client.post("/api/playbook/", json=params)

    assert rv.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    mock_which.assert_not_called()


def test_playbook_endpoint_inventory_validator_missing(client: TestClient) -> None:
    """A missing `ansible-inventory` command is a deployment problem, not bad client input.

    It must surface as a 503 rather than a 422, so the caller is not misled into rewriting an inventory that may
    be perfectly valid.
    """
    params = {
        "playbook_name": "placeholder.yaml",
        "inventory": {"all": {"hosts": {"host1.local": None}}},
    }

    with patch("lso.routes.playbook.shutil.which", return_value=None):
        rv = client.post("/api/playbook/", json=params)

    assert rv.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert rv.json()["detail"]["reason"] == InventoryValidationReason.VALIDATOR_UNAVAILABLE


def test_playbook_endpoint_inventory_validation_times_out(client: TestClient) -> None:
    """Validation that outruns its timeout fails the request instead of holding the worker indefinitely.

    A 504, not a 422: the server gave up waiting, which says nothing about whether the inventory is valid.
    """
    params = {
        "playbook_name": "placeholder.yaml",
        "inventory": {"all": {"hosts": {"host1.local": None}}},
    }

    with patch(
        "lso.routes.playbook.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ansible-inventory", timeout=1),
    ):
        rv = client.post("/api/playbook/", json=params)

    assert rv.status_code == status.HTTP_504_GATEWAY_TIMEOUT
    assert rv.json()["detail"]["reason"] == InventoryValidationReason.TIMEOUT


def test_inventory_validation_ignores_ambient_ansible_config(
    client: TestClient, mocked_ansible_runner_run: Callable, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stray ansible.cfg on the host must not change whether an inventory is accepted."""
    hostile_config = tmp_path / "ansible.cfg"
    hostile_config.write_text("[defaults]\nnot_a_real_setting = definitely\n")
    monkeypatch.setenv("ANSIBLE_CONFIG", str(hostile_config))

    params = {
        "playbook_name": "placeholder.yaml",
        "inventory": {"all": {"hosts": {"host1.local": None}}},
    }

    with patch("lso.tasks.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)

    assert rv.status_code == status.HTTP_201_CREATED


@responses.activate
def test_run_playbook_invalid_playbook_path(client: TestClient) -> None:
    """Test that the playbook runs fails with invalid playbook name/path."""
    responses.post(url=TEST_CALLBACK_URL, status=status.HTTP_200_OK)

    params = {
        "playbook_name": "invalid.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {
            "_meta": {"vars": {"host1.local": {"foo": "bar"}}},
            "all": {"hosts": {"host1.local": None}},
        },
        "extra_vars": {"dry_run": True},
    }

    with patch("lso.tasks.run_playbook_proc_task.delay"):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_410_GONE
        response = rv.json()
        assert response["detail"] == f"Filename '{get_playbook_path(Path('invalid.yaml'))}' does not exist."
