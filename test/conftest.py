import json
import os
import tempfile
from typing import Any, Generator

import pytest
from faker import Faker
from fastapi.testclient import TestClient

import lso


@pytest.fixture(scope="session")
def config_data() -> dict[str, str]:
    """Start the server with valid configuration data."""
    return {"ansible_playbooks_root_dir": "/"}


@pytest.fixture(scope="session")
def config_file(config_data: dict[str, str]) -> Generator[str, Any, None]:
    """Fixture that will yield a filename that contains a valid configuration.

    :return: Path to valid configuration file
    """
    with tempfile.NamedTemporaryFile(mode="w") as file:
        file.write(json.dumps(config_data))
        file.flush()
        yield file.name


@pytest.fixture(scope="session")
def client(config_file: str) -> Generator[TestClient, Any, None]:
    """Return a client that can be used to test the server."""
    os.environ["SETTINGS_FILENAME"] = config_file
    app = lso.create_app()
    yield TestClient(app)  # wait here until calling context ends


@pytest.fixture(scope="session")
def faker() -> Faker:
    return Faker(locale="en_GB")
