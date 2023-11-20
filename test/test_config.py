"""Set of tests that verify correct config is accepted and incorrect config is not."""
import io
import json
import os

import jsonschema
import pytest

from lso import config


def test_validate_testenv_config(data_config_filename: str) -> None:
    """Load a configuration from a file.

    :param data_config_filename: Configuration file pytest fixture
    """
    os.environ["SETTINGS_FILENAME"] = data_config_filename
    params = config.load()
    assert params


@pytest.mark.parametrize(
    "bad_config", [{"name": "bad version", "version": 123}, {"name": "missing version"}, {"version": "missing name"}]
)
def test_bad_config(bad_config: dict) -> None:
    with io.StringIO(json.dumps(bad_config)) as file:
        file.seek(0)  # rewind file position to the beginning
        with pytest.raises(jsonschema.ValidationError):
            config.load_from_file(file)
