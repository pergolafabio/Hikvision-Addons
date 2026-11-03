"""Native notice buffers and real discovery callbacks, without hardware/MQTT."""
from ctypes import c_void_p, sizeof, string_at
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from ha_mqtt_discoverable import DeviceInfo
from ha_mqtt_discoverable.sensors import Button, Text
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


def test_native_layout_utf8_body_and_zero_picture_fields():
    assert sizeof(NET_DVR_NOTICE_PIC) == (48 if sizeof(c_void_p) == 8 else 40)
    assert sizeof(NET_DVR_NOTICE_DATA) == (1552 if sizeof(c_void_p) == 8 else 1504)
    assert NET_DVR_NOTICE_DATA.struNoticePic.offset == 1136
    door, captured = station(), []

    def send(user, command, pointer, size):
        assert (user, command, size) == (7, 16008, sizeof(NET_DVR_NOTICE_DATA))
        captured.append(NET_DVR_NOTICE_DATA.from_buffer_copy(string_at(pointer, size)))
        return 1

    door._sdk.NET_DVR_RemoteControl.side_effect = send
    body = "Я" * 511 + "!"  # Exactly 1023 UTF-8 bytes, followed by a NUL.
    door.send_notice(body)
    value = captured[0]
    assert value.dwSize == sizeof(value) and value.struTime.wYear >= 2026
    assert bytes(value.byNoticeNumber).split(b"\0")[0].startswith(b"ha-")
    assert bytes(value.byNoticeNumber)[-1] == 0
    assert bytes(value.byNoticeTheme).split(b"\0")[0] == b"Home Assistant"
    assert bytes(value.byNoticeDetail).split(b"\0")[0] == body.encode("utf-8")
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
        door.send_notice("Hello")
    assert caught.value.args[1] == 23
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


@pytest.mark.parametrize("kind,user_id", [(DeviceType.OUTDOOR, 7), (DeviceType.INDOOR, -1)])
def test_invalid_target_or_login_does_not_send(kind, user_id):
    door = station(kind=kind, user_id=user_id)
    with pytest.raises(ValueError):
        door.send_notice("Hello")
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.mark.parametrize("text", ["", " \n", "x" * 1024, "😀" * 256, "a\0b", "a\x7fb", None])
def test_invalid_text_does_not_send(text):
    door = station()
    with pytest.raises(ValueError):
        door.send_notice(text)
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_image_pointer_stays_valid_during_native_call(tmp_path, mocker):
    mocker.patch("doorbell.NOTICE_IMAGE_DIR", tmp_path)
    jpeg = b"\xff\xd8" + b"sample-data" + b"\xff\xd9"
    (tmp_path / "gate.jpg").write_bytes(jpeg)
    door = station()

    def send(user, command, pointer, size):
        value = NET_DVR_NOTICE_DATA.from_buffer_copy(string_at(pointer, size))
        assert (value.byLevel, value.byPicNum) == (4, 1)
        pic = value.struNoticePic[0]
        assert pic.dwPicDataLen == len(jpeg)
        assert string_at(pic.pPicData, pic.dwPicDataLen) == jpeg
        assert all(not p.pPicData and not p.dwPicDataLen and not any(p.byRes) for p in value.struNoticePic[1:])
        return 1

    door._sdk.NET_DVR_RemoteControl.side_effect = send
    door.send_notice("Hello", "gate.jpg")
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


@pytest.mark.parametrize("filename", ["../gate.jpg", "/media/gate.jpg", "https://example.invalid/a.jpg", "a\\b.jpg", "a.png", None])
def test_invalid_filename_is_rejected_before_open(filename, mocker):
    opened, door = mocker.patch("doorbell.os.open"), station()
    with pytest.raises(ValueError):
        door.send_notice("Hello", filename)
    opened.assert_not_called()
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.mark.parametrize("data", [b"not JPEG", b"\xff\xd8unfinished", b"\xff\xd8" + b"x" * 24576 + b"\xff\xd9"])
def test_invalid_or_oversized_image_does_not_send(data, tmp_path, mocker):
    mocker.patch("doorbell.NOTICE_IMAGE_DIR", tmp_path)
    (tmp_path / "gate.jpg").write_bytes(data)
    door = station()
    with pytest.raises(ValueError):
        door.send_notice("Hello", "gate.jpg")
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_missing_symlink_and_nonregular_image_do_not_send(tmp_path, mocker):
    import os
    mocker.patch("doorbell.NOTICE_IMAGE_DIR", tmp_path)
    door = station()
    with pytest.raises(FileNotFoundError):
        door.send_notice("Hello", "missing.jpg")
    (tmp_path / "link.jpg").symlink_to(tmp_path / "missing.jpg")
    with pytest.raises(ValueError):
        door.send_notice("Hello", "link.jpg")
    os.mkfifo(tmp_path / "pipe.jpg")
    with pytest.raises(ValueError):
        door.send_notice("Hello", "pipe.jpg")
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.fixture
def controls(mocker, tmp_path):
    mocker.patch("doorbell.NOTICE_IMAGE_DIR", tmp_path)
    doors = [station("Indoor A"), station("Indoor B"), station("Outdoor", DeviceType.OUTDOOR)]
    client, callbacks, buttons, inputs, wire = Mock(spec=Client), {}, {}, {}, {}
    client.is_connected.return_value = False
    client.message_callback_add.side_effect = lambda topic, callback: callbacks.update({topic: callback})
    mocker.patch("mqtt_input.get_shared_client", return_value=client)
    mocker.patch("mqtt_input.extract_device_info", side_effect=lambda d: DeviceInfo(name=d._config.name, identifiers=d._config.name))
    reconnect = mocker.patch("mqtt_input._register_reconnect_handler")
    for name in ("Image", "Select", "Sensor"):
        mocker.patch("mqtt_input." + name)

    def button(settings, callback):
        if settings.entity.name != "Send notice":
            return Mock()
        entity = Button(settings, callback)
        buttons[next(d for d in doors if d._config.name == settings.entity.device.name)] = entity
        return entity

    def text(settings, callback):
        if settings.entity.name not in ("Notice text", "Notice JPEG"):
            return Mock()
        entity = Text(settings, callback)
        field = "text" if settings.entity.name == "Notice text" else "image"
        inputs[next(d for d in doors if d._config.name == settings.entity.device.name), field] = entity
        return entity

    mocker.patch("mqtt_input.Button", side_effect=button)
    mocker.patch("mqtt_input.Text", side_effect=text)
    instance = MQTTInput(AppConfig.MQTT(host="example.invalid"), Registry(enumerate(doors)))

    def capture(door, pointer, size):
        wire[door] = NET_DVR_NOTICE_DATA.from_buffer_copy(string_at(pointer, size))
        return 1

    for door in doors:
        door._sdk.NET_DVR_RemoteControl.side_effect = lambda user, cmd, ptr, size, target=door: capture(target, ptr, size)

    def edit(door, field, value, **flags):
        callbacks[inputs[door, field]._command_topic](client, doors[-1], message(payload=value.encode() if isinstance(value, str) else value, **flags))

    def press(door, **flags):
        callbacks[buttons[door]._command_topic](client, doors[-1], message(**flags))

    return SimpleNamespace(doors=doors, client=client, instance=instance, buttons=buttons, inputs=inputs,
                           reconnect=reconnect, edit=edit, press=press, wire=wire, image_dir=tmp_path)


