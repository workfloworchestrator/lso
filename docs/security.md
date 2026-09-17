# Security

LSO runs playbooks and executables on the machine it sits on. Whatever its process can reach, a request can
reach. This page describes what LSO enforces, what it does not, and how to make it enforce more.

## The default: LSO enforces nothing

An LSO that you have not configured for this identifies no caller and allows every request. Access control
is entirely a matter of where you put it: a trusted network, or an authenticating reverse proxy in front.

That is a legitimate way to run LSO and it stays supported. Upgrading does not change it. Everything below
is a capability you switch on, never a new requirement.

!!! warning "Application-level authentication is not a substitute for network placement"

    Even with every request authenticated and authorized, LSO still starts processes on the host. Keep it
    off untrusted networks regardless.

## Network security and application security solve different problems

A reverse proxy can decide whether a caller may reach LSO at all. It is generally poor at deciding *what*
that caller may then do, because it sees a URL and a header, not a request in context.

LSO's own authorization sees the whole request. It can allow `/api/version` while refusing `/api/execute/`,
or allow a caller to list one job's files but not delete another's. Those endpoints do not carry equal risk,
and a policy inside LSO is the only place that distinction can be drawn.

The two combine well. Neither replaces the other.

## Switching it on

Two settings control it, and both are off by default.

| Variable | Meaning |
| --- | --- |
| `LSO_OAUTH2_ACTIVE` | Whether LSO identifies its callers. |
| `LSO_OAUTH2_AUTHORIZATION_ACTIVE` | Whether LSO applies a policy to each request. Requires the above. |
| `LSO_API_KEY` | A shared secret callers present as a bearer token. |

!!! note "Why these names carry an `LSO_` prefix"

    Other applications may read `OAUTH2_ACTIVE` too, and services in one deployment often share a single
    `.env` file. Were LSO to read the unprefixed name, a value set for another application would switch LSO's
    authentication on or off, although nobody changed LSO's configuration.

    The OIDC and OPA connection details are a different matter. Those describe a provider, not LSO's own
    behaviour, so they keep the names `oauth2-lib` gives them: `OIDC_CONF_URL`, `OPA_URL` and the rest.

### The quickest way: a shared secret

Most LSO deployments have one client calling LSO. A full OIDC provider is too much for that. A
shared secret is enough: one long random value that both sides know. Set two variables and write no code:

```sh
LSO_OAUTH2_ACTIVE=true
LSO_API_KEY=a-long-random-value
```

Callers then send the secret as a bearer token:

```sh
curl -H "Authorization: Bearer a-long-random-value" https://lso.example.org/api/version
```

A request with no token, or with the wrong one, gets a `401`. Both answers are the same, so a caller cannot
tell whether a secret is set at all.

This works with the stock container image. At startup, LSO reads `LSO_API_KEY` and sets up the check itself.

