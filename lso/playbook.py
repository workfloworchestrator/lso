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


def get_playbook_path(playbook_name: Path) -> Path:
    """Get the path of a playbook on the local filesystem."""
    return Path(settings.ANSIBLE_PLAYBOOKS_ROOT_DIR) / playbook_name


def run_playbook(
    playbook_path: Path,
    extra_vars: dict[str, Any],
    inventory: dict[str, Any] | str,
    callback: HttpUrl,
) -> uuid.UUID:
    """Run an Ansible playbook against a specified inventory.

    :param Path playbook_path: playbook to be executed.
    :param dict[str, Any] extra_vars: Any extra vars needed for the playbook to run.
    :param dict[str, Any] | str inventory: The inventory that the playbook is executed against.
    :param HttpUrl callback: Callback URL where the playbook should send a status update when execution is completed.
                             This is used for workflow-orchestrator to continue with the next step in a workflow.
    :return: Result of playbook launch, this could either be successful or unsuccessful.
    :rtype: :class:`fastapi.responses.JSONResponse`
    """
    job_id = uuid.uuid4()
    if settings.EXECUTOR == ExecutorType.THREADPOOL:
        executor = get_thread_pool()
        executor_handle = executor.submit(
            run_playbook_proc_task, str(job_id), str(playbook_path), extra_vars, inventory, str(callback)
        )
        if settings.TESTING:
            executor_handle.result()

    elif settings.EXECUTOR == ExecutorType.WORKER:
        run_playbook_proc_task.delay(str(job_id), str(playbook_path), extra_vars, inventory, str(callback))

    return job_id
