# Copyright 2024-2025 GÉANT Vereniging.
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

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import HTTPException, status

from lso.config import settings

_executor = None

#: Characters a caller-supplied executable or playbook name may consist of. Such a name is only ever used as a
#: filesystem path, and for an executable as `argv[0]` of a subprocess started without a shell, so a shell
#: metacharacter in it cannot currently do anything. This allowlist keeps that true should a call site ever
#: gain a shell, and costs nothing today: ordinary names are already within it.
SAFE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+$")


def get_thread_pool() -> ThreadPoolExecutor:
    """Initialize or return a cached ThreadPoolExecutor for local asynchronous execution."""
    global _executor  # noqa: PLW0603
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=settings.MAX_THREAD_POOL_WORKERS)

    return _executor


def resolve_within_root(root_dir: str, name: Path) -> Path:
    """Resolve a caller-supplied `name` inside `root_dir`, rejecting anything that escapes it.

    `Path(root_dir) / name` offers no containment on its own: `pathlib` discards `root_dir` entirely when `name`
    is absolute, and `..` segments walk out of it. Both sides are resolved before being compared, so that a
    symlinked root directory (a symlinked `/opt` or data mount is common in a container) does not reject
    names that are in fact contained.

    Resolving follows symlinks, so a symlink inside `root_dir` pointing outside of it is rejected as well.

    `name` is additionally held to `SAFE_NAME_PATTERN`, which is defence in depth rather than a fix for
    anything reachable today.

    Args:
        root_dir (str): The configured directory that `name` has to stay inside of.
        name (Path): The caller-supplied name to resolve against `root_dir`.

    Returns:
        The resolved path, guaranteed to lie inside `root_dir`.

    Raises:
        HTTPException: Raises a 400 if `name` holds characters outside `SAFE_NAME_PATTERN`, or if the resolved
            path lies outside `root_dir`.

    """
    if not SAFE_NAME_PATTERN.match(str(name)):
        msg = f"Path '{name}' contains characters that are not allowed."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    root = Path(root_dir).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        # Deliberately echoes only what the caller sent: naming the resolved path here would disclose the
        # server's filesystem layout to whoever probes the endpoint.
        msg = f"Path '{name}' is outside the configured root directory."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    return path
