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
import re
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses
from fastapi import status
from fastapi.testclient import TestClient

from lso.config import ExecutorType, settings
from lso.playbook import get_playbook_path

TEST_CALLBACK_URL = "https://fqdn.abc.xyz/api/resume"


@contextmanager
def temporary_executor(executor_type: ExecutorType):
    original_executor = settings.EXECUTOR
    settings.EXECUTOR = executor_type
    try:
        yield
    finally:
        settings.EXECUTOR = original_executor


@responses.activate
def test_playbook_endpoint_dict_inventory_success(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    responses.post(url=TEST_CALLBACK_URL, status=status.HTTP_200_OK)

    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {
            "_meta": {"vars": {"host1.local": {"foo": "bar"}, "host2.local": {"hello": "world"}}},
            "all": {"hosts": {"host1.local": None, "host2.local": None}},
        },
        "extra_vars": {"dry_run": True, "commit_comment": "I am a robot!"},
    }

    with patch("lso.routes.playbook.ansible_runner.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_201_CREATED
        response = rv.json()

    assert isinstance(response, dict)
    assert isinstance(response["job_id"], str)
    responses.assert_call_count(TEST_CALLBACK_URL, 1)


@responses.activate
def test_playbook_endpoint_str_inventory_success(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    responses.post(url=TEST_CALLBACK_URL, status=status.HTTP_200_OK)

    params = {
        "playbook_name": "placeholder.yaml",
        "callback": TEST_CALLBACK_URL,
        "inventory": {"all": {"hosts": "host1.local\nhost2.local\nhost3.local"}},
    }

    with patch("lso.routes.playbook.ansible_runner.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_201_CREATED
        response = rv.json()

    assert isinstance(response, dict)
    assert isinstance(response["job_id"], str)
    responses.assert_call_count(TEST_CALLBACK_URL, 1)


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

    with patch("lso.routes.playbook.ansible_runner.run", new=mocked_ansible_runner_run) as _:
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response = rv.json()

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
            "_meta": {"vars": {"host1.local": {"foo": "bar"}}},
            "all": {"hosts": ["host1.local", "host2.local", "host3.local"]},
        },
    }

    with patch("lso.routes.playbook.ansible_runner.run", new=mocked_ansible_runner_run):
        rv = client.post("/api/playbook/", json=params)
        assert rv.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response = rv.json()

    assert isinstance(response, dict)
    assert 'Invalid "hosts" entry for "all" group' in re.sub(r"\n", " ", "".join(response["detail"]))
    responses.assert_call_count(TEST_CALLBACK_URL, 0)


@responses.activate
def test_run_playbook_threadpool_execution(client: TestClient, mocked_ansible_runner_run: Callable) -> None:
    """Test that the playbook runs with ThreadPoolExecutor when ExecutorType is THREADPOOL."""
    with temporary_executor(ExecutorType.THREADPOOL):
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
        assert rv.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


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
        assert rv.status_code == status.HTTP_404_NOT_FOUND
        response = rv.json()
        assert response["detail"] == f"Filename '{get_playbook_path(Path('invalid.yaml'))}' does not exist."
