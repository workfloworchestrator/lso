import io
import json
import pytest

from pydantic.error_wrappers import ValidationError

from larp import config


def test_config_with_file(config_file):
    params = config.load()
    assert params


def test_config_correct(good_config_data):
    with io.StringIO(json.dumps(good_config_data)) as f:
        f.seek(0)  # rewind file position to the beginning
        params = config.load_from_file(f)
        assert params


def test_config_incorrect(bad_config_data):
    with io.StringIO(json.dumps(bad_config_data)) as f:
        f.seek(0)
        with pytest.raises(Exception, match="'collection-uri' is a required property"):
            config.load_from_file(f)
