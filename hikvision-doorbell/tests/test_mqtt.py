from pytest_mock import MockerFixture
from config import AppConfig
from doorbell import DeviceType, Registry
from mqtt import MQTTHandler
from ha_mqtt_discoverable import DeviceInfo


def test_init(mocker: MockerFixture):
    registry = Registry()
    # Create a fake doorbell and set the parameters read by the handler
    mocked_doorbell = mocker.patch('doorbell.Doorbell')
    mocked_doorbell._type = DeviceType.OUTDOOR
    mocked_doorbell._config.name = "Test doorbell"
    mocked_doorbell._device_info.serialNumber = lambda: "123"

    registry[0] = mocked_doorbell
    
    # Mock call to get DeviceInfo
    extract_device_info = mocker.patch('mqtt.extract_device_info', autospec=True)
    dev_info = DeviceInfo(name="test", identifiers="id")
    extract_device_info.return_value = dev_info

    # Fake MQTT settings
    mqtt_config = AppConfig.MQTT(host="localhost")

    # Mock the sensors so no MQTT connection is made
    mocker.patch("mqtt.BinarySensor")
    mocker.patch("mqtt.Sensor")
    mocker.patch("mqtt.Switch")

    handler = MQTTHandler(mqtt_config, registry)
    assert handler is not None
