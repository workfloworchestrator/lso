# Copyright 2023-2024 GÉANT Vereniging.
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
    """Enum representing the types of executors available for task execution."""

    WORKER = "celery"
    THREADPOOL = "threadpool"


class Config(BaseSettings):
    """The set of parameters required for running :term:`LSO`."""

    TESTING: bool = False
    ANSIBLE_PLAYBOOKS_ROOT_DIR: str = "/path/to/ansible/playbooks"
    EXECUTOR: ExecutorType = ExecutorType.THREADPOOL
    MAX_THREAD_POOL_WORKERS: int = min(32, (os.cpu_count() or 1) + 4)
    REQUEST_TIMEOUT_SEC: int = 10
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_RESULT_EXPIRES: int = 3600
    WORKER_QUEUE_NAME: str | None = None


settings = Config()
