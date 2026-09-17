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

"""Pluggable authentication and authorization for LSO.

LSO performs no authentication or authorization by default. A deployment that sits on a trusted network, or
behind an authenticating reverse proxy, keeps working exactly as before without setting anything here.

Three stages run in order:

1. `IdTokenExtractor.extract` finds the token in the request. By default that is the bearer token in the
   `Authorization` header.
2. `Authentication.authenticate` turns the request and token into a user, or rejects it.
3. `Authorization.authorize` decides whether that user may make this particular request.

`authorize` returns `True` to allow, `False` to deny with a 403, and `None` to bypass. `None` is not a
denial: it means no opinion was expressed, and the request proceeds.
"""

import secrets
from abc import ABC, abstractmethod
from collections.abc import Sequence

from fastapi import HTTPException, status
from fastapi.requests import Request
from fastapi.security.http import HTTPBearer
from starlette.requests import HTTPConnection


class Authentication(ABC):
    """Abstract base for authentication mechanisms.

    An implementation turns a request, and the bearer token taken from it, into a user. Returning `None`
    means no user was identified and the request carries on unauthenticated. Rejecting a caller outright is
    done by raising `fastapi.HTTPException` with a 401, which LSO lets through untouched.
    """

    @abstractmethod
    async def authenticate(self, request: Request, token: str | None = None) -> dict | None:
        """Identify the caller behind this request.

        Args:
            request: The incoming request. An implementation may read any part of it.
            token: The token the registered `IdTokenExtractor` found, or `None` if it found none.

        Returns:
            A dictionary describing the caller, or `None` when no user was identified.

        """


class IdTokenExtractor(ABC):
    """Tells LSO where to find the token in a request.

    The default, `HttpBearerExtractor`, reads `Authorization: Bearer <token>`. Register a different one with
    `lso.app.LSO.register_extractor` when callers send the token somewhere else, such as an `X-API-Key`
    header or a cookie.

    An extractor only finds the token. It must not reject a request: when there is no token it returns
    `None`, and the `Authentication` decides what that means.
    """

    @abstractmethod
    async def extract(self, request: Request) -> str | None:
        """Return the token carried by this request, or `None` if there is none."""


class HttpBearerExtractor(HTTPBearer, IdTokenExtractor):
    """The default extractor: the bearer token in the `Authorization` header.

    A missing header, another scheme such as `Basic`, or a malformed value all give `None`.
    """

    def __init__(self) -> None:
        """Never reject a request by itself.

        `auto_error=False` is load-bearing. With `True`, a request with no `Authorization` header would be
        rejected before LSO's own code runs.
        """
        super().__init__(auto_error=False)

    async def extract(self, request: Request) -> str | None:
        """Return the bearer token, or `None` if the request carries none."""
        credentials = await self(request)
        return credentials.credentials if credentials else None


class Authorization(ABC):
    """Defines the authorization logic interface.

    An implementation decides whether an authenticated caller may make this request. It receives the whole
    request, so a policy can treat `/api/execute/` differently from `/api/version`: those endpoints do not
    carry equal risk.

    The return value means:

    * `True`: allowed.
    * `False`: denied. LSO turns this into a 403.
    * `None`: no opinion, the request proceeds. This is a bypass, not a denial.

    Raising `fastapi.HTTPException` directly works too, and is the way to return a custom `detail`.
    """

    @abstractmethod
    async def authorize(self, request: HTTPConnection, user: dict | None) -> bool | None:
        """Decide whether this caller may make this request."""


class NoAuth(Authentication, Authorization):
    """The default: identify nobody, allow everything.

    This is what an unconfigured LSO runs, and why upgrading changes nothing for a deployment that relies on
    network placement for its access control.
    """

    async def authenticate(self, request: Request, token: str | None = None) -> dict | None:  # noqa: ARG002
        """Identify nobody.

        Returns:
            Always `None`.

        """
        return None

    async def authorize(self, request: HTTPConnection, user: dict | None) -> bool | None:  # noqa: ARG002
        """Express no opinion, so the request proceeds.

        Returns:
            Always `None`.

        """
        return None


