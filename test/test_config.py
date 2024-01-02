"""Set of tests that verify correct config is accepted and incorrect config is not."""

import json
import os
import tempfile
from pathlib import Path

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
    with tempfile.NamedTemporaryFile(mode="w") as file:
        Path(file.name).write_text(json.dumps(bad_config))
        with pytest.raises(jsonschema.ValidationError):
            config.load_from_file(Path(file.name))
