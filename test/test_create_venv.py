import os
import subprocess

from tempfile import TemporaryDirectory

TEST_CONFIG = {
    'collection-name': 'kvklink.echo'
}


def test_create_venv_and_run_playbook():
    with TemporaryDirectory() as venv_path:
        # Instantiate a new venv
        subprocess.check_call(['python3', '-m', 'venv', venv_path])

        # Install pip dependencies
        pip_path = os.path.join(venv_path, 'bin', 'pip')
        subprocess.check_call([pip_path, 'install', 'ansible', 'ansible_runner'])

        # Add Ansible Galaxy collection
        galaxy_path = os.path.join(venv_path, 'bin', 'ansible-galaxy')
        subprocess.check_call([galaxy_path, 'collection', 'install', TEST_CONFIG['collection-name']])

        #  Run Ansible dummy playbook
        ansible_playbook_path = os.path.join(venv_path, 'bin', 'ansible-playbook')
        playbook_run = subprocess.check_output(
            [ansible_playbook_path, '-i', 'localhost,', 'playbook.yml', '--connection=local']).decode()

        assert ' '.join(playbook_run.split()).endswith(
            'localhost : ok=3 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0'
        )
