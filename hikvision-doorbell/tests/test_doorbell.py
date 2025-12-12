from ctypes import CDLL
import json
import os
import time
from unittest import mock
import xml.etree.ElementTree as ET
from pathlib import Path
from loguru import logger

import pytest
from pytest_mock import MockerFixture
from config import AppConfig
from doorbell import Doorbell
from sdk.utils import SDKError, loadSDK, setupSDK, shutdownSDK, SDKConfig, SDKLogLevel


@pytest.fixture
def mock_doorbell(mocker: MockerFixture) -> Doorbell:
    # mock SDK
    sdk = mocker.patch('ctypes.CDLL')
    config = AppConfig.Doorbell(name="test", ip="localhost", username="admin", password="password")

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

    def test_get_call_status(self, doorbell: Doorbell):
        doorbell.authenticate()
        pytest.skip("This API is still experimental")
        logger.info("Getting the call status")
        status = doorbell.get_call_status()
        logger.info("Call status {}", status)

    def test_reboot(self, doorbell: Doorbell):
        '''This test reboots the doorbell!'''
        doorbell.authenticate()
        pytest.skip("This will reboot the doorbell!")

        doorbell.reboot_device()


class TestGetNumOutputs:
    # Define a subclass of SDKError that does nothing, to be raised during the test
    class MockSDKError(SDKError):
        def __init__(self):
            pass

    def test_user_config(self, mock_doorbell: Doorbell, mocker: MockerFixture):
        '''If the user manually specifies the number of outputs, use it'''
        # Set user ID to simulate a login
        mock_doorbell.user_id = 0
        mock_doorbell._config.output_relays = 1

        outputs = mock_doorbell.get_num_outputs()
        assert outputs == 1

    def test_sdk_device_ability(self, mock_doorbell: Doorbell, mocker: MockerFixture):
        def mock_get_device_ability(user, *args, **kwargs):
            output_buffer_array = args[3]
            output_buffer_array.value = Path("tests/assets/sdk_get_device_ability_ip_view.xml").read_text().encode('utf-8')
            # call succeeded
            return True
 
        # Set user ID to simulate a login
        mock_doorbell.user_id = 0
        mock_doorbell._sdk.NET_DVR_GetDeviceAbility.side_effect = mock_get_device_ability  # type: ignore
   
        assert mock_doorbell.get_num_outputs() == 2

    def test_isapi_io_outputs(self, mock_doorbell: Doorbell, mocker: MockerFixture):
        # Set user ID to simulate a login
        mock_doorbell.user_id = 0

        # Raise exception with previous method
        mock_doorbell._sdk.NET_DVR_GetDeviceAbility.side_effect = RuntimeError  # type: ignore

        # Read test XML response and set it as return value of `cast` function
        xml_response_bytes = Path("tests/assets/isapi_system_io_outputs.xml").read_text().encode('utf-8')
        mocked_cast = mocker.patch('doorbell.cast')
        mocked_cast.return_value.value = xml_response_bytes

        outputs = mock_doorbell.get_num_outputs()
        assert outputs == 2
  
    def test_isapi_remote_control(self, mock_doorbell: Doorbell, mocker: MockerFixture):
        """Fallback to another ISAPI endpoint"""

        # Set user ID to simulate a login
        mock_doorbell.user_id = 0
        
        # Raise exception with previous method
        mock_doorbell._sdk.NET_DVR_GetDeviceAbility.side_effect = RuntimeError  # type: ignore

        # Raise exception when calling ISAPI helper function the first time
        mocker.patch('doorbell.call_ISAPI', side_effect=[self.MockSDKError, mock.DEFAULT])

        # Read test XML response and set it as return value of `cast` function
        xml_response_bytes = Path("tests/assets/isapi_remotecontrol_capabilities.xml").read_text().encode('utf-8')
        mocked_cast = mocker.patch('doorbell.cast')
        mocked_cast.return_value.value = xml_response_bytes

        outputs = mock_doorbell.get_num_outputs()
        assert outputs == 2

"""
    def test_no_methods_available(self, mock_doorbell: Doorbell, mocker: MockerFixture):
        '''Raise exception if no more methods are available'''
        # Set user ID to simulate a login
        mock_doorbell.user_id = 0
        
        # Raise exception with SDK method
        mock_doorbell._sdk.NET_DVR_GetDeviceAbility.side_effect = RuntimeError  # type: ignore

        # Raise exception when calling ISAPI helper function
        mocker.patch('doorbell.call_ISAPI', side_effect=self.MockSDKError)
        with pytest.raises(RuntimeError):
            mock_doorbell.get_num_outputs()

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
"""