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

"""Environment module for setting up logging."""

import json
import logging.config
import os
from pathlib import Path

LOGGING_DEFAULT_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s - %(name)s (%(lineno)d) - %(levelname)s - %(message)s"}},
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
        config_file = Path(filename).read_text()
        logging_config = json.loads(config_file)

    logging.config.dictConfig(logging_config)
