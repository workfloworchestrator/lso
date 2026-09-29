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

"""Default app creation."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lso import environment
from lso.auth import Authentication, AuthManager, Authorization, IdTokenExtractor
from lso.routes.default import router as default_router
from lso.routes.execute import router as executable_router
from lso.routes.files import router as files_router
from lso.routes.playbook import router as playbook_router
from lso.security import authorize, configure_auth

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: "LSO") -> AsyncIterator[None]:
    """Validate the security configuration before the application serves anything."""
    configure_auth(app)
    yield


class LSO(FastAPI):
    """The LSO application.

    A `FastAPI` in every respect, with somewhere to put the authentication and authorization in force. The
    request dependencies in `lso.security` reach it through `request.app`, so each application instance keeps
    its own and nothing is shared globally.
    """

    def __init__(self, **kwargs: Any) -> None:
        """Start out identifying nobody and allowing everything, as an unconfigured LSO does."""
        self.auth_manager = AuthManager()
        super().__init__(lifespan=_lifespan, **kwargs)

    def register_authentication(self, authentication_instance: Authentication) -> None:
        """Use this implementation to identify callers.

        Call it on the application `create_app` returns, before it starts serving:

        ```python
        app = create_app()
        app.register_authentication(MyAuthentication())
        ```

        Args:
            authentication_instance: The `Authentication` to put in force.

        """
        self.auth_manager.authentication = authentication_instance

    def register_authorization(self, authorization_instance: Authorization) -> None:
        """Use this implementation to decide which callers may make which requests.

        The implementation receives the whole request, so a policy can treat `/api/execute/` differently
        from `/api/version`.

        Args:
            authorization_instance: The `Authorization` to put in force.

        """
        self.auth_manager.authorization = authorization_instance

    def register_extractor(self, extractor_instance: IdTokenExtractor) -> None:
        """Use this extractor to find the token in each request.

        The default reads `Authorization: Bearer <token>`. Register another one when callers send the token
        somewhere else, such as an `X-API-Key` header.

        Args:
            extractor_instance: The `IdTokenExtractor` to put in force.

        """
        self.auth_manager.extractor = extractor_instance


def create_app() -> LSO:
    """Initialise the LSO app."""
    app = LSO(docs_url="/api/doc", redoc_url="/api/redoc", openapi_url="/api/openapi.json")

    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
    )

    app.include_router(default_router, prefix="/api", dependencies=[Depends(authorize)])
    app.include_router(playbook_router, prefix="/api/playbook", dependencies=[Depends(authorize)])
    app.include_router(executable_router, prefix="/api/execute", dependencies=[Depends(authorize)])
    app.include_router(files_router, prefix="/api/files", dependencies=[Depends(authorize)])

    environment.setup_logging()

    logger.info("FastAPI app initialised")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("lso.app:app", host="0.0.0.0", port=44444, log_level="debug")
