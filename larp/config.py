import json
import jsonschema
import os

CONFIG_SCHEMA = {
    '$schema': 'http://json-schema.org/draft-07/schema#',

    'definitions': {},

    'type': 'object',
    'properties': {
        'collection-name': {'type': 'string'},
    },
    'required': ['collection-name'],
    'additionalProperties': False
}


def load_from_file(f):
    """
    Loads, validates and returns configuration parameters.

    Input is validated against this jsonschema:

    .. asjson:: resource_management.config.CONFIG_SCHEMA

    :param f: file-like object that produces the config file
    :return: a dict containing the parsed configuration parameters
    """
    config = json.loads(f.read())
    jsonschema.validate(config, CONFIG_SCHEMA)
    return config


def load():
    assert 'SETTINGS_FILENAME' in os.environ
    with open(os.environ['SETTINGS_FILENAME']) as f:
        return load_from_file(f)
