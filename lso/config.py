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

"""A module for loading configuration data, including a configuration schema that data is validated against.

Data is loaded from a file, the location of which may be specified when using :func:`load_from_file`.
Configuration file location can also be loaded from environment variable ``$SETTINGS_FILENAME``, which is default
 behaviour in :func:`load`.
"""

import json
import os
from pathlib import Path

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
    """Simple Configuration class.

    Contains the root directory at which Ansible playbooks are present.
    """

    ansible_playbooks_root_dir: str


def load_from_file(file: Path) -> Config:
    """Load, validate and return configuration parameters.

    Input is validated against this JSON schema:

    .. asjson:: lso.config.CONFIG_SCHEMA

    :param file: :class:`Path` object that produces the configuration file.
    :return: a dict containing the parsed configuration parameters.
    """
    config = json.loads(file.read_text())
    jsonschema.validate(config, CONFIG_SCHEMA)
    return Config(**config)


def load() -> Config:
    """Load a configuration file, located at the path specified in the environment variable ``$SETTINGS_FILENAME``.

    Loading and validating the file is performed by :func:`load_from_file`.

    :return: a dict containing the parsed configuration parameters
    """
    assert "SETTINGS_FILENAME" in os.environ, "Environment variable SETTINGS_FILENAME not set"  # noqa: S101
    return load_from_file(Path(os.environ["SETTINGS_FILENAME"]))
