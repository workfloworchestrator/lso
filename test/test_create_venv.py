import os
import subprocess
import tempfile

TEST_CONFIG = {
    'collection-name': 'kvklink.echo'
}


class VenvContextManager:
    path: str

    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix='lso-venv-')
        subprocess.check_call(['python3', '-m', 'venv', self.path])

        # Install pip dependencies
        pip_path = os.path.join(self.path, 'bin', 'pip')
        subprocess.check_call([pip_path, 'install', 'ansible', 'ansible_runner'])

        # Add Ansible Galaxy collection
        galaxy_path = os.path.join(self.path, 'bin', 'ansible-galaxy')
        subprocess.check_call([galaxy_path, 'collection', 'install', TEST_CONFIG['collection-name']])

        return self.path

    def __exit__(self, exc_type, exc_value, exc_tb):
        subprocess.check_call(['rm', '-fr', self.path])
        print(exc_type, exc_value, exc_tb, sep='\n')  # Print raised Exception, if present


def test_create_venv_and_run_playbook():
    with VenvContextManager() as venv_path:
        #  Run Ansible dummy playbook
        ansible_playbook_path = os.path.join(venv_path, 'bin', 'ansible-playbook')
        playbook_run = subprocess.check_output(
            [ansible_playbook_path, '-i', 'localhost,', 'playbook.yml', '--connection=local']).decode()

        assert ' '.join(playbook_run.split()).endswith(
            'localhost : ok=3 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0'
        )
