#  pytest-ignore: redefined-outer-name
"""Pytest for testing valid and invalid configuration files
"""

import json
import os
import subprocess
import tempfile

import pytest
import yaml
from fastapi.testclient import TestClient

import lso

TEST_CONFIG = {
    'collection-name': 'kvklink.echo',
    'test-role': 'kvklink.echo.echo_uptime'
}


@pytest.fixture
def temp_ansible_playbook():
    """Write a sample Ansible playbook to a temporary file, and return the
    path to the new file.

    :return: Name of the temporary Playbook
    """
    with tempfile.NamedTemporaryFile(prefix='lso_playbook_', suffix='.yml',
                                     mode='w') as temp_playbook:
        yaml.dump([{
            'name': 'test-playbook',
            'hosts': 'all',
            'roles': [
                TEST_CONFIG['test-role']
            ]
        }], temp_playbook.file, sort_keys=False)

        temp_playbook.flush()
        yield temp_playbook.name


@pytest.fixture
def temp_ansible_env():
    """Fixture that yields a temporary folder with a venv that has Ansible
    installed

    :return: Path to venv with Ansible installed
    """
    with tempfile.TemporaryDirectory(prefix='lso_venv') as venv_dir:
        # Instantiate a new venv
        subprocess.check_call(['python3', '-m', 'venv', venv_dir])

        # Install pip dependencies
        pip_path = os.path.join(venv_dir, 'bin', 'pip')
        subprocess.check_call([pip_path, 'install', 'ansible',
                               'ansible_runner'])

        # Add Ansible Galaxy collection
        galaxy_path = os.path.join(venv_dir, 'bin', 'ansible-galaxy')
        subprocess.check_call([galaxy_path, 'collection', 'install',
                               TEST_CONFIG['collection-name']])
        # FIXME: download Ansible collections to a path inside the venv

        yield os.path.join(venv_dir, 'bin', 'ansible-playbook')


@pytest.fixture
def good_config_data():
    """Example of correct data used for testing
    """
    return {
        'collection-name': 'organisation.collection'
    }


@pytest.fixture
def bad_config_data():
    """Example of incorrect data used for testing
    """
    return {
        'bogus-key': 'nothing useful'
    }


@pytest.fixture
def config_file(good_config_data):
    """Fixture that yields a filename that contains a valid configuration

    :return: Path to valid configuration file
    """
    with tempfile.NamedTemporaryFile(mode='w') as file:
        file.write(json.dumps(good_config_data))
        file.flush()
        os.environ['SETTINGS_FILENAME'] = file.name
        yield file.name


@pytest.fixture
def invalid_config_file(bad_config_data):
    """Fixture that yields a filename that contains invalid configuration

    :return: Path to invalid configuration file
    """
    with tempfile.NamedTemporaryFile(mode='w') as file:
        file.write(json.dumps(bad_config_data))
        file.flush()
        os.environ['SETTINGS_FILENAME'] = file.name
        yield file.name


@pytest.fixture
def client(config_file):
    """Fixture that yields an instance of LSO
    """
    os.environ['SETTINGS_FILE'] = config_file
    app = lso.create_app()
    yield TestClient(app)  # wait here until calling context ends
