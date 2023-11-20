"""A module for loading configuration data, including a config schema that data is validated against.

Data is loaded from a file, the location of which may be specified when using :func:`load_from_file`.
Config file location can also be loaded from environment variable `SETTINGS_FILENAME`, which is default behaviour in
:func:`load`.
"""

import json
import os
from typing import TextIO

import jsonschema
from pydantic import BaseModel

CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {"ansible_playbooks_root_dir": {"type": "string"}},
    "required": ["ansible_playbooks_root_dir"],
    "additionalProperties": False,
}
DEFAULT_REQUEST_TIMEOUT = 10


class Config(BaseModel):
    """Simple Config class that only contains the path to the used Ansible playbooks."""

    ansible_playbooks_root_dir: str


def load_from_file(file: TextIO) -> Config:
    """Load, validate and return configuration parameters.

    Input is validated against this jsonschema:

    .. asjson:: lso.config.CONFIG_SCHEMA

    :param file: file-like object that produces the config file
    :return: a dict containing the parsed configuration parameters
    """
    config = json.loads(file.read())
    jsonschema.validate(config, CONFIG_SCHEMA)
    return Config(**config)


def load() -> Config:
    """Load a config file, located at the path specified in the environment variable $SETTINGS_FILENAME.

    Loading and validating the file is performed by :func:`load_from_file`.

    :return: a dict containing the parsed configuration parameters
    """
    assert "SETTINGS_FILENAME" in os.environ, "Environment variable SETTINGS_FILENAME not set"
    with open(os.environ["SETTINGS_FILENAME"], encoding="utf-8") as file:
        return load_from_file(file)
