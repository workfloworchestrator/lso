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

"""Module that gathers common API responses and data models."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import requests
from ansible_runner import Runner
from pydantic import HttpUrl
from starlette import status

from lso.config import ExecutorType, settings
from lso.tasks import run_playbook_proc_task
from lso.utils import CallbackFailedError, get_thread_pool

logger = logging.getLogger(__name__)


def get_playbook_path(playbook_name: Path) -> Path:
    """Get the path of a playbook on the local filesystem."""
    return Path(settings.ANSIBLE_PLAYBOOKS_ROOT_DIR) / playbook_name


def playbook_event_handler_factory(progress: str, *, progress_is_incremental: bool) -> Callable[[dict], bool]:
    """Create an event handler for Ansible playbook runs.

    This is used to send incremental progress updates to the external system that called for this playbook to be run.

    :param str progress: The progress URL where the external system expects to receive updates.
    :param bool progress_is_incremental: Whether progress updates are sent incrementally, or only contain the latest
                                         event data.
    :return Callable[[dict], bool]]: A handler method that processes every Ansible playbook event.
    """
    events_stdout = []

    def _playbook_event_handler(event: dict) -> bool:
        if progress_is_incremental:
            emit_body = event["stdout"].strip()
        else:
            events_stdout.append(event["stdout"].strip())
            emit_body = events_stdout

        requests.post(str(progress), json={"progress": emit_body}, timeout=settings.REQUEST_TIMEOUT_SEC)
        return True

    return _playbook_event_handler


def playbook_finished_handler_factory(callback: str, job_id: UUID) -> Callable[[Runner], None]:
    """Create an event handler for finished Ansible playbook runs.

    Once Ansible runner is finished, it will call the handler method created by this factory before teardown.

    :param str callback: The callback URL that ansible runner should report to.
    :param UUID job_id: The job ID of this playbook run, used for reporting.
    :return Callable[[Runner], None]: A handler method that sends one request to the callback URL.
    """

    def _playbook_finished_handler(runner: Runner) -> None:
        payload = {
            "status": runner.status,
            "job_id": str(job_id),
            "output": runner.stdout.readlines(),
            "return_code": int(runner.rc),
        }

        response = requests.post(str(callback), json=payload, timeout=settings.REQUEST_TIMEOUT_SEC)
        if not (status.HTTP_200_OK <= response.status_code < status.HTTP_300_MULTIPLE_CHOICES):
            msg = f"Callback failed: {response.text}, url: {callback}"
            raise CallbackFailedError(msg)

    return _playbook_finished_handler


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

    :param Path playbook_path: Playbook to be executed.
    :param dict[str, Any] extra_vars: Any extra vars needed for the playbook to run.
    :param dict[str, Any] | str inventory: The inventory that the playbook is executed against.
    :param HttpUrl callback: Callback URL where the playbook should send a status update when execution is completed.
                             This is used for workflow-orchestrator to continue with the next step in a workflow.
    :return UUID: Job ID of the launched playbook.
    """
    msg = f"playbook_path: {playbook_path}"
    job_id = uuid4()
    callback_str = None
    progress_str = None
    event_handler = None
    finished_callback = None

    if callback:
        callback_str = str(callback)
        msg += f", callback URL: {callback_str}"
        finished_callback = playbook_finished_handler_factory(callback_str, job_id)
    if progress:
        progress_str = str(progress)
        msg += f", progress URL: {progress_str}"
        event_handler = playbook_event_handler_factory(progress_str, progress_is_incremental=progress_is_incremental)

    logger.info(msg)

    if settings.EXECUTOR == ExecutorType.THREADPOOL:
        executor = get_thread_pool()
        executor_handle = executor.submit(
            run_playbook_proc_task, str(playbook_path), extra_vars, inventory, event_handler, finished_callback
        )
        if settings.TESTING:
            executor_handle.result()

    elif settings.EXECUTOR == ExecutorType.WORKER:
        run_playbook_proc_task.delay(
            str(playbook_path),
            extra_vars,
            inventory,
            event_handler,
            finished_callback,
        )

    return job_id
