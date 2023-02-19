import json
import os
from pathlib import Path
from typing import Generator
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
class TestDoorbell:

    @pytest.fixture
    def doorbell(self, sdk):
        doorbells_config = json.loads(os.environ.get("DOORBELLS"))  # type: ignore
        config = AppConfig.Doorbell(name="test", ip=doorbells_config[0]['ip'],
                                    username=doorbells_config[0]['username'], password=doorbells_config[0]['password'])
        doorbell = Doorbell(0, config, sdk)
        yield doorbell

        doorbell.logout()

    def test_connect(self, sdk):
        config = AppConfig.Doorbell(name="test", ip="192.168.0.1", username="admin", password="password")
        a = Doorbell(0, config, sdk)
        with pytest.raises(RuntimeError):
            a.authenticate()

    def test_listening(self, doorbell: Doorbell):
        doorbell.authenticate()
        doorbell.setup_alarm()

    def test_reboot(self, doorbell: Doorbell):
        doorbell.authenticate()
        doorbell.reboot_device()