def test_real_discovery_edits_do_not_send_and_press_binds_exact_device(controls):
    c = controls
    assert len(c.inputs) == 4 and len(c.buttons) == 2
    for door in c.doors[:2]:
        entity = c.buttons[door]
        assert entity.generate_config()["payload_press"] == "PRESS"
        assert any(call.args[0] is entity for call in c.reconnect.call_args_list)
        for field in ("text", "image"):
            assert c.inputs[door, field].generate_config()["retain"] is False
        c.edit(door, "text", door._config.name)
    for door in c.doors:
        door._sdk.NET_DVR_RemoteControl.assert_not_called()
    for door in c.doors[:2]:
        c.press(door)
        door._sdk.NET_DVR_RemoteControl.assert_called_once()
        assert bytes(c.wire[door].byNoticeDetail).split(b"\0")[0] == door._config.name.encode()
    c.doors[-1]._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.mark.parametrize("flags", [{"retain": True}, {"dup": True}, {"payload": b"unexpected"}])
def test_replayed_or_invalid_commands_do_not_send(controls, flags):
    c, door = controls, controls.doors[0]
    c.edit(door, "text", "Hello")
    c.press(door, **flags)
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.mark.parametrize("flags", [{"retain": True}, {"dup": True}])
def test_replayed_edits_do_not_change_draft(controls, flags):
    c, door = controls, controls.doors[0]
    c.edit(door, "text", "Hello")
    c.edit(door, "text", "Stale", **flags)
    assert c.instance._notice_drafts[door]["text"] == "Hello"


@pytest.mark.parametrize("field,payload", [("text", b"\xff"), ("text", "x" * 256), ("image", b"\0")])
def test_bad_edit_blocks_old_draft_until_explicit_correction(controls, field, payload):
    c, door = controls, controls.doors[0]
    c.edit(door, "text", "Hello")
    c.edit(door, field, payload)
    c.press(door)
    door._sdk.NET_DVR_RemoteControl.assert_not_called()
    c.edit(door, field, "Corrected" if field == "text" else "")
    c.press(door)
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


def test_empty_text_and_missing_image_block_send_until_cleared(controls):
    c, door = controls, controls.doors[0]
    c.press(door)
    c.edit(door, "text", "Hello")
    c.edit(door, "image", "missing.jpg")
    c.press(door)
    door._sdk.NET_DVR_RemoteControl.assert_not_called()
    c.edit(door, "image", "")
    c.press(door)
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


def test_discovery_flow_accepts_utf8_and_optional_image(controls):
    c, door = controls, controls.doors[0]
    jpeg = b"\xff\xd8sample-data\xff\xd9"
    (c.image_dir / "gate.jpg").write_bytes(jpeg)
    c.edit(door, "text", "😀" * 255)
    c.edit(door, "image", "gate.jpg")
    c.press(door)
    assert bytes(c.wire[door].byNoticeDetail).split(b"\0")[0] == ("😀" * 255).encode()
    assert c.wire[door].byPicNum == 1
    assert c.wire[door].struNoticePic[0].dwPicDataLen == len(jpeg)
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


def test_ignored_press_logs_flags_without_message_contents(controls):
    c, logs = controls, []
    sink = logger.add(lambda record: logs.append(str(record)))
    try:
        c.press(c.doors[0], payload=b"PRIVATE-PAYLOAD-5f1a")
    finally:
        logger.remove(sink)
    assert any("retain=False, dup=False, press=False" in line for line in logs)
    assert not any("PRIVATE-PAYLOAD-5f1a" in line for line in logs)
    c.doors[0]._sdk.NET_DVR_RemoteControl.assert_not_called()
