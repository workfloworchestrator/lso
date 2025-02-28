"""Utility functions for the LSO package."""

from concurrent.futures import ThreadPoolExecutor

from lso.config import settings

_executor = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Initialize or return a cached ThreadPoolExecutor for local asynchronous execution."""
    global _executor  # noqa: PLW0603
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=settings.MAX_THREAD_POOL_WORKERS)

    return _executor
