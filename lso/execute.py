"""Module for handling the execution of arbitrary executables."""

import uuid
from pathlib import Path

from pydantic import HttpUrl

from lso.config import ExecutorType, settings
from lso.tasks import run_executable_proc_task
from lso.utils import get_thread_pool


def get_executable_path(executable_name: Path) -> Path:
    """Return the full path of an executable, based on the configured EXECUTABLES_ROOT_DIR."""
    return Path(settings.EXECUTABLES_ROOT_DIR) / executable_name


def run_executable(executable_path: Path, args: list[str], callback: HttpUrl) -> uuid.UUID:
    """Dispatch the task for executing an arbitrary executable remotely.

    Uses a ThreadPoolExecutor (for local execution) or a Celery worker (for distributed tasks).
    """
    job_id = uuid.uuid4()
    if settings.EXECUTOR == ExecutorType.THREADPOOL:
        executor = get_thread_pool()
        future = executor.submit(run_executable_proc_task, str(job_id), str(executable_path), args, str(callback))
        if settings.TESTING:
            future.result()
    elif settings.EXECUTOR == ExecutorType.WORKER:
        run_executable_proc_task.delay(str(job_id), str(executable_path), args, str(callback))
    return job_id
