"""Automatically invoked app factory."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lso import config, environment
from lso.routes import default, ip_trunk, router


def create_app() -> FastAPI:
    """Override default settings with those found in the file read from environment variable `SETTINGS_FILENAME`.

    :return: a new flask app instance
    """

    app = FastAPI()
    # app = FastAPI(dependencies=[Depends(get_query_token)])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(default.router, prefix="/api")
    app.include_router(router.router, prefix="/api/router")
    app.include_router(ip_trunk.router, prefix="/api/ip_trunk")

    # test that config params are loaded and available
    config.load()

    logging.info("FastAPI app initialized")

    environment.setup_logging()

    return app
