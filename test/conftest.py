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
def playbook_filename():
    """
    Write a sample Ansible playbook to a temporary file, and return the
    path to the new file.

    :return: full filename of the temporary Playbook
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
def ansible_playbook_bin():
    """
    Creates a virtual environment, installs ansible & a galaxy collection,
    and returns a path to the ansible-playbook executable

    :return: full path to ansible-playbook executable
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
                               TEST_CONFIG['collection-name'], '-p',
                               os.path.join(venv_dir, 'collections')])

        # Set the environment variable for the custom collections path
        os.environ['ANSIBLE_COLLECTIONS_PATH'] = \
            os.path.join(venv_dir, 'collections')

        yield os.path.join(venv_dir, 'bin', 'ansible-playbook')


@pytest.fixture
def config_data():
    """
    valid config data used to start the server
    """
    return {
        'collection': {
            'name': 'organisation.collection',
            'version': '1.2.3.4.5'
        }
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
