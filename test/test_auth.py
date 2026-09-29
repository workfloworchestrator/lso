# Copyright 2023-2026 GÉANT Vereniging.
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
"""The authentication and authorization contracts themselves, with no application around them.

The project carries no async test plugin, and adding one for a handful of direct coroutine calls would be a
poor trade, so those are driven with `asyncio.run`. Everything that involves a request is exercised through
`TestClient` in the other security test modules.
"""

import asyncio

import pytest

from lso.auth import Authentication, AuthManager, Authorization, HttpBearerExtractor, IdTokenExtractor, NoAuth


def test_no_auth_identifies_nobody():
    """The default identifies no caller, rather than inventing one."""
    assert asyncio.run(NoAuth().authenticate(None)) is None


def test_no_auth_expresses_no_opinion():
    """The default bypasses rather than allowing, so nothing reads it as a positive decision."""
    assert asyncio.run(NoAuth().authorize(None, None)) is None


def test_manager_starts_out_bypassing():
    """A fresh manager enforces nothing, which is what makes an unconfigured LSO behave as it always did."""
    manager = AuthManager()

    assert isinstance(manager.extractor, HttpBearerExtractor)
    assert isinstance(manager.authentication, NoAuth)
    assert isinstance(manager.authorization, NoAuth)


def test_manager_slots_can_be_replaced():
    """Registering an implementation is a plain attribute set."""

    class Custom(Authentication, Authorization):
        async def authenticate(self, request, token=None):
            return {"sub": "custom"}

        async def authorize(self, request, user):
            return True

    class CustomExtractor(IdTokenExtractor):
        async def extract(self, request):
            return "a-token"

    manager = AuthManager()
    custom = Custom()
    extractor = CustomExtractor()
    manager.authentication = custom
    manager.authorization = custom
    manager.extractor = extractor

    assert manager.authentication is custom
    assert manager.authorization is custom
    assert manager.extractor is extractor


def test_managers_do_not_share_state():
    """Nothing about the manager is global, so one application cannot change another's security."""

    class Custom(Authorization):
        async def authorize(self, request, user):
            return True

    first, second = AuthManager(), AuthManager()
    first.authorization = Custom()

    assert isinstance(second.authorization, NoAuth)


@pytest.mark.parametrize("abstract", [IdTokenExtractor, Authentication, Authorization])
def test_the_contracts_cannot_be_instantiated(abstract: type):
    """They are interfaces. Forgetting the method is an error at construction, not during a request."""
    with pytest.raises(TypeError):
        abstract()


def test_a_misspelled_method_fails_at_construction():
    """A policy whose method name is misspelled must not start.

    The base `authorize` returns `None`, and `None` lets the request through. If a subclass with a typo could
    be built, it would inherit that and allow every request without any error.
    """

    class Misspelled(Authorization):
        async def authorise(self, request, user):
            return False

    with pytest.raises(TypeError):
        Misspelled()
