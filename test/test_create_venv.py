import os
import subprocess


def test_create_venv_and_run_playbook(temp_ansible_env, temp_ansible_playbook):
    #  Run Ansible dummy playbook
    playbook_run = subprocess.run(
        [temp_ansible_env, '-i', 'localhost,', temp_ansible_playbook, '--connection=local'],
        capture_output=True
    )

    assert ' '.join(playbook_run.stdout.decode().split()).endswith(
        'localhost : ok=3 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0'
    )

    assert playbook_run.returncode is 0
