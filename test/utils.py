import tempfile
from contextlib import contextmanager
from pathlib import Path

from pydantic import SecretStr

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
def auth_settings(*, active: bool = False, authorization_active: bool = False, api_key: str | None = None):
    """Apply security settings for the duration of a test, then put the originals back.

    The settings are one process-wide singleton, so a test that changed them and did not restore them would
    decide the outcome of every test that ran afterwards.
    """
    original = (settings.LSO_OAUTH2_ACTIVE, settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE, settings.LSO_API_KEY)
    settings.LSO_OAUTH2_ACTIVE = active
    settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE = authorization_active
    settings.LSO_API_KEY = SecretStr(api_key) if api_key is not None else None
    try:
        yield
    finally:
        settings.LSO_OAUTH2_ACTIVE, settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE, settings.LSO_API_KEY = original


@contextmanager
def temp_executable_env(executor_type: ExecutorType):
    """Sets up a temporary executables environment and adjusts the executor type."""
    original_executable_dir = settings.EXECUTABLES_ROOT_DIR
    try:
        with temporary_executor(executor_type), tempfile.TemporaryDirectory() as exec_dir:
            settings.EXECUTABLES_ROOT_DIR = exec_dir
            yield Path(exec_dir)
    finally:
        settings.EXECUTABLES_ROOT_DIR = original_executable_dir
