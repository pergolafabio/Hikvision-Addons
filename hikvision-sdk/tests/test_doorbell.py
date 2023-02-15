import os
from pathlib import Path
from config import AppConfig
from doorbell import Doorbell
from sdk.utils import loadSDK, setupSDK, shutdownSDK, SDKConfig, SDKLogLevel
import pytest

@pytest.fixture
def sdk(tmp_path: Path):
    sdk = loadSDK()
    sdk_config: SDKConfig = {
        'log_level': SDKLogLevel.DEBUG,
        'log_dir': str(tmp_path)
    }
    setupSDK(sdk, sdk_config)
    yield sdk

    shutdownSDK(sdk)


@pytest.mark.skipif(os.environ.get("CI") is not None, reason="Cannot run inside CI pipeline")
def test_connect(sdk):
    config = AppConfig.Doorbell(name="test", ip="192.168.0.1", username="admin", password="password")
    a = Doorbell(0, config, sdk)
    with pytest.raises(RuntimeError):
        a.authenticate()
        a.logout()


@pytest.mark.skipif(os.environ.get("CI") is not None, reason="Cannot run inside CI pipeline")
def test_listening(sdk):
    config = AppConfig.Doorbell(name="test", ip="192.168.0.1", username="admin", password="password")
    a = Doorbell(0, config, sdk)
    with pytest.raises(RuntimeError):
        a.authenticate()
        a.authenticate()
        a.logout()
