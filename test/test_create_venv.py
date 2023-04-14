import os
import subprocess
import tempfile

TEST_CONFIG = {
    'collection-name': 'kvklink.echo'
}


def test_create_venv_and_run_playbook():
    #  Create a new venv
    venv_path = tempfile.mkdtemp(prefix='lso-venv-')
    subprocess.check_call(['python3', '-m', 'venv', venv_path])

    #  Install pip requirements and ansible
    pip_path = os.path.join(venv_path, 'bin', 'pip')
    requirements = '../requirements.txt'  # TODO: this should be changed when moving to codebase
    subprocess.check_call([pip_path, 'install', '-r', requirements])
    subprocess.check_call([pip_path, 'install', '-e', '..'])  # TODO: change path

    #  Add Ansible Galaxy collection
    subprocess.check_call(
        f"source {venv_path}/bin/activate; ansible-galaxy collection install {TEST_CONFIG['collection-name']}",
        shell=True
    )

    #  Run Ansible dummy playbook
    playbook_run = subprocess.check_output(
        f'source {venv_path}/bin/activate; ansible-playbook -i localhost, playbook.yml --connection=local',
        shell=True
    ).decode()

    #  Clean up the used venv
    subprocess.check_call(['rm', '-fr', venv_path])

    assert ' '.join(playbook_run.split()).endswith(
        'localhost : ok=3 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0'
    )
