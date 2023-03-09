import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from config import AppConfig
from doorbell import Doorbell
from sdk.utils import loadSDK, setupSDK, shutdownSDK, SDKConfig, SDKLogLevel


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
class TestRealDoorbell:

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

    def test_call_isapi(self, doorbell: Doorbell):
        doorbell.authenticate()
        result = doorbell._call_isapi("GET", "/ISAPI/System/IO/outputs")
        assert len(result) != 0

        root = ET.fromstring(result)

        assert 'IOOutputPortList' in root.tag
    
    def test_get_num_outputs(self, doorbell: Doorbell):
        doorbell.authenticate()
        outputs = doorbell.get_num_outputs()
        print(outputs)
        assert outputs is not None
    
    def test_get_device_info(self, doorbell: Doorbell):
        doorbell.authenticate()
        info = doorbell.get_device_info()
        print(info)
        assert info is not None

    def test_reboot(self, doorbell: Doorbell):
        # This test reboots the doorbell!
        doorbell.authenticate()
        doorbell.reboot_device()


def test_unlock_door(mocker: MockerFixture):
    # Mock SDK and configuration
    sdk = mocker.patch('ctypes.CDLL')
    config = mocker.patch('config.AppConfig.Doorbell')

    doorbell = Doorbell(0, config, sdk)
    # Set user ID to simulate a login
    doorbell.user_id = 0

    doorbell.unlock_door(0)
    sdk.NET_DVR_RemoteControl.assert_called_once()


def test_unlock_door_isapi(mocker: MockerFixture):
    """The SDK fails, fallback to ISAPI"""
    # mock sdk and configuration
    sdk = mocker.patch('ctypes.CDLL')
    # Simulate error in NET_DVR_RemoteControl
    sdk.NET_DVR_RemoteControl.return_value = 0
    config = mocker.patch('config.AppConfig.Doorbell')

    doorbell = Doorbell(0, config, sdk)
    # Set user ID to simulate a login
    doorbell.user_id = 0

    doorbell.unlock_door(0)
    sdk.NET_DVR_RemoteControl.assert_called_once()
    # Check that ISAPI call has been made
    sdk.NET_DVR_STDXMLConfig.assert_called_once()
