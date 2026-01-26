from config import AppConfig, LogLevel
from sdk.utils import SDKLogLevel
import pytest
import os
from pydantic import ValidationError
from unittest.mock import patch

def test_AppConfig():
    AppConfig.default_files = []
    config = AppConfig(
        doorbells=[],
        system={"log_level": "WARNING", "sdk_log_level": "NONE"}  # Provide system
    )
    assert config.doorbells == []
    assert config.system.log_level == LogLevel.WARNING
    assert config.system.sdk_log_level == SDKLogLevel.NONE

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "fake_test_token")
    # Change the patch to return a mock object that doesn't explode
    with patch("config.requests.get") as mock_get:
        # Instead of mock_get.side_effect = Exception(...), do this:
        # Create a proper mock that won't trigger exceptions
        mock_response = type('MockResponse', (), {})()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_response.json = lambda: {'data': {}}
        mock_get.return_value = mock_response
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
