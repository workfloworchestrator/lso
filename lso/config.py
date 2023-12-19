"""A module for loading configuration data, including a config schema that data is validated against.

Data is loaded from a file, the location of which may be specified when using :func:`load_from_file`.
Config file location can also be loaded from environment variable `SETTINGS_FILENAME`, which is default behaviour in
:func:`load`.
"""

import json
import os
from pathlib import Path

import jsonschema
from pydantic import BaseModel

CONFIG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "ansible_playbooks_root_dir": {"type": "string"},
        "filtered_ansible_keys": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ansible_playbooks_root_dir"],
    "additionalProperties": False,
}
DEFAULT_REQUEST_TIMEOUT = 10


class Config(BaseModel):
    """Simple Config class.

    Contains the root directory at which Ansible playbooks can be found, and a list of keys that should be filtered
    from playbook execution output.
    """

    ansible_playbooks_root_dir: str
    #: .. deprecated:: 0.21
    #:    Not used anymore, does not have to be present in config.
    filtered_ansible_keys: list[str] | None = None


def load_from_file(file: Path) -> Config:
    """Load, validate and return configuration parameters.

    Input is validated against this jsonschema:

    .. asjson:: lso.config.CONFIG_SCHEMA

    :param file: :class:`Path` object that produces the config file.
    :return: a dict containing the parsed configuration parameters.
    """
    config = json.loads(file.read_text())
    jsonschema.validate(config, CONFIG_SCHEMA)
    return Config(**config)


def load() -> Config:
    """Load a config file, located at the path specified in the environment variable $SETTINGS_FILENAME.

    Loading and validating the file is performed by :func:`load_from_file`.

    :return: a dict containing the parsed configuration parameters
    """
    assert "SETTINGS_FILENAME" in os.environ, "Environment variable SETTINGS_FILENAME not set"  # noqa: S101
    return load_from_file(Path(os.environ["SETTINGS_FILENAME"]))
