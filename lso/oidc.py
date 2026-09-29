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

"""OpenID Connect and Open Policy Agent, through `oauth2-lib`.

Needs an extra that plain LSO does not install: `pip install 'orchestrator-lso[oidc]'`. Nothing else in
`lso` imports this module.

Register the adapters on the application, then serve your own module. Connection settings are
`oauth2-lib`'s own, unprefixed. See `docs/security.md`.
"""

import logging

from oauth2_lib.fastapi import OIDCAuth, OIDCUserModel, OPAAuthorization
from oauth2_lib.settings import oauth2lib_settings
from starlette.requests import HTTPConnection, Request

from lso.auth import Authentication, Authorization
from lso.config import settings

logger = logging.getLogger(__name__)


def _adopt_lso_switches() -> None:
    """Make oauth2-lib follow LSO's switches rather than its own.

    `OIDCAuth.authenticate` returns `None` when oauth2-lib's `OAUTH2_ACTIVE` is false, and LSO reads that as
    "no opinion" and allows the request. Left alone, a deployment whose `.env` is shared with another
    application that sets `OAUTH2_ACTIVE=false` would therefore run wide open while believing it was
    protected, and a deployer would have to keep two settings in step to avoid it.

    So `LSO_OAUTH2_ACTIVE` decides, and these follow. Nothing else in an LSO process uses oauth2-lib, so
    there is nothing else for this to affect.
    """
    oauth2lib_settings.OAUTH2_ACTIVE = settings.LSO_OAUTH2_ACTIVE
    oauth2lib_settings.OAUTH2_AUTHORIZATION_ACTIVE = settings.LSO_OAUTH2_AUTHORIZATION_ACTIVE

    logger.info(
        "Applied LSO's security switches to oauth2-lib: OAUTH2_ACTIVE=%s, OAUTH2_AUTHORIZATION_ACTIVE=%s",
        oauth2lib_settings.OAUTH2_ACTIVE,
        oauth2lib_settings.OAUTH2_AUTHORIZATION_ACTIVE,
    )


class OIDCAuthentication(Authentication):
    """Adapts an `oauth2-lib` `OIDCAuth` to LSO's authentication contract."""

    def __init__(self, oidc_auth: OIDCAuth) -> None:
        """Wrap an already-configured `OIDCAuth`."""
        self.oidc_auth = oidc_auth

    async def authenticate(self, request: Request, token: str | None = None) -> dict | None:
        """Identify the caller through the OIDC provider.

        Returns:
            The OIDC user, or `None` when oauth2-lib bypassed the request.

        """
        return await self.oidc_auth.authenticate(request, token)


class OPAAuthorizationAdapter(Authorization):
    """Adapts an `oauth2-lib` `OPAAuthorization` to LSO's authorization contract."""

    def __init__(self, opa_authorization: OPAAuthorization) -> None:
        """Wrap an already-configured `OPAAuthorization`."""
        self.opa_authorization = opa_authorization

    async def authorize(self, request: HTTPConnection, user: dict | None) -> bool | None:
        """Ask Open Policy Agent whether this caller may make this request.

        Returns:
            `True` when the policy allows, `False` when it denies, `None` when it was bypassed.

        """
        # oauth2-lib declares this argument as an `OIDCUserModel`, though its own implementation copes with
        # `None` by way of `user_info or {}`. An unauthenticated caller becomes an empty model rather than
        # `None`, which spreads into the OPA input identically while keeping to the declared contract. A
        # user that already is an `OIDCUserModel`, which is what OIDC authentication returns, passes
        # straight through.
        user_info = user if isinstance(user, OIDCUserModel) else OIDCUserModel(user or {})

        return await self.opa_authorization.authorize(request, user_info)


def oidc_authentication(oidc_auth: OIDCAuth | None = None) -> OIDCAuthentication:
    """Build OIDC authentication from oauth2-lib's settings.

    Note that `OIDCAuth.userinfo` raises `NotImplementedError`, so a real deployment subclasses `OIDCAuth`,
    implements `userinfo` for its provider, and passes the instance in here. The `AsyncClient` handed to
    `userinfo` comes from oauth2-lib, so import it from `httpx2`, which is what oauth2-lib 3.x and LSO both
    use. Mixing it with the older `httpx` gives two unrelated classes of the same name.

    Args:
        oidc_auth: A configured `OIDCAuth`. Built from the environment when left out.

    Returns:
        Something `lso.app.LSO.register_authentication` accepts.

    """
    _adopt_lso_switches()

    return OIDCAuthentication(
        oidc_auth
        or OIDCAuth(
            openid_url=oauth2lib_settings.OIDC_BASE_URL,
            openid_config_url=oauth2lib_settings.OIDC_CONF_URL,
            resource_server_id=oauth2lib_settings.OAUTH2_RESOURCE_SERVER_ID,
            resource_server_secret=oauth2lib_settings.OAUTH2_RESOURCE_SERVER_SECRET,
            oidc_user_model_cls=OIDCUserModel,
        )
    )


def opa_authorization(opa: OPAAuthorization | None = None) -> OPAAuthorizationAdapter:
    """Build Open Policy Agent authorization from oauth2-lib's settings.

    Args:
        opa: A configured `OPAAuthorization`. Built from `OPA_URL` when left out.

    Returns:
        Something `lso.app.LSO.register_authorization` accepts.

    """
    _adopt_lso_switches()

    return OPAAuthorizationAdapter(opa or OPAAuthorization(opa_url=oauth2lib_settings.OPA_URL))
