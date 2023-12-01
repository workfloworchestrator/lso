import json
import os
import tempfile
from collections.abc import Callable, Generator
from io import StringIO
from typing import Any
from unittest.mock import patch

import pytest
from faker import Faker
from fastapi.testclient import TestClient

import lso


@pytest.fixture()
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
def configuration_data() -> dict[str, str]:
    """Start the server with valid configuration data."""
    return {"ansible_playbooks_root_dir": "/app/gap/collections/ansible_collections/geant/gap_ansible/playbooks"}


@pytest.fixture(scope="session")
def data_config_filename(configuration_data: dict[str, str]) -> Generator[str, Any, None]:
    """Fixture that will yield a filename that contains a valid configuration.

    :return: Path to valid configuration file
    """
    with tempfile.NamedTemporaryFile(mode="w") as file:
        file.write(json.dumps(configuration_data))
        file.flush()
        yield file.name


@pytest.fixture(scope="session")
def client(data_config_filename: str) -> TestClient:
    """Return a client that can be used to test the server."""
    os.environ["SETTINGS_FILENAME"] = data_config_filename
    app = lso.create_app()
    return TestClient(app)  # wait here until calling context ends


@pytest.fixture(scope="session")
def faker() -> Faker:
    return Faker(locale="en_GB")


@pytest.fixture(scope="session", autouse=True)
def path_exists() -> bool:
    """A patch that prevents all test requests from failing since the playbook file does not exist on the filesystem."""
    with patch("pathlib.Path.exists") as mock_patch:
        mock_patch.return_value = True

        yield mock_patch
