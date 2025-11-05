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

import responses
from starlette import status

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
