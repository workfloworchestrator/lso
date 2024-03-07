# Copyright 2023-2024 GÉANT Vereniging.
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

"""Automatically invoked app factory."""

__version__ = "1.0.0"

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lso import config, environment
from lso.routes.default import router as default_router
from lso.routes.playbook import router as playbook_router


def create_app() -> FastAPI:
    """Override default settings with those found in the file read from environment variable `SETTINGS_FILENAME`.

    :return: a new flask app instance
    """
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
    )

    app.include_router(default_router, prefix="/api")
    app.include_router(playbook_router, prefix="/api/playbook")

    # test that config params are loaded and available
    config.load()

    environment.setup_logging()

    logging.info("FastAPI app initialized")

    return app
