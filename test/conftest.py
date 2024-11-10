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
import os
import tempfile
from collections.abc import Callable
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from faker import Faker
from fastapi.testclient import TestClient


def pytest_configure() -> None:
    """Configure environment variables for testing before the session starts."""
    tempdir = tempfile.TemporaryDirectory()

    # Create required YAML files for the unit tests
    (Path(tempdir.name) / "placeholder.yaml").touch()

    # Set environment variables for the test session
    os.environ["ANSIBLE_PLAYBOOKS_ROOT_DIR"] = tempdir.name
    os.environ["TESTING"] = "true"

    # Register finalizers to clean up after tests are done
    def cleanup() -> None:
        tempdir.cleanup()
        del os.environ["ANSIBLE_PLAYBOOKS_ROOT_DIR"]
        del os.environ["TESTING"]

    pytest.session_cleanup = cleanup


@pytest.fixture
def mocked_ansible_runner_run() -> Callable:
    class Runner:
        def __init__(self) -> None:
            self.status = "success"
            self.rc = 0
            self.stdout = StringIO("[{'step one': 'results'}, {'step two': 2}]")

    def run(*args: Any, **kwargs: Any) -> Runner:  # noqa: ARG001
        return Runner()

    return run


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Return a client that can be used to test the server."""
    from lso import create_app  # noqa: PLC0415

    app = create_app()
    return TestClient(app)  # wait here until calling context ends


@pytest.fixture(scope="session")
def faker() -> Faker:
    return Faker(locale="en_GB")
