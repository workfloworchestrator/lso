"""
automatically invoked app factory
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ansible_api import environment
from ansible_api import config

from ansible_api.routes import default


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

    app.include_router(
        default.router,
        prefix='/api',
        # tags="default"],
        # dependencies=[Depends(get_token_header)],
        # responses={418: {"description": "I'm a teapot"}},
    )

    # app.include_router(
    #     interfaces.router,
    #     prefix='/api/interfaces',
    #     # tags=["trunk"],
    #     # dependencies=[Depends(get_token_header)],
    #     # responses={418: {"description": "I'm a teapot"}},
    # )

    # test that config params are available and can be loaded
    config.load()

    logging.info('FastAPI app initialized')

    environment.setup_logging()

    return app
