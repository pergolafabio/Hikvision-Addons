from config import AppConfig
import pytest
import os
from pydantic import ValidationError
from unittest.mock import patch

# This fixture will run before every test and provide a dummy token
@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "fake_token_for_testing")

def test_AppConfig():
    # FIX: Set the ClassVar on the Class, not the instance
    AppConfig.default_files = [] 
    config = AppConfig()
    # If doorbells is now optional, this will pass
    config.load()

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "fake_test_token")
    # Change the patch to return a mock object that doesn't explode
    with patch("requests.get") as mock_get:
        # Instead of mock_get.side_effect = Exception(...), do this:
        mock_get.return_value.status_code = 404
        yield


def test_load_config_from_json():
    config = AppConfig()  # type: ignore
    config.load("tests/assets/test_config.json")


def test_load_config_missing_token(monkeypatch):
    # Ensure environment is clean
    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)
    monkeypatch.delenv("HOME_ASSISTANT__TOKEN", raising=False)

    # We expect a ValidationError because we provide a HA block but no token
    with pytest.raises(ValidationError):
        # Pass the dictionary directly into the class constructor
        AppConfig(
            doorbells=[],
            home_assistant={"url": "http://localhost:8123"}
        )


def test_load_config_mqtt():
    config = AppConfig()  # type: ignore
    config.load("tests/assets/test_config_mqtt.json")
    assert config.mqtt.host is not None
    assert config.mqtt.port is not None
