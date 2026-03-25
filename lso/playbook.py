# Copyright 2023-2026 GÉANT Vereniging.
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

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import HttpUrl

from lso.config import ExecutorType, settings
from lso.tasks import run_playbook_proc_task
from lso.utils import get_thread_pool


def get_playbook_path(playbook_name: Path) -> Path:
    """Get the path of a playbook on the local filesystem."""
    return Path(settings.ANSIBLE_PLAYBOOKS_ROOT_DIR) / playbook_name


def run_playbook(
    playbook_path: Path,
    extra_vars: dict[str, Any],
    inventory: dict[str, Any] | str,
    callback: HttpUrl | None,
    progress: HttpUrl | None,
    *,
    progress_is_incremental: bool,
) -> UUID:
    """Run an Ansible playbook against a specified inventory.

    Args:
        playbook_path (Path): Path to the playbook to be executed.
        extra_vars (dict[str, Any]): Any extra vars needed for the playbook to run.
        inventory (dict[str, Any] | str): The inventory that the playbook is executed against.
        callback (HttpUrl, optional): Callback URL where the playbook should send a status update when execution is
            completed. This is used e.g. for Workflow Orchestrator to continue with the next step in a workflow.
        progress (HttpUrl, optional): URL where the playbook should send periodical status updates as the execution
            progresses.
        progress_is_incremental (bool): `True` if the progress updates should only contain the latest info. `False` if
            the progress update should contain the complete history of the playbook execution.

    """
    job_id = uuid4()
    callback_str = None
    progress_str = None
    if callback:
        callback_str = str(callback)
    if progress:
        progress_str = str(progress)

    if settings.EXECUTOR == ExecutorType.THREADPOOL:
        executor = get_thread_pool()
        executor_handle = executor.submit(
            run_playbook_proc_task,
            str(job_id),
            str(playbook_path),
            extra_vars,
            inventory,
            callback_str,
            progress_str,
            progress_is_incremental=progress_is_incremental,
        )
        if settings.TESTING:
            executor_handle.result()

    elif settings.EXECUTOR == ExecutorType.WORKER:
        run_playbook_proc_task.delay(
            str(job_id),
            str(playbook_path),
            extra_vars,
            inventory,
            callback_str,
            progress_str,
            progress_is_incremental=progress_is_incremental,
        )

    return job_id
