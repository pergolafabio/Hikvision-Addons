from config import loadConfig, validateConfig
import pytest

def test_loadConfig():
    config = loadConfig()
    assert config is not None

def test_validateConfig_missing_fields():
    config = loadConfig()
    with pytest.raises(ValueError):
        validateConfig(config)