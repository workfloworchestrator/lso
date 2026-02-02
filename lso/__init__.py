# Copyright 2023-2025 GÉANT Vereniging.
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

"""LSO, an API for remotely running Ansible playbooks."""

__version__ = "2.4.5"

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lso import environment
from lso.routes.default import router as default_router
from lso.routes.execute import router as executable_router
from lso.routes.playbook import router as playbook_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Initialise the :term:`LSO` app."""
    app = FastAPI(docs_url="/api/doc", redoc_url="/api/redoc", openapi_url="/api/openapi.json")

    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
    )

    app.include_router(default_router, prefix="/api")
    app.include_router(playbook_router, prefix="/api/playbook")
    app.include_router(executable_router, prefix="/api/execute")

    environment.setup_logging()

    logger.info("FastAPI app initialized")

    return app
