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

"""Module that gathers common API responses and data models."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import ansible_runner
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import HttpUrl

from lso.config import ExecutorType, settings
from lso.tasks import run_playbook_proc_task

_executor = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Get and optionally initialise a ThreadPoolExecutor.

    Returns:
        ThreadPoolExecutor

    """
    global _executor  # noqa: PLW0603
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=settings.MAX_THREAD_POOL_WORKERS)

    return _executor


def get_playbook_path(playbook_name: str) -> Path:
    """Get the path of a playbook on the local filesystem."""
    return Path(settings.ANSIBLE_PLAYBOOKS_ROOT_DIR) / playbook_name


def playbook_launch_success(job_id: str) -> JSONResponse:
    """Return a :class:`PlaybookLaunchResponse` for the successful start of a playbook execution.

    :return JSONResponse: A playbook launch response that's successful.
    """
    return JSONResponse(content={"job_id": job_id}, status_code=status.HTTP_201_CREATED)


def playbook_launch_error(reason: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> JSONResponse:
    """Return a :class:`PlaybookLaunchResponse` for the erroneous start of a playbook execution.

    :param str reason: The reason why a request has failed.
    :param status status_code: The HTTP status code that should be associated with this request. Defaults to HTTP 400:
                               Bad request.
    :return JSONResponse: A playbook launch response that's unsuccessful.
    """
    return JSONResponse(content={"error": reason}, status_code=status_code)


def run_playbook(
    playbook_path: Path,
    extra_vars: dict[str, Any],
    inventory: dict[str, Any] | str,
    callback: HttpUrl,
) -> JSONResponse:
    """Run an Ansible playbook against a specified inventory.

    :param Path playbook_path: playbook to be executed.
    :param dict[str, Any] extra_vars: Any extra vars needed for the playbook to run.
    :param dict[str, Any] | str inventory: The inventory that the playbook is executed against.
    :param HttpUrl callback: Callback URL where the playbook should send a status update when execution is completed.
                             This is used for workflow-orchestrator to continue with the next step in a workflow.
    :return: Result of playbook launch, this could either be successful or unsuccessful.
    :rtype: :class:`fastapi.responses.JSONResponse`
    """
    if not Path.exists(playbook_path):
        msg = f"Filename '{playbook_path}' does not exist."
        return playbook_launch_error(reason=msg, status_code=status.HTTP_404_NOT_FOUND)

    if not ansible_runner.utils.isinventory(inventory):
        msg = "Invalid inventory provided. Should be a string, or JSON object."
        return playbook_launch_error(reason=msg, status_code=status.HTTP_400_BAD_REQUEST)

    job_id = str(uuid.uuid4())
    if settings.EXECUTOR == ExecutorType.THREADPOOL:
        executor = get_thread_pool()
        executor_handle = executor.submit(
            run_playbook_proc_task, job_id, str(playbook_path), extra_vars, inventory, str(callback)
        )
        if settings.TESTING:
            executor_handle.result()

    elif settings.EXECUTOR == ExecutorType.WORKER:
        run_playbook_proc_task.delay(job_id, str(playbook_path), extra_vars, inventory, str(callback))

    return playbook_launch_success(job_id=job_id)
