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

"""Module that sets up LSO as a Celery worker."""

from celery import Celery
from celery.signals import worker_shutting_down

from lso.config import settings

RUN_PLAYBOOK = "lso.tasks.run_playbook_proc_task"
RUN_EXECUTABLE = "lso.tasks.run_executable_proc_task"

celery = Celery(
    "lso-worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    result_expires=settings.CELERY_RESULT_EXPIRES,
    worker_prefetch_multiplier=1,
    worker_send_task_event=True,
    task_send_sent_event=True,
    redbeat_redis_url=settings.CELERY_BROKER_URL,
    broker_connection_retry_on_startup=True,
    task_ignore_result=not settings.TESTING,
)

if settings.WORKER_QUEUE_NAME:
    celery.conf.task_routes = {
        RUN_PLAYBOOK: {"queue": settings.WORKER_QUEUE_NAME},
        RUN_EXECUTABLE: {"queue": settings.WORKER_QUEUE_NAME},
    }

# Ensure the task modules are imported so their ``@celery.task`` decorators register the tasks. The worker is started
# with ``-A lso.worker``, which does not otherwise import ``lso.tasks``; without this, the worker boots with an empty
# task registry and rejects every incoming task with "Received unregistered task". ``autodiscover_tasks`` is used
# instead of a top-level import to avoid the circular import between ``lso.worker`` and ``lso.tasks``.
celery.autodiscover_tasks(["lso"], related_name="tasks", force=True)


@worker_shutting_down.connect  # type: ignore[untyped-decorator]
def worker_shutting_down_handler(sig, how, exitcode, **kwargs) -> None:  # type: ignore[no-untyped-def] # noqa: ARG001
    """Handle the Celery worker shutdown event."""
    celery.close()
