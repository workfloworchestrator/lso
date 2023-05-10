"""
A module for loading configuration data, including a config schema that
data is validated against. Data is loaded from a file, the location of which
may be specified when using :func:`load_from_file`. Config file location can
also be loaded from environment variable `SETTINGS_FILENAME`, which is default
behaviour in :func:`load`.
"""

import json
import os

import jsonschema
from pydantic import BaseModel

CONFIG_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-07/schema#',

    'definitions': {
        'galaxy-collection-details': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'version': {'type': 'string'}
            },
            'required': ['name', 'version'],
            'additionalProperties': False
        }
    },

    'type': 'object',
    'properties': {
        'collection': {'$ref': '#/definitions/galaxy-collection-details'},
        'ansible_playbooks_root_dir': 'str'
    },
    'required': ['collection', 'ansible_playbooks_root_dir'],
    'additionalProperties': False
}


class AnsibleCollectionDetails(BaseModel):
    name: str
    version: str


class Config(BaseModel):
    collection: AnsibleCollectionDetails
    ansible_playbooks_root_dir: os.PathLike[str]


def load_from_file(file) -> Config:
    """
    Loads, validates and returns configuration parameters.

    Input is validated against this jsonschema:

    .. asjson:: lso.config.CONFIG_SCHEMA

    :param file: file-like object that produces the config file
    :return: a dict containing the parsed configuration parameters
    """
    config = json.loads(file.read())
    jsonschema.validate(config, CONFIG_SCHEMA)
    return Config(**config)


def load() -> Config:
    """
    Loads a config file, located at the path specified in the environment
    variable $SETTINGS_FILENAME. Loading and validating the file is performed
    by :func:`load_from_file`.

    :return: a dict containing the parsed configuration parameters
    """
    assert 'SETTINGS_FILENAME' in os.environ
    with open(os.environ['SETTINGS_FILENAME'], encoding='utf-8') as file:
        return load_from_file(file)
