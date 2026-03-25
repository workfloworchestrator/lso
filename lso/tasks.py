# Copyright 2024-2026 GÉANT Vereniging.
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

"""Module defines tasks for executing Ansible playbooks asynchronously using Celery.

The primary task, `run_playbook_proc_task`, runs an Ansible playbook and sends a POST request with
the results to a specified callback URL.
"""

import logging
from collections.abc import Callable
from typing import Any
from uuid import UUID

import requests
from ansible_runner import Runner, run
from starlette import status

from lso.config import settings
from lso.schema import ExecutableRunResponse
from lso.worker import RUN_EXECUTABLE, RUN_PLAYBOOK, celery

logger = logging.getLogger(__name__)


class CallbackFailedError(Exception):
    """Exception raised when a callback url can't be reached."""


def playbook_event_handler_factory(
    progress: str | None, *, progress_is_incremental: bool
) -> Callable[[dict], bool] | None:
    """Create an event handler for Ansible playbook runs.

    This is used to send incremental progress updates to the external system that called for this playbook to be run.

    Args:
        progress (str, optional): The progress URL where the external system expects to receive updates.
        progress_is_incremental (bool): Whether progress updates are sent incrementally, or contain the whole history
            of event data.

    """
    events_stdout = []

    def _playbook_event_handler(event: dict) -> bool:
        event_data = event["stdout"].strip()
        if not event_data:
            return False

        event_data_lines = event_data.split("\r\n")
        if progress_is_incremental:
            emit_body = event_data_lines
        else:
            events_stdout.extend(event_data_lines)
            emit_body = events_stdout

        requests.post(str(progress), json={"progress": emit_body}, timeout=settings.REQUEST_TIMEOUT_SEC)
        return True

    if progress:
        return _playbook_event_handler
    return None


def playbook_finished_handler_factory(callback: str | None, job_id: str) -> Callable[[Runner], None] | None:
    """Create an event handler for finished Ansible playbook runs.

    Once Ansible runner is finished, it will call the handler method created by this factory before teardown.

    Args:
        callback (str, optional): The callback URL that the Ansible runner should report to.
        job_id (str): The job ID of this playbook run, used for reporting.

    Returns:
        A handler method that sends one request to the callback URL.

    Raises:
        CallbackFailedError: If the callback to the external system has failed.

    """

    def _playbook_finished_handler(runner: Runner) -> None:
        playbook_output = runner.stdout.read().split("\n")
        playbook_output = [line for line in playbook_output if line.strip()]

        payload = {
            "status": runner.status,
            "job_id": job_id,
            "output": playbook_output,
            "return_code": int(runner.rc),
        }

        response = requests.post(str(callback), json=payload, timeout=settings.REQUEST_TIMEOUT_SEC)
        if not (status.HTTP_200_OK <= response.status_code < status.HTTP_300_MULTIPLE_CHOICES):
            msg = f"Callback failed: {response.text}, url: {callback}"
            raise CallbackFailedError(msg)

    if callback:
        return _playbook_finished_handler
    return None


@celery.task(name=RUN_PLAYBOOK)  # type: ignore[untyped-decorator]
def run_playbook_proc_task(
    job_id: str,
    playbook_path: str,
    extra_vars: dict[str, Any],
    inventory: dict[str, Any] | str,
    callback: str | None,
    progress: str | None,
    *,
    progress_is_incremental: bool,
) -> None:
    """Celery task to run a playbook.

    Args:
        job_id (str): Identifier of the job being executed.
        playbook_path (str): Path to the playbook to be exectuted.
        extra_vars (dict[str, Any]): Extra variables to pass to the playbook.
        inventory (dict[str, Any] | str): Inventory to run the playbook against.
        callback (str, optional): Callback URL for status update.
        progress (str, optional): URL for sending progress updates.
        progress_is_incremental (bool): Whether progress updates include all past progress.

    """
    msg = f"playbook_path: {playbook_path}, callback: {callback}"
    logger.info(msg)
    run(
        playbook=playbook_path,
        inventory=inventory,
        extravars=extra_vars,
        event_handler=playbook_event_handler_factory(progress, progress_is_incremental=progress_is_incremental),
        finished_callback=playbook_finished_handler_factory(callback, job_id),
    )


@celery.task(name=RUN_EXECUTABLE)  # type: ignore[untyped-decorator]
def run_executable_proc_task(job_id: str, executable_path: str, args: list[str], callback: str | None) -> None:
    """Celery task to run an arbitrary executable and notify via callback.

    Executes the executable with the provided arguments and posts back the result if a callback URL is provided.

    Args:
        job_id (str): Identifier of the job being executed.
        executable_path (str): Path to the executable to be executed.
        args (list[str]): Arguments that are passed to the executable.
        callback (str, optional): Callback URL for status update.

    Raises:
        CallbackFailedError: If the callback to the external system has failed.

    """
    from lso.execute import run_executable_sync  # noqa: PLC0415

    msg = f"Executing executable: {executable_path} with args: {args}, callback: {callback}"
    logger.info(msg)
    result = run_executable_sync(executable_path, args)

    if callback:
        payload = ExecutableRunResponse(
            job_id=UUID(job_id),
            result=result,
        ).model_dump(mode="json")

        def _raise_callback_error(message: str, error: Exception | None = None) -> None:
            if error:
                raise CallbackFailedError(message) from error
            raise CallbackFailedError(message)

        try:
            response = requests.post(str(callback), json=payload, timeout=settings.REQUEST_TIMEOUT_SEC)
            if not (status.HTTP_200_OK <= response.status_code < status.HTTP_300_MULTIPLE_CHOICES):
                msg = f"Callback failed: {response.text}, url: {callback}"
                _raise_callback_error(msg)
        except Exception as e:
            error_msg = f"Callback error: {e}"
            logger.exception(error_msg)
            _raise_callback_error(error_msg, e)
