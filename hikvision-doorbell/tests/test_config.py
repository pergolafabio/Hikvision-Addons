from config import AppConfig
import pytest
from pydantic import ValidationError


def test_AppConfig():
    config = AppConfig()  # type: ignore
    config.load()


def test_load_config_from_json():
    config = AppConfig()  # type: ignore
    config.load("tests/assets/test_config.json")


def test_load_config_missing_token():
    with pytest.raises(ValidationError):
        config = AppConfig()  # type: ignore
        config.load("tests/assets/test_config_wrong.json")


def test_load_config_mqtt():
    config = AppConfig()  # type: ignore
    config.load("tests/assets/test_config_mqtt.json")
