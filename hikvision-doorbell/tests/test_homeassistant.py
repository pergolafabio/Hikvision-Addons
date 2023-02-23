
import asyncio

from pytest_mock import MockerFixture
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
