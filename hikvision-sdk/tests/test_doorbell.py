import os
from pathlib import Path
from doorbell import Doorbell, Config
from sdk.utils import loadSDK, setupSDK, shutdownSDK, SDKConfig, LogLevel
import pytest

@pytest.fixture
def sdk(tmp_path: Path):
    sdk = loadSDK()
    sdk_config: SDKConfig = {
        'log_level': LogLevel.DEBUG,
        'log_dir': str(tmp_path)
    }
    setupSDK(sdk, sdk_config)
    yield sdk

    shutdownSDK(sdk)

config: Config = {
    "ip": os.getenv("IP", ""),
    "username": os.getenv("USERNAME", ""),
    "password": os.getenv("PASSWORD", ""),
}

# Disabled since it requires an Hikvision device
# def test_connect(sdk):
#     a = Doorbell(sdk, config)
#     a.authenticate()
#     a.logout()

# def test_listening(sdk):
#     a = Doorbell(sdk, config)
#     a.authenticate()
#     a.start_listening()
#     a.logout()