import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

import lso


@pytest.fixture
def good_config_data():
    return {
        'collection-name': 'organisation.collection'
    }


@pytest.fixture
def bad_config_data():
    return {
        'bogus-key': 'nothing useful'
    }


@pytest.fixture
def config_file(good_config_data):
    with tempfile.NamedTemporaryFile(mode='w') as f:
        f.write(json.dumps(good_config_data))
        f.flush()
        os.environ['SETTINGS_FILENAME'] = f.name
        yield f.name


@pytest.fixture
def invalid_config_file(bad_config_data):
    with tempfile.NamedTemporaryFile(mode='w') as f:
        f.write(json.dumps(bad_config_data))
        f.flush()
        os.environ['SETTINGS_FILENAME'] = f.name
        yield f.name


@pytest.fixture
def client(config_file):
    app = lso.create_app()
    yield TestClient(app)  # wait here until calling context ends
