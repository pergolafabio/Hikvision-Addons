from ctypes import CDLL
import json
import os
from unittest import mock
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from config import AppConfig
from doorbell import Doorbell
from sdk.utils import SDKError, loadSDK, setupSDK, shutdownSDK, SDKConfig, SDKLogLevel


@pytest.fixture
def mock_doorbell(mocker: MockerFixture) -> Doorbell:
    # mock SDK and configuration
    sdk = mocker.patch('ctypes.CDLL')
    config = mocker.patch('config.AppConfig.Doorbell')
    
    return Doorbell(0, config, sdk)


@pytest.fixture
def doorbell(sdk: CDLL):
    """Connect to a real Doorbell device"""
    doorbells_config = json.loads(os.environ.get("DOORBELLS"))  # type: ignore
    config = AppConfig.Doorbell(name="test", ip=doorbells_config[0]['ip'],
                                username=doorbells_config[0]['username'], password=doorbells_config[0]['password'])
    doorbell = Doorbell(0, config, sdk)
    yield doorbell

    doorbell.logout()


@pytest.mark.skipif(os.environ.get("CI") is not None, reason="Cannot run inside CI pipeline")
class TestRealDoorbell:

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


def test_unlock_door(mock_doorbell: Doorbell):
    # Set user ID to simulate a login
    mock_doorbell.user_id = 0

    mock_doorbell.unlock_door(0)
    mock_doorbell._sdk.NET_DVR_RemoteControl.assert_called_once()  # type: ignore 


def test_unlock_door_isapi(mock_doorbell: Doorbell):
    # Set user ID to simulate a login
    mock_doorbell.user_id = 0

    # Simulate error in NET_DVR_RemoteControl
    mock_doorbell._sdk.NET_DVR_RemoteControl.return_value = 0  # type: ignore 
    
    mock_doorbell.unlock_door(0)

    mock_doorbell._sdk.NET_DVR_RemoteControl.assert_called_once()  # type: ignore 
    # Check that ISAPI call has been made
    mock_doorbell._sdk.NET_DVR_STDXMLConfig.assert_called_once()   # type: ignore 


def test_get_num_outputs_io_outputs(mock_doorbell: Doorbell, mocker: MockerFixture):
    # Set user ID to simulate a login
    mock_doorbell.user_id = 0

    # Read test XML response and set it as return value of `cast` function
    xml_response_bytes = Path("tests/assets/isapi_system_io_outputs.xml").read_text().encode('utf-8')
    mocked_cast = mocker.patch('doorbell.cast')
    mocked_cast.return_value.value = xml_response_bytes

    outputs = mock_doorbell.get_num_outputs()
    assert outputs == 2


def test_get_num_outputs_remote_control(mock_doorbell: Doorbell, mocker: MockerFixture):
    # Define a subclass of SDKError that does nothing, to be raised during the test
    class MockSDKError(SDKError):
        def __init__(self):
            pass

    """Fallback to another ISAPI endpoint"""
    # Set user ID to simulate a login
    mock_doorbell.user_id = 0
    
    # Raise exception when calling endpoint the first time
    mocker.patch('doorbell.call_ISAPI', side_effect=[MockSDKError, mock.DEFAULT])

    # Read test XML response and set it as return value of `cast` function
    xml_response_bytes = Path("tests/assets/isapi_remotecontrol_capabilities.xml").read_text().encode('utf-8')
    mocked_cast = mocker.patch('doorbell.cast')
    mocked_cast.return_value.value = xml_response_bytes

    outputs = mock_doorbell.get_num_outputs()
    assert outputs == 2