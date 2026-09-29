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

"""Request dependencies that apply the configured authentication and authorization.

`lso.app` attaches `authorize` to every router, so a policy sees every API request without any endpoint
having to know that authorization exists. `authorize` depends on `authenticate`, which depends on the bearer
extractor, so the three stages run in that order and each one receives what the previous produced.

Both dependencies read the active implementations off `request.app`, never off a module-level global. Two
applications in one process therefore keep their own, and a test that registers an implementation cannot
affect another test.
"""

import logging
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, status
from fastapi.requests import Request

from lso.auth import NoAuth, SharedSecretAuth
from lso.config import settings

if TYPE_CHECKING:
    from lso.app import LSO

logger = logging.getLogger(__name__)


def configure_auth(app: "LSO") -> None:
    """Settle which authentication and authorization this application runs with, and refuse a broken one.

    Runs at startup, not in `create_app`, because a deployer registers on the object `create_app` returns.

    Raises:
        RuntimeError: When a security feature is switched on but nothing can enforce it. Booting into a
            silent bypass would leave a deployment that asked for authentication running with none.

    """
    authentication_missing = isinstance(app.auth_manager.authentication, NoAuth)

    # Registered here rather than in `create_app` so an explicitly registered implementation stays in charge.
    if settings.LSO_OAUTH2_ACTIVE and authentication_missing and settings.LSO_API_KEY:
        app.register_authentication(SharedSecretAuth([settings.LSO_API_KEY.get_secret_value()]))
        authentication_missing = False
        logger.info("Registered shared-secret authentication from LSO_API_KEY")

    if settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE and not settings.LSO_OAUTH2_ACTIVE:
        msg = (
            "LSO_OAUTH2_AUTHORIZATION_ACTIVE is true but LSO_OAUTH2_ACTIVE is false. An authorization "
            "policy has no authenticated caller to judge. Set LSO_OAUTH2_ACTIVE=true, or switch "
            "authorization off."
        )
        raise RuntimeError(msg)

    if settings.LSO_OAUTH2_ACTIVE and authentication_missing:
        msg = (
            "LSO_OAUTH2_ACTIVE is true but no authentication is registered. Set LSO_API_KEY to use a shared "
            "secret, or call app.register_authentication(...) on the app returned by create_app(), or set "
            "LSO_OAUTH2_ACTIVE=false."
        )
        raise RuntimeError(msg)

    if settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE and isinstance(app.auth_manager.authorization, NoAuth):
        msg = (
            "LSO_OAUTH2_AUTHORIZATION_ACTIVE is true but no authorization is registered. Call "
            "app.register_authorization(...) on the app returned by create_app(), or set "
            "LSO_OAUTH2_AUTHORIZATION_ACTIVE=false."
        )
        raise RuntimeError(msg)

    # Registering something and leaving the switch off is a plausible mistake, and a quiet one. It is not an
    # error, because running one image across environments and switching by variable is fair, so warn loudly.
    if not settings.LSO_OAUTH2_ACTIVE and not isinstance(app.auth_manager.authentication, NoAuth):
        logger.warning(
            "An authentication implementation is registered but LSO_OAUTH2_ACTIVE is false, so it will not "
            "be used and every request is allowed. Set LSO_OAUTH2_ACTIVE=true to enforce it."
        )

    if not settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE and not isinstance(app.auth_manager.authorization, NoAuth):
        logger.warning(
            "An authorization implementation is registered but LSO_OAUTH2_AUTHORIZATION_ACTIVE is false, so "
            "it will not be used and every request is allowed. Set LSO_OAUTH2_AUTHORIZATION_ACTIVE=true to "
            "enforce it."
        )


async def authenticate(request: Request) -> dict | None:
    """Identify the caller behind this request.

    Returns:
        A dictionary describing the caller, or `None` when authentication is switched off or no user was
        identified.

    """
    if not settings.LSO_OAUTH2_ACTIVE:
        return None

    auth_manager = request.app.auth_manager
    token = await auth_manager.extractor.extract(request)
    return await auth_manager.authentication.authenticate(request, token)


async def authorize(request: Request, user: Annotated[dict | None, Depends(authenticate)]) -> bool | None:
    """Decide whether this caller may make this request, and interrupt it if not.

    An implementation is free to raise `HTTPException` itself, which is how it returns a custom `detail`.
    Anything it raises passes through untouched.

    Returns:
        `True` when the caller is authorized, or `None` when authorization is switched off or the
        implementation expressed no opinion. Both let the request proceed.

    Raises:
        HTTPException: 403 when the implementation returned `False`.

    """
    if not settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE:
        return None

    result = await request.app.auth_manager.authorization.authorize(request, user)
    # `None` is different: it means the implementation had no opinion, so the request is allowed through.
    # Testing truthiness here instead would silently turn every bypass into a denial.
    if result is False:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return result
