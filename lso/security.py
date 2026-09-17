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

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.requests import Request

from lso.config import settings


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
