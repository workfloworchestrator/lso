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

from concurrent.futures import ThreadPoolExecutor

from lso.config import settings

_executor = None


def get_thread_pool() -> ThreadPoolExecutor:
    """Initialize or return a cached ThreadPoolExecutor for local asynchronous execution."""
    global _executor  # noqa: PLW0603
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=settings.MAX_THREAD_POOL_WORKERS)

    return _executor
