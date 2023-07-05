from typing import TextIO

TEST_CALLBACK_URL = "https://fqdn.abc.xyz/api/resume"


def test_ansible_runner_run(**kwargs):
    class Runner:
        def __init__(self):
            self.status = "success"
            self.rc = 0
            self.stdout = TextIO()

    return Runner()
