# Copyright 2026 GÉANT Vereniging.
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

from lso.config import settings
from lso.worker import RUN_EXECUTABLE, RUN_PLAYBOOK, celery


def test_worker_registers_tasks() -> None:
    """The Celery app must have the playbook and executable tasks registered.

    The worker is started with ``-A lso.worker``, so ``lso.worker`` is solely responsible for ensuring the task
    modules are imported. If this regresses, the worker boots with an empty registry and rejects every incoming task
    with "Received unregistered task", silently stalling any workflow that dispatches to it.
    """
    assert RUN_PLAYBOOK in celery.tasks
    assert RUN_EXECUTABLE in celery.tasks


def test_celery_broker_is_configured_to_self_heal_after_switch_over() -> None:
    """The Celery broker must retry and use keep-alive so a Redis broker switch-over self-heals.

    These assert the broker-resilience contract that lets the worker recover after a Redis broker switch-over (for
    example a virtual IP moving between Redis nodes) instead of getting stuck until a manual restart.
    """
    assert celery.conf.broker_connection_retry is True
    assert celery.conf.broker_connection_retry_on_startup is True
    # Kombu treats 0 as "fail on the first error"; only None retries indefinitely.
    assert celery.conf.broker_connection_max_retries is None
    # ReadOnlyError from a demoted replica is a channel error; the worker must redial on it.
    assert celery.conf.broker_channel_error_retry is True

    transport_options = celery.conf.broker_transport_options
    assert transport_options["socket_keepalive"] is True
    assert transport_options["retry_on_timeout"] is True
    assert transport_options["health_check_interval"] > 0

    # A switch-over kills connections without an RST reaching the client; without a socket
    # timeout, an unbounded recv() on such a half-open socket blocks the consumer restart
    # forever, before any of the retry settings above can engage.
    assert transport_options["socket_timeout"] > 0
    assert transport_options["socket_connect_timeout"] > 0
    # TCP keep-alive timing must be overridden: the kernel default (7200s idle) means a broker
    # connection that died silently would go unnoticed for up to 2 hours. Constant names differ
    # per platform (TCP_KEEPIDLE on Linux, TCP_KEEPALIVE on macOS), so assert on the values.
    keepalive_options = transport_options["socket_keepalive_options"]
    assert sorted(keepalive_options.values()) == [
        settings.CELERY_REDIS_SOCKET_KEEPALIVE_COUNT,
        settings.CELERY_REDIS_SOCKET_KEEPALIVE_INTERVAL,
        settings.CELERY_REDIS_SOCKET_KEEPALIVE_IDLE,
    ]

    # The Redis result store ignores transport options for connection parameters; it only honors
    # these top-level redis_* settings.
    assert celery.conf.redis_socket_keepalive is True
    assert celery.conf.redis_retry_on_timeout is True
    assert celery.conf.redis_socket_timeout > 0
    assert celery.conf.redis_socket_connect_timeout > 0
    assert celery.conf.redis_backend_health_check_interval > 0
