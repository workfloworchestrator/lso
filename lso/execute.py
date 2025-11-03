# Copyright 2023-2025 GÉANT Vereniging.
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

"""Module for handling the execution of arbitrary executables."""

import subprocess  # noqa: S404
import uuid
from pathlib import Path

from pydantic import HttpUrl

from lso.config import ExecutorType, settings
from lso.schema import ExecutionResult
from lso.tasks import run_executable_proc_task
from lso.utils import get_thread_pool


def get_executable_path(executable_name: Path) -> Path:
    """Return the full path of an executable, based on the configured EXECUTABLES_ROOT_DIR."""
    return Path(settings.EXECUTABLES_ROOT_DIR) / executable_name


def run_executable_async(executable_path: Path, args: list[str], callback: HttpUrl | None) -> uuid.UUID:
    """Dispatch the task for executing an arbitrary executable remotely.

    Uses a ThreadPoolExecutor (for local execution) or a Celery worker (for distributed tasks).
    """
    job_id = uuid.uuid4()
    callback_url = str(callback) if callback else None
    if settings.EXECUTOR == ExecutorType.THREADPOOL:
        executor = get_thread_pool()
        future = executor.submit(run_executable_proc_task, str(job_id), str(executable_path), args, callback_url)
        if settings.TESTING:
            future.result()
    elif settings.EXECUTOR == ExecutorType.WORKER:
        run_executable_proc_task.delay(str(job_id), str(executable_path), args, callback_url)
    return job_id


def run_executable_sync(executable_path: str, args: list[str]) -> ExecutionResult:
    """Run the given executable synchronously and return the result."""
    try:
        result = subprocess.run(  # noqa: S603
            [executable_path, *args],
            text=True,
            capture_output=True,
            timeout=settings.EXECUTABLE_TIMEOUT_SEC,
            check=False,
        )
        output = result.stdout + result.stderr
        return_code = result.returncode
    except subprocess.TimeoutExpired:
        output = "Execution timed out."
        return_code = -1
    except Exception as e:  # noqa: BLE001
        output = str(e)
        return_code = -1

    return ExecutionResult(  # type: ignore[call-arg]
        output=output,
        return_code=return_code,
    )
