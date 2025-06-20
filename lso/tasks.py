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

"""Module defines tasks for executing Ansible playbooks asynchronously using Celery.

The primary task, `run_playbook_proc_task`, runs an Ansible playbook and sends a POST request with
the results to a specified callback URL.
"""

import logging
from typing import Any
from uuid import UUID

import ansible_runner
import requests
from starlette import status

from lso.config import settings
from lso.schema import ExecutableRunResponse
from lso.utils import run_executable_sync
from lso.worker import RUN_EXECUTABLE, RUN_PLAYBOOK, celery

logger = logging.getLogger(__name__)


class CallbackFailedError(Exception):
    """Exception raised when a callback url can't be reached."""


@celery.task(name=RUN_PLAYBOOK)  # type: ignore[misc]
def run_playbook_proc_task(
    job_id: str, playbook_path: str, extra_vars: dict[str, Any], inventory: dict[str, Any] | str, callback: str
) -> None:
    """Celery task to run a playbook.

    :param str job_id: Identifier of the job being executed.
    :param str playbook_path: Path to the playbook to be executed.
    :param dict[str, Any] extra_vars: Extra variables to pass to the playbook.
    :param dict[str, Any] | str inventory: Inventory to run the playbook against.
    :param HttpUrl callback: Callback URL for status updates.
    :return: None
    """
    msg = f"playbook_path: {playbook_path}, callback: {callback}"
    logger.info(msg)
    ansible_playbook_run = ansible_runner.run(playbook=playbook_path, inventory=inventory, extravars=extra_vars)

    payload = {
        "status": ansible_playbook_run.status,
        "job_id": job_id,
        "output": ansible_playbook_run.stdout.readlines(),
        "return_code": int(ansible_playbook_run.rc),
    }

    response = requests.post(str(callback), json=payload, timeout=settings.REQUEST_TIMEOUT_SEC)
    if not (status.HTTP_200_OK <= response.status_code < status.HTTP_300_MULTIPLE_CHOICES):
        msg = f"Callback failed: {response.text}, url: {callback}"
        raise CallbackFailedError(msg)


@celery.task(name=RUN_EXECUTABLE)  # type: ignore[misc]
def run_executable_proc_task(job_id: str, executable_path: str, args: list[str], callback: str) -> None:
    """Celery task to run an arbitrary executable and notify via callback.

    Executes the executable with the provided arguments and posts back the output and status.
    """
    msg = f"Executing executable: {executable_path} with args: {args}, callback: {callback}"
    logger.info(msg)
    result = run_executable_sync(executable_path, args)

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
