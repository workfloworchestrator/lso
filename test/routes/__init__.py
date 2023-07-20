from io import StringIO
from typing import Any

TEST_CALLBACK_URL = "https://fqdn.abc.xyz/api/resume"


class Runner:
    def __init__(self) -> None:
        self.status = "success"
        self.rc = 0
        self.stdout = StringIO("[{'step one': 'results'}, {'step two': 2}]")


def test_ansible_runner_run(**kwargs: Any) -> Runner:
    return Runner()
