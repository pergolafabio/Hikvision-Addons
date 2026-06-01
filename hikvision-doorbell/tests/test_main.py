"""Tests for the SDK-driven connectivity callback in main.py."""
import sys
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from doorbell import Registry  # noqa: E402
from main import make_exception_callback  # noqa: E402
from sdk.hcnetsdk import (  # noqa: E402
    ALARM_RECONNECTSUCCESS,
    EXCEPTION_ALARM,
    EXCEPTION_ALARMRECONNECT,
    EXCEPTION_EXCHANGE,
    EXCEPTION_PREVIEW,
    EXCEPTION_RECONNECT,
    PREVIEW_RECONNECTSUCCESS,
)


def _make_doorbell(mocker: MockerFixture, doorbell_id: int, user_id: int):
    d = mocker.MagicMock()
    d._id = doorbell_id
    d.user_id = user_id
    return d


class TestExceptionCallback:

    def test_alarm_reconnect_marks_offline(self, mocker: MockerFixture):
        registry = Registry()
        registry[0] = _make_doorbell(mocker, doorbell_id=0, user_id=42)
        handler = mocker.MagicMock()

        cb = make_exception_callback(registry, handler)
        cb(EXCEPTION_ALARMRECONNECT, 42, 0, None)

        handler.set_doorbell_offline.assert_called_once_with(0)
        handler.set_doorbell_online.assert_not_called()

    def test_reconnect_success_marks_online(self, mocker: MockerFixture):
        registry = Registry()
        registry[0] = _make_doorbell(mocker, doorbell_id=0, user_id=42)
        handler = mocker.MagicMock()

        cb = make_exception_callback(registry, handler)
        cb(ALARM_RECONNECTSUCCESS, 42, 0, None)

        handler.set_doorbell_online.assert_called_once_with(0)
        handler.set_doorbell_offline.assert_not_called()

    @pytest.mark.parametrize("ok_type", [PREVIEW_RECONNECTSUCCESS, ALARM_RECONNECTSUCCESS])
    def test_all_reconnect_codes_mark_online(self, mocker: MockerFixture, ok_type):
        registry = Registry()
        registry[0] = _make_doorbell(mocker, doorbell_id=0, user_id=42)
        handler = mocker.MagicMock()

        cb = make_exception_callback(registry, handler)
        cb(ok_type, 42, 0, None)

        handler.set_doorbell_online.assert_called_once_with(0)

    @pytest.mark.parametrize("exc_type", [
        EXCEPTION_EXCHANGE, EXCEPTION_ALARM, EXCEPTION_PREVIEW,
        EXCEPTION_RECONNECT, EXCEPTION_ALARMRECONNECT,
    ])
    def test_all_disconnect_exceptions_mark_offline(self, mocker: MockerFixture, exc_type):
        registry = Registry()
        registry[0] = _make_doorbell(mocker, doorbell_id=0, user_id=42)
        handler = mocker.MagicMock()

        cb = make_exception_callback(registry, handler)
        cb(exc_type, 42, 0, None)

        handler.set_doorbell_offline.assert_called_once_with(0)

    def test_unknown_user_id_does_nothing(self, mocker: MockerFixture):
        registry = Registry()
        registry[0] = _make_doorbell(mocker, doorbell_id=0, user_id=42)
        handler = mocker.MagicMock()

        cb = make_exception_callback(registry, handler)
        cb(EXCEPTION_ALARMRECONNECT, 999, 0, None)

        handler.set_doorbell_offline.assert_not_called()
        handler.set_doorbell_online.assert_not_called()

    def test_no_mqtt_handler_does_not_crash(self, mocker: MockerFixture):
        registry = Registry()
        registry[0] = _make_doorbell(mocker, doorbell_id=0, user_id=42)

        cb = make_exception_callback(registry, None)
        cb(EXCEPTION_ALARMRECONNECT, 42, 0, None)
        cb(ALARM_RECONNECTSUCCESS, 42, 0, None)

    def test_unknown_exception_type_no_state_change(self, mocker: MockerFixture):
        registry = Registry()
        registry[0] = _make_doorbell(mocker, doorbell_id=0, user_id=42)
        handler = mocker.MagicMock()

        cb = make_exception_callback(registry, handler)
        cb(0xDEAD, 42, 0, None)

        handler.set_doorbell_offline.assert_not_called()
        handler.set_doorbell_online.assert_not_called()

    def test_maps_correct_doorbell_among_many(self, mocker: MockerFixture):
        registry = Registry()
        registry[0] = _make_doorbell(mocker, doorbell_id=0, user_id=10)
        registry[1] = _make_doorbell(mocker, doorbell_id=1, user_id=20)
        registry[2] = _make_doorbell(mocker, doorbell_id=2, user_id=30)
        handler = mocker.MagicMock()

        cb = make_exception_callback(registry, handler)
        cb(EXCEPTION_ALARMRECONNECT, 20, 0, None)

        handler.set_doorbell_offline.assert_called_once_with(1)
