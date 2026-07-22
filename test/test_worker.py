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

from lso.worker import RUN_EXECUTABLE, RUN_PLAYBOOK, celery


def test_worker_registers_tasks() -> None:
    """The Celery app must have the playbook and executable tasks registered.

    The worker is started with ``-A lso.worker``, so ``lso.worker`` is solely responsible for ensuring the task
    modules are imported. If this regresses, the worker boots with an empty registry and rejects every incoming task
    with "Received unregistered task", silently stalling any workflow that dispatches to it.
    """
    assert RUN_PLAYBOOK in celery.tasks
    assert RUN_EXECUTABLE in celery.tasks
