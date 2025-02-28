import tempfile
from contextlib import contextmanager
from pathlib import Path

from lso.config import ExecutorType, settings


@contextmanager
def temporary_executor(executor_type: ExecutorType):
    original_executor = settings.EXECUTOR
    settings.EXECUTOR = executor_type
    try:
        yield
    finally:
        settings.EXECUTOR = original_executor


@contextmanager
def temp_executable_env(executor_type: ExecutorType) -> Path:
    """Sets up a temporary executables environment and adjusts the executor type."""
    original_executable_dir = settings.EXECUTABLES_ROOT_DIR
    try:
        with temporary_executor(executor_type), tempfile.TemporaryDirectory() as exec_dir:
            settings.EXECUTABLES_ROOT_DIR = exec_dir
            yield Path(exec_dir)
    finally:
        settings.EXECUTABLES_ROOT_DIR = original_executable_dir
