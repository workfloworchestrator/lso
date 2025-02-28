import uuid
from pathlib import Path

import responses

from lso.config import ExecutorType
from lso.execute import run_executable
from test.utils import temp_executable_env

TEST_CALLBACK_URL = "http://localhost/callback"


@responses.activate
def test_run_executable_threadpool(temp_executable: Path):
    """
    Test direct invocation of run_executable using the ThreadPool executor.
    """
    with temp_executable_env(ExecutorType.THREADPOOL) as exec_dir:
        target_exe = exec_dir / temp_executable.name
        target_exe.write_text(temp_executable.read_text())
        target_exe.chmod(0o755)

        # Simulate a successful callback.
        responses.add(responses.POST, TEST_CALLBACK_URL, status=200)

        job_id = run_executable(target_exe, ["--version"], TEST_CALLBACK_URL)
        uuid.UUID(str(job_id))  # Validate job_id format.
