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

# Transport options that let the Redis broker connection survive a broker switch-over (for
# example a virtual IP moving between Redis nodes) and reconnect automatically instead of getting
# stuck on a dead connection. ``broker_channel_error_retry`` additionally makes the worker treat
# channel errors (such as Redis ``ReadOnlyError`` from a node demoted to read-only replica) as
# recoverable, so it redials instead of failing permanently. The Redis result store does not
# read these from transport options and only honors the top-level ``redis_*`` settings passed
# below. None of this ties LSO to Redis: with another broker or result store (for example
# RabbitMQ or ``rpc://``) these options are simply ignored by the transport that does not know
# them.
redis_transport_options = {
    "socket_keepalive": settings.CELERY_REDIS_SOCKET_KEEPALIVE,
    "health_check_interval": settings.CELERY_REDIS_HEALTH_CHECK_INTERVAL,
    "retry_on_timeout": settings.CELERY_REDIS_RETRY_ON_TIMEOUT,
}

celery.conf.update(
    result_expires=settings.CELERY_RESULT_EXPIRES,
    worker_prefetch_multiplier=1,
    worker_send_task_event=True,
    task_send_sent_event=True,
    redbeat_redis_url=settings.CELERY_BROKER_URL,
    broker_connection_retry=settings.CELERY_BROKER_CONNECTION_RETRY,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=settings.CELERY_BROKER_CONNECTION_MAX_RETRIES,
    broker_channel_error_retry=settings.CELERY_BROKER_CHANNEL_ERROR_RETRY,
    broker_transport_options=redis_transport_options,
    redis_socket_keepalive=settings.CELERY_REDIS_SOCKET_KEEPALIVE,
    redis_retry_on_timeout=settings.CELERY_REDIS_RETRY_ON_TIMEOUT,
    redis_socket_timeout=settings.CELERY_REDIS_SOCKET_TIMEOUT,
    redis_socket_connect_timeout=settings.CELERY_REDIS_SOCKET_CONNECT_TIMEOUT,
    redis_backend_health_check_interval=settings.CELERY_REDIS_HEALTH_CHECK_INTERVAL,
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
