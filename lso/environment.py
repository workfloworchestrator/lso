"""Environment module for setting up logging."""

import json
import logging.config
import os

LOGGING_DEFAULT_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s - %(name)s " "(%(lineno)d) - %(levelname)s - %(message)s"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {"resource_management": {"level": "DEBUG", "handlers": ["console"], "propagate": False}},
    "root": {"level": "INFO", "handlers": ["console"]},
}


def setup_logging() -> None:
    """Set up logging using the configured filename.

    If LOGGING_CONFIG is defined in the environment, use this for the filename, otherwise use LOGGING_DEFAULT_CONFIG.
    """
    logging_config = LOGGING_DEFAULT_CONFIG
    if "LOGGING_CONFIG" in os.environ:
        filename = os.environ["LOGGING_CONFIG"]
        with open(filename, encoding="utf-8") as file:
            logging_config = json.loads(file.read())

    logging.config.dictConfig(logging_config)
