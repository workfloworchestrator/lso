import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import lso

TEST_CONFIG = {
    'collection-name': 'kvklink.echo',
    'test-role': 'kvklink.echo.echo_uptime'
}


@pytest.fixture
def config_data():
    """
    valid config data used to start the server
    """
    return {
        'ansible_playbooks_root_dir': '/'
    }


@pytest.fixture
def config_file(config_data):
    """
    Fixture that yields a filename that contains a valid configuration

    :return: Path to valid configuration file
    """
    with tempfile.NamedTemporaryFile(mode='w') as file:
        file.write(json.dumps(config_data))
        file.flush()
        yield file.name


@pytest.fixture
def client(config_file):
    """
    returns a client that can be used to test the server
    """
    os.environ['SETTINGS_FILENAME'] = config_file
    app = lso.create_app()
    yield TestClient(app)  # wait here until calling context ends
