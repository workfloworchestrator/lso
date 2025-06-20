# Copyright 2024-2025 GÉANT Vereniging.
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

"""Utility functions for the LSO package."""

import subprocess  # noqa: S404
from concurrent.futures import ThreadPoolExecutor

from lso.config import settings
from lso.schema import ExecutionResult

_executor = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Initialize or return a cached ThreadPoolExecutor for local asynchronous execution."""
    global _executor  # noqa: PLW0603
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=settings.MAX_THREAD_POOL_WORKERS)

    return _executor


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
