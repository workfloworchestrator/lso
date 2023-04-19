"""
Test creating a temporary venv and running a dummy Ansible playbook.
"""

import subprocess


def test_create_venv_and_run_playbook(temp_ansible_env, temp_ansible_playbook):
    """
    Test method that takes an Ansible venv and a playbook as inputs, both are
    fixtures provided by pytest.

    :param temp_ansible_env: Fixture that points to a temporary venv with
    Ansible installed.
    :param temp_ansible_playbook: Fixture that points to a dummy Ansible
    playbook in a temporary location.
    """
    playbook_run = subprocess.run(
        [temp_ansible_env, '-i', 'localhost,', temp_ansible_playbook,
         '--connection=local'],
        capture_output=True,
        check=False
    )

    assert ' '.join(playbook_run.stdout.decode().split()).endswith(
        'ok=3 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0'
    )

    assert playbook_run.returncode == 0