!!! note "Rotating the secret"

    `LSO_API_KEY` holds one secret. If you change it, LSO rejects the old one as soon as it restarts. Every
    caller still sending the old one gets a `401` until it is updated too.

    To avoid that gap, accept both secrets while you move the callers across:

    ```python
    from lso.app import create_app
    from lso.auth import SharedSecretAuth

    app = create_app()
    app.register_authentication(SharedSecretAuth(["old-secret", "new-secret"]))
    ```

    When every caller sends the new secret, restart with only the new one.

    An environment variable cannot hold a list, so this needs your own module. See
    [Registering your own implementation](#registering-your-own-implementation).

    If a short break is fine, skip all this: change `LSO_API_KEY` and restart LSO and its callers.

### What happens for each combination

LSO refuses to start rather than boot into a bypass it would not report. A deployment that asked for
authentication and silently got none is worse than one that never asked, because it believes it is
protected.

| `LSO_OAUTH2_ACTIVE` | `LSO_OAUTH2_AUTHORIZATION_ACTIVE` | Registered | Result |
| --- | --- | --- | --- |
| false | false | anything | No checks: every request goes through. The default. |
| true | false | nothing, `LSO_API_KEY` set | Shared secret, registered automatically. |
| true | false | authentication | Callers are identified. No policy. |
| true | true | authentication and authorization | Callers are identified and judged. |
| true | any | nothing, no `LSO_API_KEY` | **Refuses to start.** |
| false | true | anything | **Refuses to start:** a policy has no caller to judge. |
| true | true | authentication only | **Refuses to start:** no policy to apply. |

Each refusal names what to set or call.

Registering an implementation and leaving the switch off is the opposite mistake, and LSO allows everything
in that state: the switch is the authority. It is not treated as an error, because running one image across
environments and switching by variable is a fair way to work, but LSO logs a warning at startup so the
mistake is not silent.

## Authentication and authorization are separate

Three things happen, in order.

1. **Token extraction.** LSO finds the token in the request. By default it reads
   `Authorization: Bearer <token>`. A missing token is not an error at this point.
2. **Authentication.** Your `Authentication` turns the request and that token into a caller.
3. **Authorization.** Your `Authorization` decides whether that caller may make this particular request.

| Stage | Outcome | Result |
| --- | --- | --- |
| Authentication | returns a user | carries on to authorization |
| Authentication | returns `None` | carries on with no caller identified |
| Authentication | raises `HTTPException(401)` | `401`, request stops |
| Authorization | returns `True` | allowed |
| Authorization | returns `False` | `403`, request stops |
| Authorization | returns `None` | allowed: no opinion was expressed |
| Authorization | raises `HTTPException` | that response, so you can set your own `detail` |

!!! warning "`None` is not a denial"

    An authorization returning `None` means it had no opinion, and the request proceeds. Only `False`
    denies.

A denied request is rejected before its body is validated, so a caller who may not use an endpoint does not
learn what that endpoint's body should look like.

## Writing your own implementation

Subclass `Authentication` and `Authorization` from `lso.auth`:

```python
import os

from lso.auth import Authentication, Authorization

EXPECTED_TOKEN = os.environ["MY_CLIENT_TOKEN"]


class HeaderAuthentication(Authentication):
    async def authenticate(self, request, token=None):
        # `token` is what the extractor found. The whole request is available too.
        if token != EXPECTED_TOKEN:
            return None
        return {"groups": ["operators"], "sub": "my-client"}


class ReadOnlyForMostCallers(Authorization):
    async def authorize(self, request, user):
        if request.url.path.startswith(("/api/execute", "/api/playbook")):
            groups = (user or {}).get("groups") or []
            return "operators" in groups
        return True
```

`authorize` receives the whole request, so `request.url.path`, `request.method`, `request.path_params` and
`request.query_params` are all available. Reading the body with `await request.json()` works too, and does
not stop the endpoint parsing it afterwards.

### Rules per playbook or per inventory

These belong in your policy. The body holds `playbook_name`, `inventory` and `extra_vars`, so the policy can
decide on any of them. The OPA adapter sends the body to OPA as `input.arguments.json`.

```python
ALLOWED = {"backup.yaml": {"operators"}}


class PerPlaybook(Authorization):
    async def authorize(self, request, user):
        if request.url.path != "/api/playbook/":
            return True
        body = await request.json()
        groups = set((user or {}).get("groups") or [])
        return bool(groups & ALLOWED.get(body.get("playbook_name"), set()))
```

Two things to watch:

- The policy sees the name as it was sent. Match it exactly: `ok/../danger.yaml` runs `danger.yaml`, so a
  prefix or wildcard match can be fooled.
- `extra_vars` can change which hosts a playbook targets. A rule about hosts must check them too, not only
  `inventory`.

### Taking the token from another header

By default LSO reads the token from `Authorization: Bearer <token>`. If your callers send it somewhere else,
write an extractor:

```python
from lso.auth import IdTokenExtractor


class ApiKeyHeaderExtractor(IdTokenExtractor):
    async def extract(self, request):
        return request.headers.get("X-API-Key")
```

Return `None` when there is no token. Do not reject the request in the extractor: that is the job of your
`Authentication`.

The extractor works with any authentication, including the shared secret. With the extractor above and
`LSO_API_KEY` set, callers send `X-API-Key: <secret>`.

## Registering your own implementation

`lso.app:app`, which the example `Dockerfile` serves, is already built by the time your code could reach it.
To register something, serve your own module instead:

```python title="my_lso.py"
from lso.app import create_app
from my_auth import ApiKeyHeaderExtractor, HeaderAuthentication, ReadOnlyForMostCallers

app = create_app()
app.register_extractor(ApiKeyHeaderExtractor())
app.register_authentication(HeaderAuthentication())
app.register_authorization(ReadOnlyForMostCallers())
```

`register_extractor` is optional. Leave it out to keep the bearer header.

```sh
uvicorn my_lso:app --host 0.0.0.0 --port 8000
```

A shared secret needs none of this. `LSO_API_KEY` works with the stock image.

## OpenID Connect and Open Policy Agent

These come through `oauth2-lib`, as an optional extra:

```sh
pip install 'orchestrator-lso[oidc]'
```

It is not a core dependency. `oauth2-lib` brings `authlib`, `structlog`, `asyncstdlib` and
`strawberry-graphql` with it; LSO has no GraphQL and being small is the point of it, so that is not a price
to put on every deployment. Nothing in LSO imports it unless you do.

```python title="my_lso.py"
from lso.app import create_app
from lso.oidc import oidc_authentication, opa_authorization

app = create_app()
app.register_authentication(oidc_authentication())
app.register_authorization(opa_authorization())
```

Provider settings keep `oauth2-lib`'s own names: `OIDC_CONF_URL`, `OIDC_BASE_URL`,
`OAUTH2_RESOURCE_SERVER_ID`, `OAUTH2_RESOURCE_SERVER_SECRET` and `OPA_URL`.

!!! note "`LSO_OAUTH2_ACTIVE` is still the only switch"

    `oauth2-lib` has switches of its own, `OAUTH2_ACTIVE` and `OAUTH2_AUTHORIZATION_ACTIVE`. When they are
    false, it allows every request. LSO sets them from its own settings when you build these adapters, so you
    never set them yourself and they cannot disagree.

    This matters when LSO shares an `.env` file with another application. An `OAUTH2_ACTIVE=false` left there
    for that application would otherwise switch LSO's OIDC off, and LSO would allow everything while looking
    protected.

!!! note "Which `AsyncClient` to import"

    `OIDCAuth.userinfo` is not implemented for you: subclass `OIDCAuth` and write it for your provider. The
    client it receives comes from `oauth2-lib`, which on 3.x uses `httpx2`, the same client LSO uses. Import
    `AsyncClient`, `BasicAuth`, `Timeout` and `Limits` from `httpx2`, not from the older `httpx`: they are
    unrelated classes that happen to share their names.

## What is not covered

- **The API documentation endpoints.** `/api/doc`, `/api/redoc` and `/api/openapi.json` stay readable
  whatever your policy decides, because FastAPI serves them outside the dependency system. This is accepted
  rather than pending: LSO's API schema is published with the project, so serving it reveals nothing that is
  not already on the project website. Block them at your reverse proxy if your deployment would rather not
  serve them at all.
- **Paths that do not exist.** A request to an unknown URL is answered with a `404` before any policy runs,
  so a caller can discover which endpoints exist.

## Upgrading

Nothing to do. An LSO that sets none of these variables behaves exactly as it did before.
