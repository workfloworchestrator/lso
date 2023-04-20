"""
A module for loading configuration data, including a config schema that
data is validated against. Data is loaded from a file, the location of which
may be specified when using :func:`load_from_file`. Config file location can
also be loaded from environment variable `SETTINGS_FILENAME`, which is default
behaviour in :func:`load`.
"""

import os
import json
import jsonschema

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
    },
    'required': ['collection'],
    'additionalProperties': False
}


def load_from_file(file):
    """
    Loads, validates and returns configuration parameters.

    Input is validated against this jsonschema:

    .. asjson:: resource_management.config.CONFIG_SCHEMA

    :param file: file-like object that produces the config file
    :return: a dict containing the parsed configuration parameters
    """
    config = json.loads(file.read())
    jsonschema.validate(config, CONFIG_SCHEMA)
    return config


def load():
    """
    Loads a config file, located at the path specified in the environment
    variable $SETTINGS_FILENAME. Loading and validating the file is performed
    by :func:`load_from_file`.

    :return: a dict containing the parsed configuration parameters
    """
    assert 'SETTINGS_FILENAME' in os.environ
    with open(os.environ['SETTINGS_FILENAME'], encoding='utf-8') as file:
        return load_from_file(file)
