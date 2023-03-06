
from pytest_mock import MockerFixture
from config import AppConfig
from doorbell import DeviceType, Registry
from mqtt_input import MQTTInput
from ha_mqtt_discoverable import DeviceInfo


def test_init(mocker: MockerFixture):
    registry = Registry()
    # Create a fake doorbell
    mocked_doorbell = mocker.patch('doorbell.Doorbell')
    mocked_doorbell._type = DeviceType.INDOOR
    mocked_doorbell._config.name = "Test doorbell"
    mocked_doorbell._device_info.serialNumber = lambda: "123"

    registry[0] = mocked_doorbell
    # Mock call to get DeviceInfo
    extract_device_info = mocker.patch('mqtt_input.extract_device_info', autospec=True)
    dev_info = DeviceInfo(name="test", identifiers="id")
    extract_device_info.return_value = dev_info
    
    # Mock the button so no MQTT connection is made
    mocker.patch("mqtt_input.Button")

    # Fake MQTT settings
    mqtt_config = AppConfig.MQTT(host="localhost")

    input = MQTTInput(mqtt_config, registry)
    assert input is not None
