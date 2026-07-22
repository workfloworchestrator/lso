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
from pathlib import Path
from unittest.mock import patch

import pytest
import responses
from pydantic import HttpUrl
from starlette import status

from lso.config import settings
from lso.playbook import run_playbook

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


@responses.activate
def test_playbook_crash_posts_failure_callback() -> None:
    """If Ansible runner crashes before the finished callback fires, a failure status must still be posted."""
    callback = responses.post(TEST_CALLBACK_URL)

    with patch("lso.tasks.run", side_effect=RuntimeError("boom")), pytest.raises(RuntimeError, match="boom"):
        run_playbook(
            playbook_path=Path(__file__).parent / "test-playbook.yaml",
            extra_vars={},
            inventory="127.0.0.1",
            callback=HttpUrl(TEST_CALLBACK_URL),
            progress=HttpUrl(TEST_PROGRESS_URL),
            progress_is_incremental=True,
        )

    responses.assert_call_count(TEST_CALLBACK_URL, 1)
    assert callback.status == status.HTTP_200_OK
    request_body = callback.calls[0].request.body
    assert request_body is not None
    body_text = request_body.decode() if isinstance(request_body, bytes) else request_body
    assert '"status": "failed"' in body_text


@responses.activate
def test_playbook_uses_configured_pexpect_timeout() -> None:
    """The configured pexpect timeout must be passed through to Ansible runner."""
    with patch("lso.tasks.run") as mock_run:
        run_playbook(
            playbook_path=Path(__file__).parent / "test-playbook.yaml",
            extra_vars={},
            inventory="127.0.0.1",
            callback=None,
            progress=None,
            progress_is_incremental=True,
        )

    passed_settings = mock_run.call_args.kwargs["settings"]
    assert passed_settings["pexpect_timeout"] == settings.ANSIBLE_PEXPECT_TIMEOUT_SEC
    assert passed_settings["idle_timeout"] is None