class SharedSecretAuth(Authentication):
    """Authenticate a caller by a shared secret sent as a bearer token.

    Most LSO deployments have a single client calling LSO, where a full OIDC provider is too much. This
    covers that case with no extra dependency: the caller sends
    `Authorization: Bearer <secret>` and LSO compares it against the secrets it was configured with.

    Set `LSO_API_KEY` and LSO registers this by itself at startup, so the stock container image needs no
    code. Constructing it directly accepts several secrets at once, which is how a secret is rotated without
    downtime: run with the old and the new one, move the callers over, then drop the old one.

    The comparison is constant-time, and a missing token is rejected exactly as a wrong one is, so neither
    the secret nor the fact that one is configured can be read off the responses.

    The secret is whatever token the registered extractor finds, so it can also be sent in another header.
    """

    def __init__(self, secret_values: Sequence[str]) -> None:
        """Configure the secrets a caller may present.

        Args:
            secret_values: The accepted secrets. Empty strings are ignored, because an unset environment
                variable arriving here as `""` must never become a secret that anything matches.

        Raises:
            ValueError: If no usable secret is left, which would otherwise authenticate nobody while
                looking configured.

        """
        usable = [value for value in secret_values if value]
        if not usable:
            msg = "SharedSecretAuth needs at least one non-empty secret."
            raise ValueError(msg)

        self._secrets = [value.encode() for value in usable]

    async def authenticate(self, request: Request, token: str | None = None) -> dict | None:  # noqa: ARG002
        """Accept the caller when the token matches a configured secret.

        Returns:
            A dictionary identifying the caller. It is deliberately non-empty, so an `Authorization`
            implementation can tell a caller authenticated by shared secret from the `None` that means
            authentication is switched off.

        Raises:
            HTTPException: 401 if the token is missing or does not match. Both cases return the same status
                and message, so a caller cannot learn whether a secret is configured.

        """
        if token is None or not self._matches(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        return {"sub": "api-key", "name": "shared-secret"}

    def _matches(self, token: str) -> bool:
        """Report whether the token equals one of the configured secrets.

        Every secret is compared, rather than stopping at the first match, so the time taken does not reveal
        which one matched. `compare_digest` keeps each individual comparison constant-time, so a caller
        cannot recover a secret one character at a time from how long the answer took.

        Returns:
            `True` if the token matches a configured secret.

        """
        candidate = token.encode()
        matched = False
        for secret in self._secrets:
            if secrets.compare_digest(candidate, secret):
                matched = True

        return matched


class AuthManager:
    """Holds the token extractor, authentication and authorization in force for one application.

    Each `lso.app.LSO` instance owns one of these, and the request dependencies read it off `request.app`.
    Nothing here is global: two applications in one process keep their own, which is what stops one test
    leaking a registered implementation into the next.

    The extractor starts as `HttpBearerExtractor`, and the other two slots as `NoAuth`. The `register_*`
    methods on `lso.app.LSO` replace them.
    """

    def __init__(self) -> None:
        """Start out identifying nobody and allowing everything."""
        self._extractor: IdTokenExtractor = HttpBearerExtractor()
        self._authentication: Authentication = NoAuth()
        self._authorization: Authorization = NoAuth()

    @property
    def extractor(self) -> IdTokenExtractor:
        """The token extractor in force."""
        return self._extractor

    @extractor.setter
    def extractor(self, extractor_instance: IdTokenExtractor) -> None:
        self._extractor = extractor_instance

    @property
    def authentication(self) -> Authentication:
        """The authentication in force."""
        return self._authentication

    @authentication.setter
    def authentication(self, auth_instance: Authentication) -> None:
        self._authentication = auth_instance

    @property
    def authorization(self) -> Authorization:
        """The authorization in force."""
        return self._authorization

    @authorization.setter
    def authorization(self, auth_instance: Authorization) -> None:
        self._authorization = auth_instance
