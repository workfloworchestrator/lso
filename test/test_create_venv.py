import os
import subprocess


def test_create_venv_and_run_playbook(temp_venv, temp_ansible_playbook):
    #  Run Ansible dummy playbook
    ansible_playbook_path = os.path.join(temp_venv, 'bin', 'ansible-playbook')
    playbook_run = subprocess.run(
        [ansible_playbook_path, '-i', 'localhost,', temp_ansible_playbook, '--connection=local'],
        capture_output=True
    )

    assert ' '.join(playbook_run.stdout.decode().split()).endswith(
        'localhost : ok=3 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0'
    )

    assert playbook_run.returncode is 0
