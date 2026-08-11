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

"""Module for loading and managing configuration settings for the LSO app.

Uses `pydantic`'s `BaseSettings` to load settings from environment variables.
"""

import os
from enum import Enum

from pydantic_settings import BaseSettings


class ExecutorType(Enum):
    """Enumerator representing the types of executors available for task execution."""

    WORKER = "celery"
    THREADPOOL = "threadpool"


class Config(BaseSettings):
    """The set of parameters required for running :term:`LSO`.

    Attributes:
        TESTING (bool, optional): `True` if running in a testing environment, `False` otherwise.
        ANSIBLE_PLAYBOOKS_ROOT_DIR (str): Absolute path to the location where Ansible playbooks are stored.
        EXECUTABLES_ROOT_DIR (str): Absolute path to the location where executables are stored.
        EXECUTOR (ExecutorType, optional): The executor type that LSO uses.
        MAX_THREAD_POOL_WORKERS (int, optional): The amount of threads in the pool, if using the thread pool executor.
        REQUEST_TIMEOUT_SEC (int, optional): HTTP Timeout, in seconds.
        CELERY_BROKER_URL (str, optional): Celery broker URL, required when using the Celery executor.
        CELERY_RESULT_BACKEND (str, optional): Celery result backend URL, required when using the Celery executor.
        CELERY_RESULT_EXPIRES (int, optional): Celery result expiration timeout, in seconds.
        CELERY_BROKER_CONNECTION_RETRY (bool, optional): Retry re-establishing the broker connection at runtime.
        CELERY_BROKER_CONNECTION_MAX_RETRIES (int | None, optional): Max broker reconnection attempts; ``None`` retries
            indefinitely (the Celery broker transport treats ``0`` as "fail on the first error").
        CELERY_BROKER_CHANNEL_ERROR_RETRY (bool, optional): Treat broker channel errors (such as Redis
            ``ReadOnlyError`` from a node demoted to read-only replica) as recoverable and reconnect.
        CELERY_REDIS_SOCKET_KEEPALIVE (bool, optional): Enable TCP keep-alive on the Redis broker connection.
        CELERY_REDIS_HEALTH_CHECK_INTERVAL (int, optional): Seconds between Redis broker connection health checks.
        CELERY_REDIS_RETRY_ON_TIMEOUT (bool, optional): Retry a Redis command that timed out instead of dropping it.
        CELERY_REDIS_SOCKET_TIMEOUT (float, optional): Timeout, in seconds, for Redis socket operations on the
            broker and result-store connections, so a socket that died without a TCP reset packet reaching
            the client fails instead of blocking the worker forever.
        CELERY_REDIS_SOCKET_CONNECT_TIMEOUT (float, optional): Timeout, in seconds, for establishing a Redis
            broker or result-store socket connection.
        CELERY_REDIS_SOCKET_KEEPALIVE_IDLE (int, optional): Seconds a Redis connection is idle before TCP
            keep-alive probing starts (``TCP_KEEPIDLE``). The kernel default of 7200 seconds is far too slow to
            detect a broker connection that died silently during a switch-over.
        CELERY_REDIS_SOCKET_KEEPALIVE_INTERVAL (int, optional): Seconds between TCP keep-alive probes on an idle
            Redis connection (``TCP_KEEPINTVL``).
        CELERY_REDIS_SOCKET_KEEPALIVE_COUNT (int, optional): Failed TCP keep-alive probes after which the kernel
            declares a Redis connection dead (``TCP_KEEPCNT``).
        WORKER_QUEUE_NAME (str, optional): Celery worker queue name.
        EXECUTABLE_TIMEOUT_SEC (int, optional): Timeout period for an executable, in seconds.
        ANSIBLE_PLAYBOOK_TIMEOUT_SEC (int, optional): Idle/read timeout, in seconds, for the `ansible-runner` output
            pipe. This is passed to `ansible-runner` as its `pexpect_timeout` so that a transient gap in playbook
            output (e.g. a slow-but-healthy device operation) does not abort an otherwise-successful run. Defaults to
            a large value to tolerate such gaps; the underlying job is still bounded by the run itself.

    """

    TESTING: bool = True
    ANSIBLE_PLAYBOOKS_ROOT_DIR: str = "/path/to/ansible/playbooks"
    EXECUTABLES_ROOT_DIR: str = "/path/to/executables"
    EXECUTOR: ExecutorType = ExecutorType.THREADPOOL
    MAX_THREAD_POOL_WORKERS: int = min(32, (os.cpu_count() or 1) + 4)
    REQUEST_TIMEOUT_SEC: int = 10
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_RESULT_EXPIRES: int = 3600
    CELERY_BROKER_CONNECTION_RETRY: bool = True
    CELERY_BROKER_CONNECTION_MAX_RETRIES: int | None = None
    CELERY_BROKER_CHANNEL_ERROR_RETRY: bool = True
    CELERY_REDIS_SOCKET_KEEPALIVE: bool = True
    CELERY_REDIS_HEALTH_CHECK_INTERVAL: int = 10
    CELERY_REDIS_RETRY_ON_TIMEOUT: bool = True
    CELERY_REDIS_SOCKET_TIMEOUT: float = 30.0
    CELERY_REDIS_SOCKET_CONNECT_TIMEOUT: float = 10.0
    CELERY_REDIS_SOCKET_KEEPALIVE_IDLE: int = 30
    CELERY_REDIS_SOCKET_KEEPALIVE_INTERVAL: int = 10
    CELERY_REDIS_SOCKET_KEEPALIVE_COUNT: int = 3
    WORKER_QUEUE_NAME: str | None = None
    EXECUTABLE_TIMEOUT_SEC: int = 300
    ANSIBLE_PLAYBOOK_TIMEOUT_SEC: int = 300


settings = Config()
