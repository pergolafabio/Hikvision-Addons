"""Fixed notice payload and actual discovery callbacks, without hardware/MQTT."""
from ctypes import c_void_p, sizeof, string_at
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from ha_mqtt_discoverable import DeviceInfo
from ha_mqtt_discoverable.sensors import Button
from paho.mqtt.client import Client
from loguru import logger

from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry
from mqtt_input import MQTTInput
from sdk.hcnetsdk import NET_DVR_NOTICE_DATA, NET_DVR_NOTICE_PIC
from sdk.utils import SDKError


def station(name="Indoor", kind=DeviceType.INDOOR, user_id=7):
    sdk = Mock()
    sdk.NET_DVR_RemoteControl.return_value = 1
    door = Doorbell(0, SimpleNamespace(name=name, scenes=False), sdk)
    door._type, door.user_id = kind, user_id
    return door


def message(**changes):
    return SimpleNamespace(**dict({"payload": b"PRESS", "retain": False, "dup": False}, **changes))


def test_native_layout_and_fixed_text_payload():
    assert sizeof(NET_DVR_NOTICE_PIC) == (48 if sizeof(c_void_p) == 8 else 40)
    assert sizeof(NET_DVR_NOTICE_DATA) == (1552 if sizeof(c_void_p) == 8 else 1504)
    assert NET_DVR_NOTICE_DATA.struNoticePic.offset == 1136
    door, captured = station(), []

    def send(user, command, pointer, size):
        assert (user, command, size) == (7, 16008, sizeof(NET_DVR_NOTICE_DATA))
        captured.append(NET_DVR_NOTICE_DATA.from_buffer_copy(string_at(pointer, size)))
        return 1

    door._sdk.NET_DVR_RemoteControl.side_effect = send
    door.send_test_notice()
    value = captured[0]
    assert value.dwSize == sizeof(value) and value.struTime.wYear >= 2026
    assert bytes(value.byNoticeNumber).split(b"\0")[0].startswith(b"ha-test-")
    assert bytes(value.byNoticeNumber)[-1] == 0
    assert bytes(value.byNoticeTheme).split(b"\0")[0] == b"Home Assistant test"
    assert bytes(value.byNoticeDetail).split(b"\0")[0] == b"Test notice from Home Assistant."
    assert (value.byLevel, value.byPicNum) == (4, 0)
    assert not any(bytes(value.struNoticePic)) and not any(value.byRes1) and not any(value.byRes2)
    door._sdk.NET_DVR_RemoteControl.assert_called_once()
    door._sdk.NET_DVR_GetLastError.assert_not_called()


def test_sdk_rejection_preserves_error_code_without_retry():
    door = station()
    door._sdk.NET_DVR_RemoteControl.return_value = 0
    door._sdk.NET_DVR_GetLastError.return_value = 23
    door._sdk.NET_DVR_GetErrorMsg.return_value = b"Not supported"
    with pytest.raises(SDKError) as caught:
        door.send_test_notice()
    assert caught.value.args[1] == 23
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


@pytest.mark.parametrize("kind,user_id", [(DeviceType.OUTDOOR, 7), (DeviceType.INDOOR, -1)])
def test_invalid_target_or_login_does_not_send(kind, user_id):
    door = station(kind=kind, user_id=user_id)
    with pytest.raises(ValueError):
        door.send_test_notice()
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.mark.parametrize("flags", [{"retain": True}, {"dup": True}, {"payload": b"unexpected"}])
def test_replayed_or_invalid_commands_do_not_send(flags):
    door = station()
    MQTTInput.__new__(MQTTInput)._test_notice_callback(None, door, message(**flags))
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_ignored_press_logs_flags_without_message_contents():
    door, logs = station(), []
    sink = logger.add(lambda record: logs.append(str(record)))
    try:
        MQTTInput.__new__(MQTTInput)._test_notice_callback(None, door, message(payload=b"PRIVATE-PAYLOAD-5f1a"))
    finally:
        logger.remove(sink)
    assert any("retain=False, dup=False, press=False" in line for line in logs)
    assert not any("PRIVATE-PAYLOAD-5f1a" in line for line in logs)
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_real_button_discovery_binds_each_indoor_device(mocker):
    doors = [station("Indoor A"), station("Indoor B"), station("Outdoor", DeviceType.OUTDOOR)]
    client, callbacks, buttons = Mock(spec=Client), {}, []
    client.is_connected.return_value = False
    client.message_callback_add.side_effect = lambda topic, callback: callbacks.update({topic: callback})
    mocker.patch("mqtt_input.get_shared_client", return_value=client)
    mocker.patch("mqtt_input.extract_device_info", side_effect=lambda d: DeviceInfo(name=d._config.name, identifiers=d._config.name))
    reconnect = mocker.patch("mqtt_input._register_reconnect_handler")
    for name in ("Text", "Image", "Select", "Sensor"):
        mocker.patch("mqtt_input." + name)

    def button(settings, callback):
        if settings.entity.name != "Test notice":
            return Mock()
        entity = Button(settings, callback)
        buttons.append(entity)
        return entity

    mocker.patch("mqtt_input.Button", side_effect=button)
    MQTTInput(AppConfig.MQTT(host="example.invalid"), Registry(enumerate(doors)))
    assert len(buttons) == 2
    for door in doors:
        door._sdk.NET_DVR_RemoteControl.assert_not_called()
    for index, entity in enumerate(buttons):
        assert entity.generate_config()["entity_category"] == "diagnostic"
        assert entity.generate_config()["payload_press"] == "PRESS"
        assert any(call.args[0] is entity for call in reconnect.call_args_list)
        callbacks[entity._command_topic](client, doors[1 - index], message())
        doors[index]._sdk.NET_DVR_RemoteControl.assert_called_once()
    doors[2]._sdk.NET_DVR_RemoteControl.assert_not_called()
