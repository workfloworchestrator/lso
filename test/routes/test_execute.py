import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import responses
from fastapi import status
from fastapi.testclient import TestClient

from lso.config import ExecutorType
from test.utils import temp_executable_env

TEST_CALLBACK_URL = "http://localhost/callback"


@responses.activate
def test_execute_endpoint_threadpool_success(client: TestClient, temp_executable: Path):
    with temp_executable_env(ExecutorType.THREADPOOL) as exec_dir:
        target_exe = exec_dir / temp_executable.name
        target_exe.write_text(temp_executable.read_text())
        target_exe.chmod(0o755)

        # Simulate a successful callback.
        responses.add(responses.POST, TEST_CALLBACK_URL, status=200)

        params = {
            "executable_name": temp_executable.name,
            "args": [],
            "callback": TEST_CALLBACK_URL,
        }
        with (
            patch("lso.execute.run_executable_proc_task") as mock_run_executable_proc_task,
            patch("lso.execute.get_thread_pool") as mock_get_thread_pool,
        ):
            mock_executor = MagicMock()
            mock_get_thread_pool.return_value = mock_executor
            rv = client.post("/api/execute/", json=params)

            assert rv.status_code == status.HTTP_201_CREATED
            response = rv.json()

        assert isinstance(response, dict)
        uuid.UUID(response["job_id"])  # Validate job_id format.
        mock_executor.submit.assert_called_once()
        assert mock_run_executable_proc_task.call_count == 0


@responses.activate
def test_execute_endpoint_worker_success(client: TestClient, temp_executable: Path):
    with temp_executable_env(ExecutorType.WORKER) as exec_dir:
        target_exe = exec_dir / temp_executable.name
        target_exe.write_text(temp_executable.read_text())
        target_exe.chmod(0o755)

        # Simulate a successful callback.
        responses.add(responses.POST, TEST_CALLBACK_URL, status=200)

        params = {
            "executable_name": temp_executable.name,
            "args": [],
            "callback": TEST_CALLBACK_URL,
        }
        with patch("lso.tasks.run_executable_proc_task.delay") as mock_celery_delay:
            rv = client.post("/api/execute/", json=params)
            assert rv.status_code == status.HTTP_201_CREATED
            response = rv.json()

        assert isinstance(response, dict)
        uuid.UUID(response["job_id"])  # Validate job_id format.
        mock_celery_delay.assert_called_once()


@responses.activate
def test_execute_endpoint_not_found(client: TestClient):
    # Request with a non-existent executable should return 404.
    params = {
        "executable_name": "nonexistent.sh",
        "args": [],
        "callback": TEST_CALLBACK_URL,
    }
    response = client.post("/api/execute/", json=params)
    assert response.status_code == status.HTTP_404_NOT_FOUND


@responses.activate
def test_execute_endpoint_not_executable(client: TestClient, tmp_path: Path):
    # Create a file that exists but is not executable.
    non_exe = tmp_path / "non_executable.sh"
    non_exe.write_text("echo 'Hello'")
    non_exe.chmod(0o644)
    with temp_executable_env(ExecutorType.THREADPOOL) as exec_dir:
        target_file = exec_dir / non_exe.name
        target_file.write_text(non_exe.read_text())
        target_file.chmod(0o644)
        params = {
            "executable_name": non_exe.name,
            "args": [],
            "callback": TEST_CALLBACK_URL,
        }
        response = client.post("/api/execute/", json=params)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json() == {"detail": f"Executable '{non_exe.name}' is not marked as executable."}


@responses.activate
def test_execute_endpoint_not_a_file(client: TestClient):
    """
    Test that if the provided executable path is a directory (exists but is not a file),
    the endpoint returns a 404 with an appropriate error message.
    """
    with temp_executable_env(ExecutorType.THREADPOOL) as exec_dir:
        # Create a directory within the temporary executables' environment.
        target_dir = exec_dir / "not_a_file"
        target_dir.mkdir()

        params = {
            "executable_name": "not_a_file",
            "args": [],
            "callback": TEST_CALLBACK_URL,
        }

        response = client.post("/api/execute/", json=params)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "Executable 'not_a_file' is not a valid file."}
