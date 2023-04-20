"""
automatically invoked app factory
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from lso import environment
from lso import config

from lso.routes import default, device


def create_app():
    """
    overrides default settings with those found
    in the file read from env var SETTINGS_FILENAME

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

    app.include_router(default.router, prefix='/api')
    app.include_router(device.router, prefix='/api/device')

    # test that config params are available and can be loaded
    config.load()

    logging.info('FastAPI app initialized')

    environment.setup_logging()

    return app