
import asyncio

from pytest_mock import MockerFixture
from doorbell import DeviceType, Doorbell
from home_assistant import HomeAssistantAPI, sanitize_doorbell_name


def test_sanitize_name():
    # Check that we substitute - and whitespace with _
    sanitized = sanitize_doorbell_name("ds-kd800 3")
    assert "-" not in sanitized
    assert " " not in sanitized
    assert "_" in sanitized


def test_unhandled_event(mocker: MockerFixture):
    registry = mocker.patch('doorbell.Registry')
    doorbell = mocker.patch('doorbell.Doorbell')
    config = mocker.patch('config.AppConfig.HomeAssistant')

    ha = HomeAssistantAPI(config, registry)

    asyncio.run(ha.unhandled_event(doorbell, 0, None, None, None, None)) # type: ignore


def test_friendly_name_multiple_doorbells(mocker: MockerFixture):
    """Test that with multiple doorbells, the sensors gets their correct friendly_name attribute. See issue #18 """
    registry = mocker.patch('doorbell.Registry')
    fake_config = mocker.MagicMock()
    fake_config.name = "A"
    doorbell_a = mocker.Mock(Doorbell, _type=DeviceType.OUTDOOR, _config=fake_config)
    fake_config = mocker.MagicMock()
    fake_config.name = "B"
    doorbell_b = mocker.Mock(Doorbell, _type=DeviceType.OUTDOOR, _config=fake_config)
    registry.values.return_value = [doorbell_a, doorbell_b]

    config = mocker.patch('config.AppConfig.HomeAssistant')
    # Mock call to API
    mocker.patch("home_assistant.requests")

    ha = HomeAssistantAPI(config, registry)

    assert len(ha._sensors) == 2
    assert len(ha._sensors[doorbell_a]) == 6
    assert ha._sensors[doorbell_a]['door']['attributes']["friendly_name"] == 'A door'

