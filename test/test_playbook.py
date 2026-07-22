# Copyright 2024 GÉANT Vereniging.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
from pathlib import Path
from typing import Any

import pytest
import responses
from starlette import status

from lso.config import settings
from lso.playbook import run_playbook
from lso.tasks import run_playbook_proc_task

TEST_CALLBACK_URL = "http://localhost/callback"
TEST_PROGRESS_URL = "http://localhost/progress"


@responses.activate
def test_playbook_execution() -> None:
    callback = responses.post(TEST_CALLBACK_URL)
    run_playbook(
        playbook_path=Path(__file__).parent / "test-playbook.yaml",
        extra_vars={},
        inventory="127.0.0.1",
        callback=TEST_CALLBACK_URL,
        progress=TEST_PROGRESS_URL,
        progress_is_incremental=True,
    )

    responses.assert_call_count(TEST_CALLBACK_URL, 1)
    assert callback.status == status.HTTP_200_OK


def test_run_playbook_passes_configured_timeout_to_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """The configured playbook timeout is passed to ansible_runner.run as the idle/read timeout."""
    configured_timeout = 123
    captured: dict[str, Any] = {}

    def fake_run(*_args: Any, **kwargs: Any) -> None:
        captured.update(kwargs)

    monkeypatch.setattr("lso.tasks.run", fake_run)
    monkeypatch.setattr(settings, "ANSIBLE_PLAYBOOK_TIMEOUT_SEC", configured_timeout)

    run_playbook_proc_task(
        job_id="job-1",
        playbook_path="/path/to/playbook.yaml",
        extra_vars={},
        inventory="127.0.0.1",
        callback=None,
        progress=None,
        progress_is_incremental=True,
    )

    assert captured["settings"]["pexpect_timeout"] == configured_timeout


@responses.activate
def test_run_playbook_crash_posts_failure_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    """If ansible_runner.run raises, a failed-status callback is POSTed before the exception is re-raised.

    This is the safety net that prevents a crashed run from orphaning a workflow in ``awaiting_callback``.
    """

    crash_message = "TIMEOUT(<pexpect.pty_spawn.spawn ...>)"

    def fake_run(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError(crash_message)

    monkeypatch.setattr("lso.tasks.run", fake_run)
    callback = responses.post(TEST_CALLBACK_URL)

    with pytest.raises(RuntimeError, match="TIMEOUT"):
        run_playbook_proc_task(
            job_id="job-xyz",
            playbook_path="/path/to/playbook.yaml",
            extra_vars={},
            inventory="127.0.0.1",
            callback=TEST_CALLBACK_URL,
            progress=None,
            progress_is_incremental=True,
        )

    responses.assert_call_count(TEST_CALLBACK_URL, 1)
    body = json.loads(callback.calls[0].request.body)
    assert body["status"] == "failed"
    assert body["job_id"] == "job-xyz"
    assert body["return_code"] != 0


@responses.activate
def test_run_playbook_result_callback_failure_not_double_posted(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failure delivering the result callback must not trigger a second, spurious failure callback.

    Once the run completes and its result callback has been attempted, the crash safety net must stay out of the
    way — otherwise a transient orchestrator hiccup would produce two conflicting callbacks for one job.
    """
    from io import StringIO  # noqa: PLC0415

    from lso.tasks import CallbackFailedError  # noqa: PLC0415

    class _Runner:
        status = "successful"
        rc = 0

        def __init__(self) -> None:
            self.stdout = StringIO("some output")

    def fake_run(*_args: Any, **kwargs: Any) -> None:
        # Simulate a completed run invoking its finished_callback, which POSTs the result callback.
        kwargs["finished_callback"](_Runner())

    monkeypatch.setattr("lso.tasks.run", fake_run)
    # Orchestrator rejects the result callback, so the finished handler raises CallbackFailedError.
    responses.post(TEST_CALLBACK_URL, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    with pytest.raises(CallbackFailedError):
        run_playbook_proc_task(
            job_id="job-2",
            playbook_path="/path/to/playbook.yaml",
            extra_vars={},
            inventory="127.0.0.1",
            callback=TEST_CALLBACK_URL,
            progress=None,
            progress_is_incremental=True,
        )

    # Exactly one POST — the result callback. No spurious second failure callback.
    responses.assert_call_count(TEST_CALLBACK_URL, 1)
