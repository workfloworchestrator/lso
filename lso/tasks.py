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
from collections.abc import Callable
from typing import Any
from uuid import UUID

import requests
from ansible_runner import Runner, run
from starlette import status

from lso.config import settings
from lso.schema import ExecutableRunResponse
from lso.utils import CallbackFailedError
from lso.worker import RUN_EXECUTABLE, RUN_PLAYBOOK, celery

logger = logging.getLogger(__name__)


@celery.task(name=RUN_PLAYBOOK)  # type: ignore[misc]
def run_playbook_proc_task(
    playbook_path: str,
    extra_vars: dict[str, Any],
    inventory: dict[str, Any] | str,
    event_handler: Callable[[dict], bool] | None = None,
    finished_callback: Callable[[Runner], None] | None = None,
) -> None:
    """Celery task to run a playbook.

    :param str playbook_path: Path to the playbook to be executed.
    :param dict[str, Any] extra_vars: Extra variables to pass to the playbook.
    :param dict[str, Any] | str inventory: Inventory to run the playbook against.
    :param Callable[[dict], bool] event_handler: Event handler method that is executed on every event while the playbook
                                                 runs.
    :param Callable[[Runner], None] finished_callback: Callback handler method that is executed once the playbook run is
                                                       completed.
    :return: None
    """
    run(
        playbook=playbook_path,
        inventory=inventory,
        extravars=extra_vars,
        event_handler=event_handler,
        finished_callback=finished_callback,
    )


@celery.task(name=RUN_EXECUTABLE)  # type: ignore[misc]
def run_executable_proc_task(job_id: str, executable_path: str, args: list[str], callback: str | None) -> None:
    """Celery task to run an arbitrary executable and notify via callback.

    Executes the executable with the provided arguments and posts back the result if a callback URL is provided.
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
