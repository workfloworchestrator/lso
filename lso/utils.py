# Copyright 2024-2026 GÉANT Vereniging.
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

"""Utility functions for the LSO package."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import HTTPException, status
from nwastdlib import file_utils
from nwastdlib.file_utils import PathOutsideRootError

from lso.config import settings

_executor = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Initialize or return a cached ThreadPoolExecutor for local asynchronous execution."""
    global _executor  # noqa: PLW0603
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=settings.MAX_THREAD_POOL_WORKERS)

    return _executor


def resolve_within_root(root_dir: str, name: Path) -> Path:
    """Resolve a caller-supplied `name` inside `root_dir`, rejecting anything that escapes it.

    Wraps `nwastdlib.file_utils.resolve_within_root`, translating its error into the 400 that LSO's API returns.

    Args:
        root_dir (str): The configured directory that `name` has to stay inside of.
        name (Path): The caller-supplied name to resolve against `root_dir`.

    Returns:
        The resolved path, guaranteed to lie inside `root_dir`.

    Raises:
        HTTPException: Raises a 400 if the resolved path lies outside `root_dir`.

    """
    try:
        return file_utils.resolve_within_root(root_dir, name)
    except PathOutsideRootError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
