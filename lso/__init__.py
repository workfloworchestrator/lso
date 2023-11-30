"""Automatically invoked app factory."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lso import config, environment
from lso.routes import default, ip_trunk, playbook, router


def create_app() -> FastAPI:
    """Override default settings with those found in the file read from environment variable `SETTINGS_FILENAME`.

    :return: a new flask app instance
    """
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(default.router, prefix="/api")
    app.include_router(playbook.router, prefix="/api/playbook")
    app.include_router(router.router, prefix="/api/router")
    app.include_router(ip_trunk.router, prefix="/api/ip_trunk")

    # test that config params are loaded and available
    config.load()

    environment.setup_logging()

    logging.info("FastAPI app initialized")

    return app
