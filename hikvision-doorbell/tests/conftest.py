'''Define useful pytest fixtures shared across all the test code'''
from ctypes import CDLL
from pathlib import Path
import pytest
import json
import os
from config import AppConfig
from doorbell import Doorbell

from sdk.utils import SDKConfig, SDKLogLevel, loadSDK, setupSDK, shutdownSDK


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


@pytest.fixture
def doorbell(sdk: CDLL):
    """Connect to a real Doorbell device"""
    doorbells_config = json.loads(os.environ.get("DOORBELLS"))  # type: ignore
    config = AppConfig.Doorbell(name="test", ip=doorbells_config[0]['ip'],
                                username=doorbells_config[0]['username'], password=doorbells_config[0]['password'])
    doorbell = Doorbell(0, config, sdk)
    yield doorbell

    doorbell.logout()