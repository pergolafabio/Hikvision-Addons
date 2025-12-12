
import pytest
from pytest_mock import MockerFixture
from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry
from mqtt_input import MQTTInput
from ha_mqtt_discoverable import DeviceInfo


@pytest.fixture
def mock_doorbell(mocker: MockerFixture) -> Doorbell:
    # Create a fake doorbell
    mocked_doorbell = mocker.patch('doorbell.Doorbell')
    mocked_doorbell._type = DeviceType.INDOOR
    mocked_doorbell._config.name = "Test doorbell"
    mocked_doorbell._device_info.serialNumber = lambda: "123"

    return mocked_doorbell


def test_init(mock_doorbell: Doorbell, mocker: MockerFixture):
    registry = Registry()

    registry[0] = mock_doorbell
    
    # Mock call to get DeviceInfo
    extract_device_info = mocker.patch('mqtt_input.extract_device_info', autospec=True)
    dev_info = DeviceInfo(name="test", identifiers="id")
    extract_device_info.return_value = dev_info
    
    # Mock the entities so no MQTT connection is made
    mocker.patch("mqtt_input.Button")
    mocker.patch("mqtt_input.Text")

    # Fake MQTT settings
    mqtt_config = AppConfig.MQTT(host="localhost")

    input = MQTTInput(mqtt_config, registry)
    assert input is not None
