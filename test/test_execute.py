import subprocess  # noqa: S404
from pathlib import Path
from uuid import UUID

import pytest
import responses

from lso.config import ExecutorType
from lso.execute import get_executable_path, run_executable_async, run_executable_sync
from lso.schema import JobStatus
from lso.tasks import CallbackFailedError
from test.utils import temp_executable_env

TEST_CALLBACK_URL = "http://localhost/callback"


@responses.activate
def test_run_executable_async_threadpool_success(temp_executable: Path):
    """ThreadPool mode: successful async run invokes callback once."""
    with temp_executable_env(ExecutorType.THREADPOOL) as exec_dir:
        target_exe = exec_dir / temp_executable.name
        target_exe.write_text(temp_executable.read_text())
        target_exe.chmod(0o755)

        responses.add(responses.POST, TEST_CALLBACK_URL, status=200)

        job_id = run_executable_async(target_exe, ["--version"], TEST_CALLBACK_URL)
        assert isinstance(job_id, UUID)
        responses.assert_call_count(TEST_CALLBACK_URL, 1)


@responses.activate
def test_run_executable_async_threadpool_callback_failure(temp_executable: Path):
    """ThreadPool mode: non-2xx callback raises CallbackFailedError."""
    with temp_executable_env(ExecutorType.THREADPOOL) as exec_dir:
        target_exe = exec_dir / temp_executable.name
        target_exe.write_text(temp_executable.read_text())
        target_exe.chmod(0o755)

        responses.add(responses.POST, TEST_CALLBACK_URL, status=500)

        with pytest.raises(CallbackFailedError) as exc:
            run_executable_async(target_exe, [], TEST_CALLBACK_URL)

        assert f"Callback failed: , url: {TEST_CALLBACK_URL}" in str(exc.value)


def test_run_executable_async_worker_delay(monkeypatch, temp_executable: Path):
    """Worker mode: schedules Celery .delay without HTTP calls."""
    with temp_executable_env(ExecutorType.WORKER) as exec_dir:
        target_exe = exec_dir / temp_executable.name
        target_exe.write_text(temp_executable.read_text())
        target_exe.chmod(0o755)

        calls = []
        import lso.execute as exec_mod  # noqa: PLC0415

        monkeypatch.setattr(
            exec_mod.run_executable_proc_task,
            "delay",
            lambda job_id, path, args, callback: calls.append((job_id, path, args, callback)),
        )

        job_id = run_executable_async(target_exe, ["a", "b"], TEST_CALLBACK_URL)
        assert len(calls) == 1
        called_job_id, called_path, called_args, called_callback = calls[0]
        assert called_job_id == str(job_id)
        assert called_path == str(target_exe)
        assert called_args == ["a", "b"]
        assert called_callback == TEST_CALLBACK_URL


@pytest.mark.parametrize("args", [[], ["x"], ["1", "2", "3"]])
def test_run_executable_sync_various_args(temp_executable: Path, args):
    """Sync helper accepts different arg lists and returns correct status."""
    # success exit
    result = run_executable_sync(str(temp_executable), args)
    assert result.return_code == 0
    assert "Executable Test" in result.output
    assert result.status == JobStatus.SUCCESSFUL

    # failure exit
    fail = temp_executable.with_name("fail.sh")
    fail.write_text("#!/bin/sh\nexit 1\n")
    fail.chmod(0o755)
    result2 = run_executable_sync(str(fail), [])
    assert result2.return_code == 1
    assert result2.status == JobStatus.FAILED


def test_get_executable_path_under_root():
    """get_executable_path returns a path under EXECUTABLES_ROOT_DIR."""
    with temp_executable_env(ExecutorType.THREADPOOL):
        p = get_executable_path(Path("foo.sh"))
        assert Path(p).parent.exists()


def test_run_executable_sync_timeout(monkeypatch):
    """If subprocess.run raises TimeoutExpired, we get return_code=-1 and the timeout message."""

    # simulate subprocess.run raising TimeoutExpired
    def fake_run(*args, **kwargs):  # noqa: ARG001
        raise subprocess.TimeoutExpired(cmd=kwargs.get("args", []), timeout=0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_executable_sync("/does/not/matter", [])
    assert result.return_code == -1
    assert result.output == "Execution timed out."
    assert result.status == JobStatus.FAILED


def test_run_executable_sync_exception(monkeypatch):
    """If subprocess.run raises a generic Exception, it's captured as output and rc=-1."""

    def fake_run(*args, **kwargs):  # noqa: ARG001
        msg = "boom!"
        raise RuntimeError(msg)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = run_executable_sync("/does/not/matter", ["x"])
    assert result.return_code == -1
    assert "boom!" in result.output
    assert result.status == JobStatus.FAILED
