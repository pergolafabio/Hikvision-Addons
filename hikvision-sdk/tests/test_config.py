from config import loadConfig
import pytest


def test_loadConfig():
    with pytest.raises(ValueError):
        config = loadConfig()


def test_loadConfig_from_file():
    config = loadConfig("tests/assets/test_config.json")
    assert config.ip is not None
    assert config.system.log_level is not None


def test_validateConfig_missing_fields():
    with pytest.raises(ValueError):
        config = loadConfig()
        config.validate()
