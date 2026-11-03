"""Native notice buffers and real discovery callbacks, without hardware/MQTT."""
from ctypes import c_void_p, sizeof, string_at
from types import SimpleNamespace
from unittest.mock import Mock, MagicMock

import pytest
import requests
from ha_mqtt_discoverable import DeviceInfo
from ha_mqtt_discoverable.sensors import Button, Text
from paho.mqtt.client import Client
from loguru import logger

from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry, MAX_NOTICE_IMAGE_BYTES
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
    jpeg = b"\xff\xd8" + b"sample-data" + b"\xff\xd9"
    image = tmp_path / "Картинка.jpg"
    image.write_bytes(jpeg)
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
    door.send_notice("Hello", str(image))
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


@pytest.mark.parametrize("filename", ["bad\0name", None])
def test_invalid_image_source_is_rejected_before_open(filename, mocker):
    opened, door = mocker.patch("doorbell.os.open"), station()
    with pytest.raises(ValueError):
        door.send_notice("Hello", filename)
    opened.assert_not_called()
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.mark.parametrize("data", [b"not JPEG", b"\xff\xd8unfinished", b"\xff\xd8" + b"x" * 524288 + b"\xff\xd9"])
def test_invalid_or_oversized_image_does_not_send(data, tmp_path, mocker):
    (tmp_path / "gate.jpg").write_bytes(data)
    door = station()
    with pytest.raises(ValueError):
        door.send_notice("Hello", str(tmp_path / "gate.jpg"))
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_missing_and_nonregular_image_do_not_send(tmp_path):
    import os
    door = station()
    with pytest.raises(FileNotFoundError):
        door.send_notice("Hello", str(tmp_path / "missing.jpg"))
    os.mkfifo(tmp_path / "pipe.jpg")
    with pytest.raises(ValueError):
        door.send_notice("Hello", str(tmp_path / "pipe.jpg"))
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_local_image_may_be_a_symlink(tmp_path):
    image = tmp_path / "gate.jpg"
    image.write_bytes(b"\xff\xd8sample\xff\xd9")
    link = tmp_path / "link.jpg"
    link.symlink_to(image)
    door = station()
    door.send_notice("Hello", str(link))
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


def test_image_at_documented_sdk_limit_is_not_truncated(tmp_path):
    assert MAX_NOTICE_IMAGE_BYTES == 524288
    image = tmp_path / "large.jpg"
    image.write_bytes(b"\xff\xd8" + b"x" * (524288 - 4) + b"\xff\xd9")
    door, lengths = station(), []

    def send(user, command, pointer, size):
        value = NET_DVR_NOTICE_DATA.from_buffer_copy(string_at(pointer, size))
        pic = value.struNoticePic[0]
        lengths.append(pic.dwPicDataLen)
        assert string_at(pic.pPicData, pic.dwPicDataLen) == image.read_bytes()
        return 1

    door._sdk.NET_DVR_RemoteControl.side_effect = send
    door.send_notice("Hello", str(image))
    assert lengths == [524288]


def download_response(mocker, chunks):
    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.return_value = iter(chunks)
    get = mocker.patch("doorbell.requests.get", return_value=response)
    return response, get


@pytest.mark.parametrize("url", ["http://example.invalid/image", "https://example.invalid/image?token=private"])
def test_http_and_https_stream_into_live_native_picture(url, mocker):
    jpeg = b"\xff\xd8sample\xff\xd9"
    response, get = download_response(mocker, [jpeg[:4], b"", jpeg[4:]])
    opened, door = mocker.patch("doorbell.os.open"), station()

    def send(user, command, pointer, size):
        value = NET_DVR_NOTICE_DATA.from_buffer_copy(string_at(pointer, size))
        pic = value.struNoticePic[0]
        assert value.byPicNum == 1 and string_at(pic.pPicData, pic.dwPicDataLen) == jpeg
        return 1

    door._sdk.NET_DVR_RemoteControl.side_effect = send
    door.send_notice("Hello", url)
    get.assert_called_once_with(url, stream=True, timeout=(5, 10))  # TLS verification is not disabled.
    response.__exit__.assert_called_once()
    opened.assert_not_called()
    door._sdk.NET_DVR_RemoteControl.assert_called_once()


def test_oversized_http_stream_stops_before_native_send(mocker):
    consumed = []

    def chunks():
        for index, chunk in enumerate([b"x" * 524288, b"x", b"never consumed"]):
            consumed.append(index)
            yield chunk

    response, get = download_response(mocker, [])
    response.iter_content.return_value = chunks()
    response.headers = {"Content-Length": "1"}  # Do not trust the claimed length.
    door = station()
    with pytest.raises(ValueError, match="512 KiB"):
        door.send_notice("Hello", "https://example.invalid/image")
    assert consumed == [0, 1]
    response.__exit__.assert_called_once()
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.mark.parametrize("error", [requests.Timeout, requests.exceptions.SSLError, requests.ConnectionError])
def test_fetch_failure_does_not_send_or_expose_url(error, mocker):
    mocker.patch("doorbell.requests.get", side_effect=error("https://example.invalid/?token=PRIVATE-TOKEN"))
    door = station()
    with pytest.raises(ValueError, match="Unable to fetch") as caught:
        door.send_notice("Hello", "https://example.invalid/?token=PRIVATE-TOKEN")
    assert "PRIVATE-TOKEN" not in str(caught.value)
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_http_error_or_nonjpeg_body_does_not_send(mocker):
    response, get = download_response(mocker, [b"an HTML error page"])
    door = station()
    with pytest.raises(ValueError, match="JPEG"):
        door.send_notice("Hello", "https://example.invalid/image")
    response.raise_for_status.side_effect = requests.HTTPError("404 PRIVATE-TOKEN")
    with pytest.raises(ValueError, match="Unable to fetch"):
        door.send_notice("Hello", "https://example.invalid/image")
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


@pytest.fixture
def controls(mocker, tmp_path):
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
            assert c.inputs[door, field].generate_config()["retain"] is True
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


def test_duplicate_edit_does_not_change_draft(controls):
    c, door = controls, controls.doors[0]
    c.edit(door, "text", "Hello")
    c.edit(door, "text", "Stale", dup=True)
    assert c.instance._notice_drafts[door]["text"] == "Hello"


def test_retained_fields_restore_draft_without_sending(controls):
    c, door = controls, controls.doors[0]
    c.edit(door, "text", "Restored text", retain=True)
    c.edit(door, "image", "gate.jpg", retain=True)
    assert c.instance._notice_drafts[door] == {"text": "Restored text", "image": "gate.jpg"}
    c.press(door, retain=True)
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_retained_edit_during_entity_construction_is_not_lost():
    door, client = station(), Mock(spec=Client)
    instance = MQTTInput.__new__(MQTTInput)
    instance._notice_drafts = {door: {"text": "", "image": ""}}
    instance._sensors = {door: {}}
    instance._notice_input_callback(client, door, message(payload=b"Restored", retain=True), "text")
    assert instance._notice_drafts[door]["text"] == "Restored"
    client.publish.assert_not_called()
    door._sdk.NET_DVR_RemoteControl.assert_not_called()


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
    c.edit(door, "image", str(c.image_dir / "missing.jpg"))
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
    c.edit(door, "image", str(c.image_dir / "gate.jpg"))
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
