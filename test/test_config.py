"""Set of tests that verify correct config is accepted and incorrect config is
not.
"""
import io
import json
import os

import pytest

from lso import config


def test_config_with_file(config_file):
    """Load a configuration from a file.

    :param config_file: Configuration file pytest fixture
    """
    os.environ['SETTINGS_FILENAME'] = config_file
    params = config.load()
    assert params


def test_config_correct(good_config_data):
    """Verify that correct configuration is loaded and accepted.

    :param good_config_data: Correct configuration pytest fixture
    """
    with io.StringIO(json.dumps(good_config_data)) as file:
        file.seek(0)  # rewind file position to the beginning
        params = config.load_from_file(file)
        assert params


def test_config_incorrect(bad_config_data):
    """Verify that incorrect configuration raises an exception when trying to
    load.

    :param bad_config_data: Incorrect configuration pytest fixture
    """
    with io.StringIO(json.dumps(bad_config_data)) as file:
        file.seek(0)
        with pytest.raises(Exception,
                           match="'collection-name' is a required property"):
            config.load_from_file(file)
