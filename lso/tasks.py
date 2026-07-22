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
from fastapi import HTTPException
from requests.exceptions import HTTPError

from lso.config import settings
from lso.schema import ExecutableRunResponse
from lso.worker import RUN_EXECUTABLE, RUN_PLAYBOOK, celery

logger = logging.getLogger(__name__)


class CallbackFailedError(HTTPException):
    """Exception raised when a callback URL can't be reached."""


def playbook_event_handler_factory(
    progress: str | None, *, progress_is_incremental: bool
) -> Callable[[dict], bool] | None:
    """Handle Ansible playbook run events.

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


class PlaybookFinishedHandler:
    """Report a finished Ansible playbook run to the callback URL from the original request.

    An instance is passed to `ansible-runner` as its `finished_callback` and invoked once when the run shuts down.
    It records in `reported` whether that report was made, so the caller can tell the run reached completion and
    avoid sending a second, conflicting callback if the run instead crashed before finishing.

    Args:
        callback (str, optional): The callback URL that the Ansible runner should report to. When not set, the
            handler is a no-op (nothing is POSTed).
        job_id (str): The job ID of this playbook run, used for reporting.

    Attributes:
        reported (bool): `True` once the handler has run, i.e. the playbook finished and its result callback was
            attempted (regardless of whether delivering it then succeeded).

    Raises:
        CallbackFailedError: If the callback to the external system has failed.

    """

    def __init__(self, callback: str | None, job_id: str) -> None:
        """Store the callback URL and job ID to report on when the playbook run finishes."""
        self._callback = callback
        self._job_id = job_id
        self.reported = False

    def __call__(self, runner: Runner) -> None:
        """Send one request with the playbook result to the callback URL."""
        # Record completion before attempting delivery, so a failure while POSTing does not let the caller's
        # crash safety net fire a second callback for the same job.
        self.reported = True
        if not self._callback:
            return

        playbook_output = [line for line in runner.stdout.read().split("\n") if line.strip()]
        payload = {
            "status": runner.status,
            "job_id": self._job_id,
            "output": playbook_output,
            "return_code": int(str(runner.rc)),
        }

        response = requests.post(str(self._callback), json=payload, timeout=settings.REQUEST_TIMEOUT_SEC)
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise CallbackFailedError(
                status_code=e.response.status_code, detail=f"{e.response.reason} for url: {e.request.url}"
            ) from e


def _post_playbook_failure_callback(callback: str | None, job_id: str, exc: BaseException) -> None:
    """Notify the orchestrator that a playbook run crashed before it could report its own result.

    Mirrors the payload shape of `PlaybookFinishedHandler` with a failed status so the workflow
    can transition out of `awaiting_callback` instead of hanging. Any error while delivering this callback is
    logged and swallowed, so it never masks the original exception that is being re-raised by the caller.

    Args:
        callback (str, optional): The callback URL that the Ansible runner should report to. No-op if not set.
        job_id (str): The job ID of this playbook run, used for reporting.
        exc (BaseException): The exception that escaped the runner, included in the callback output for diagnostics.

    """
    if not callback:
        return

    payload = {
        "status": "failed",
        "job_id": job_id,
        "output": [f"Ansible playbook run failed: {exc}"],
        "return_code": -1,
    }
    try:
        requests.post(str(callback), json=payload, timeout=settings.REQUEST_TIMEOUT_SEC)
    except requests.RequestException:
        logger.exception("Failed to POST failure callback to %s for job_id=%s", callback, job_id)


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
        playbook_path (str): Path to the playbook to be executed.
        extra_vars (dict[str, Any]): Extra variables to pass to the playbook.
        inventory (dict[str, Any] | str): Inventory to run the playbook against.
        callback (str, optional): Callback URL for status update.
        progress (str, optional): URL for sending progress updates.
        progress_is_incremental (bool): Whether progress updates include all past progress.

    """
    msg = f"playbook_path: {playbook_path}, callback: {callback}"
    logger.info(msg)

    finished_handler = PlaybookFinishedHandler(callback, job_id)
    try:
        run(
            playbook=playbook_path,
            inventory=inventory,
            extravars=extra_vars,
            event_handler=playbook_event_handler_factory(progress, progress_is_incremental=progress_is_incremental),
            finished_callback=finished_handler,
            settings={"pexpect_timeout": settings.ANSIBLE_PLAYBOOK_TIMEOUT_SEC},
        )
    except Exception as exc:
        # Safety net: if the runner crashes before finished_handler runs (e.g. a pexpect read timeout), no result
        # is ever POSTed and the orchestrator's workflow orphans in `awaiting_callback`. Notify the orchestrator
        # of the failure before re-raising so the workflow can never hang indefinitely. `finished_handler.reported`
        # guards against a second, conflicting callback when the run completed but delivering its result failed.
        logger.exception("Ansible playbook run for job_id=%s crashed", job_id)
        if not finished_handler.reported:
            _post_playbook_failure_callback(callback, job_id, exc)
        raise


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

        response = requests.post(str(callback), json=payload, timeout=settings.REQUEST_TIMEOUT_SEC)
        try:
            response.raise_for_status()
        except HTTPError as e:
            raise CallbackFailedError(
                status_code=e.response.status_code, detail=f"{e.response.reason} for url: {e.request.url}"
            ) from e
