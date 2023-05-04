"""
Test creating a temporary venv and running a dummy Ansible playbook.
"""

import subprocess


def test_run_playbook(ansible_playbook_bin, playbook_filename):
    """
    Run an ansible playbook in a temporary venv

    TODO: figure out how to use this venv with ansible_runner
    TODO: call the ansible_runner.run thread proc

    :param ansible_playbook_bin: Fixture that points to a temporary venv with
    Ansible installed.
    :param playbook_filename: Fixture that points to a dummy Ansible
    playbook in a temporary location.
    """
    playbook_run = subprocess.run(
        [
            ansible_playbook_bin,
            '-i', 'localhost,',
            playbook_filename,
            '--connection=local',
            '-e', 'ansible_remote_tmp=/tmp'
        ],
        capture_output=True,
        check=False
    )

    assert ' '.join(playbook_run.stdout.decode().split()).endswith(
        'ok=3 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0'
    )

    assert playbook_run.returncode == 0
