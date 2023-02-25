from pytest_mock import MockerFixture
from doorbell import DeviceType, Registry
from mqtt import MQTTHandler


def test_init(mocker: MockerFixture):
    registry = Registry()
    # Create a fake doorbell and set the parameters read by the handler
    mocked_doorbell = mocker.patch('doorbell.Doorbell')
    mocked_doorbell._type = DeviceType.OUTDOOR
    mocked_doorbell._config.name = "Test doorbell"
    mocked_doorbell._device_info.serialNumber = lambda: "123"

    registry[0] = mocked_doorbell
    handler = MQTTHandler(registry)
    assert handler is not None
