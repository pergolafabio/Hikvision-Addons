"""Real discovery classes, synthetic MQTT callbacks, no broker or device."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import paho.mqtt.client as mqtt_client
from ha_mqtt_discoverable import Settings, DeviceInfo

from config import AppConfig
from doorbell import Doorbell, DeviceType, Registry
from indoor_notice import NoticeService
from indoor_notice_inputs import NoticeInputs
from mqtt_input import MQTTInput
import mqtt


def message(value, **changes):
    return SimpleNamespace(payload=value.encode() if isinstance(value, str) else value,
                           retain=changes.get("retain", False), dup=changes.get("dup", False))


@pytest.fixture
def controls(tmp_path):
    client = Mock(spec=mqtt_client.Client)
    client.is_connected.return_value = True
    client.subscribe.return_value = (mqtt_client.MQTT_ERR_SUCCESS, 1)
    settings = Settings.MQTT(host="example.invalid", client=client)
    callbacks, registered = {}, []
    client.message_callback_add.side_effect = lambda topic, callback: callbacks.__setitem__(topic, callback)
    clock = [1793674800.0]
    sdk = Mock()
    sdk.NET_DVR_RemoteControl.return_value = 1
    station = Doorbell(0, AppConfig.Doorbell(name="Indoor", ip="example.invalid", username="x", password="x"), sdk)
    station._type, station.user_id = DeviceType.INDOOR, 0
    station._device_info = SimpleNamespace(serialNumber=lambda: "synthetic-device")
    station._call_isapi = Mock(return_value='{"CallStatus":{"status":"idle"}}')
    service = NoticeService(tmp_path / "journal", tmp_path / "pictures", lambda: clock[0])
    reader = MQTTInput.__new__(MQTTInput)
    reader._notice_service, reader._notice_inputs = service, {}
    inputs = NoticeInputs(settings, DeviceInfo(name="Indoor", identifiers="synthetic-device"), "indoor", station,
                          send=lambda payload: reader._send_notice_payload(client, station, payload),
                          report=lambda result: reader._publish_notice_result(client, station, result),
                          register=registered.append, clock=lambda: clock[0])
    reader._notice_inputs[station] = inputs
    return SimpleNamespace(inputs=inputs, client=client, callbacks=callbacks, registered=registered,
                           clock=clock, station=station, sdk=sdk, service=service, reader=reader, root=tmp_path)


def edit(controls, field, value, **flags):
    entity = controls.inputs.entities[field]
    controls.callbacks[entity._command_topic](controls.client, controls.station, message(value, **flags))


def press(controls, payload=None, **flags):
    return controls.inputs.press(message(payload or controls.inputs.button._entity.payload_press, **flags))


def fill(controls, title="Проверка", text='Сообщение с "кавычками"\nи переносом'):
    edit(controls, "title", title)
    edit(controls, "text", text)


def test_discovery_controls_are_grouped_and_have_safe_command_settings(controls):
    assert len(controls.registered) == 6
    configs = [entity.generate_config() for entity in controls.registered]
    assert {c["name"] for c in configs} == {"Notice title", "Notice text", "Notice JPEG", "Notice type", "Send notice", "Notice result"}
    assert all(c["device"]["identifiers"] == "synthetic-device" for c in configs)
    assert len({c["unique_id"] for c in configs}) == 6
    assert len({c["command_topic"] for c in configs if "command_topic" in c}) == 5
    assert all(c["retain"] is False for c in configs if "command_topic" in c)
    assert controls.inputs.entities["text"].generate_config()["max"] == 255
    assert controls.inputs.entities["level"].generate_config()["options"] == ["notice", "alarm"]
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()


def test_field_callbacks_echo_without_sending_or_logging_text(controls):
    from loguru import logger
    messages = []
    handler = logger.add(lambda event: messages.append(str(event)))
    try:
        controls.client.publish.reset_mock()
        fill(controls, title="Private marker", text="PRIVATE-BODY-5b7e")
        edit(controls, "picture", "private-camera.jpg")
        assert controls.inputs.fields["text"] == "PRIVATE-BODY-5b7e"
        assert controls.inputs.fields["picture"] == "private-camera.jpg"
        writes = controls.client.publish.call_args_list
        assert any(call.args[:2] == (controls.inputs.entities["text"].state_topic, "PRIVATE-BODY-5b7e") and call.kwargs["retain"] is False for call in writes)
        assert not any("PRIVATE-BODY-5b7e" in str(log) or "private-camera.jpg" in str(log) for log in messages)
    finally:
        logger.remove(handler)
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()
    assert not (controls.root / "journal").exists()


def test_button_sends_once_and_consumes_text(controls):
    fill(controls)
    token = controls.inputs.button._entity.payload_press
    result = press(controls, token)
    assert result["status"] == "accepted"
    assert controls.inputs.fields["text"] == ""
    assert press(controls, token)["reason"] == "stale_draft_press_rejected"
    assert press(controls)["reason"] == "draft_incomplete"
    controls.sdk.NET_DVR_RemoteControl.assert_called_once()
    assert controls.inputs.last_result["send_attempted"] is False


def test_actual_button_topic_callback_uses_current_discovery_payload(controls):
    fill(controls)
    button = controls.inputs.button
    controls.callbacks[button._command_topic](controls.client, controls.station, message(button.generate_config()["payload_press"]))
    controls.sdk.NET_DVR_RemoteControl.assert_called_once()


def test_edit_invalidates_previous_button_token(controls):
    fill(controls)
    token = controls.inputs.button._entity.payload_press
    edit(controls, "text", "Новый текст")
    assert press(controls, token)["status"] == "not_sent"
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()
    assert press(controls)["status"] == "accepted"


@pytest.mark.parametrize("field,value", [("title", "я" * 32), ("text", "x" * 256), ("text", "bad\x00"),
                                         ("picture", "../secret.jpg"), ("picture", "/tmp/a.jpg"),
                                         ("picture", "https://example.invalid/a.jpg"), ("level", "other"), ("text", b"\xff")])
def test_bad_edits_block_old_draft_until_corrected(controls, field, value):
    fill(controls)
    previous = controls.inputs.fields[field]
    edit(controls, field, value)
    assert controls.inputs.fields[field] == previous
    assert press(controls)["reason"] == "draft_field_invalid"
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()
    edit(controls, field, previous)
    if field == "picture":
        assert controls.inputs.fields[field] == ""
    assert press(controls)["status"] == "accepted"


@pytest.mark.parametrize("flag", ["retain", "dup"])
def test_replayed_fields_and_button_commands_never_send(controls, flag):
    fill(controls)
    token = controls.inputs.button._entity.payload_press
    old = dict(controls.inputs.fields)
    edit(controls, "text", "Replay", **{flag: True})
    assert controls.inputs.fields == old
    assert press(controls, token, **{flag: True})["status"] == "not_sent"
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()


def test_expired_draft_never_sends_but_explicit_edit_prepares_new_request(controls):
    fill(controls)
    controls.clock[0] += 300
    assert press(controls)["reason"] == "draft_expired"
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()
    edit(controls, "text", controls.inputs.fields["text"])
    assert press(controls)["status"] == "accepted"


def test_timeout_and_restart_keep_no_retry_barrier(controls):
    fill(controls)
    controls.sdk.NET_DVR_RemoteControl.return_value = 0
    controls.sdk.NET_DVR_GetLastError.return_value = 10
    token = controls.inputs.button._entity.payload_press
    assert press(controls, token)["status"] == "unknown"
    assert press(controls, token)["duplicate"] is True
    controls.sdk.NET_DVR_RemoteControl.assert_called_once()
    edit(controls, "text", "New message")
    controls.clock[0] += 61
    assert press(controls)["reason"] == "previous_attempt_needs_review"
    controls.sdk.NET_DVR_RemoteControl.assert_called_once()
    # A fresh UI controller creates an empty draft with a new press token.
    new = NoticeInputs(controls.inputs.button._settings.mqtt, DeviceInfo(name="Indoor", identifiers="synthetic-device"),
                       "indoor", controls.station, send=Mock(), report=Mock(), register=Mock(), clock=lambda: controls.clock[0])
    assert new.fields["text"] == "" and new.fields["title"] == ""
    assert new.press(message(token))["reason"] == "stale_draft_press_rejected"
    new.send.assert_not_called()


def test_reconnect_restores_nonretained_states_and_nonce_without_sending(controls, monkeypatch):
    fill(controls)
    token = controls.inputs.button._entity.payload_press
    monkeypatch.setattr(mqtt, "_registered_entities", {})
    monkeypatch.setattr(mqtt, "_command_topics", {})
    for entity in controls.registered:
        mqtt._register_reconnect_handler(entity)
    controls.client.publish.reset_mock()
    controls.client.subscribe.reset_mock()
    mqtt._on_connect(controls.client, None)
    assert controls.inputs.button._entity.payload_press == token
    assert controls.inputs.fields["text"].startswith("Сообщение")
    assert any(call.args[:2] == (controls.inputs.entities["text"].state_topic, controls.inputs.fields["text"]) and call.kwargs["retain"] is False
               for call in controls.client.publish.call_args_list)
    assert controls.client.subscribe.call_count == 5
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()


def test_alarm_selection_and_new_explicit_message_respect_rate_limit(controls):
    import ctypes as C
    from indoor_notice import NoticeData
    levels = []
    controls.sdk.NET_DVR_RemoteControl.side_effect = lambda user, cmd, ptr, size: levels.append(C.cast(ptr, C.POINTER(NoticeData)).contents.byLevel) or 1
    fill(controls)
    edit(controls, "level", "alarm")
    assert press(controls)["status"] == "accepted"
    edit(controls, "text", "Another explicit message")
    assert press(controls)["reason"] == "rate_limited"
    controls.clock[0] += 60
    assert press(controls)["status"] == "accepted"
    assert levels == [3, 3]


def test_full_mqtt_input_creates_controls_only_for_unambiguous_indoor(controls, mocker):
    from mqtt_input import MQTTInput
    registry = Registry()
    registry[0] = controls.station
    mocker.patch("mqtt_input.get_shared_client", return_value=controls.client)
    mocker.patch("mqtt_input.extract_device_info", return_value=DeviceInfo(name="Indoor", identifiers="synthetic-device"))
    for name in ("Button", "Text", "Image", "Select", "Sensor", "_register_reconnect_handler"):
        mocker.patch("mqtt_input." + name)
    reader = MQTTInput(AppConfig.MQTT(host="example.invalid"), registry)
    assert controls.station in reader._notice_inputs
    assert len(reader._notice_inputs[controls.station].entities) == 4
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()


def test_missing_picture_preserves_draft_and_clear_is_explicit(controls):
    fill(controls)
    edit(controls, "picture", "missing.jpg")
    assert press(controls)["status"] == "not_sent"
    assert controls.inputs.fields["text"]
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()
    edit(controls, "picture", "")
    assert press(controls)["status"] == "accepted"


def test_ha_character_limit_also_fits_native_utf8_limit(controls):
    fill(controls, title="я" * 31 + "x", text="🙂" * 255)
    assert len(controls.inputs.fields["text"].encode()) == 1020
    assert press(controls)["status"] == "accepted"


def test_setup_callback_cannot_send_before_controls_are_ready(controls):
    controls.inputs.ready = False
    assert press(controls)["reason"] == "draft_not_ready"
    edit(controls, "text", "Early command")
    assert controls.inputs.fields["text"] == ""
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()


def test_two_controllers_keep_exact_device_binding_despite_userdata(controls):
    settings = controls.inputs.button._settings.mqtt
    other_device = Mock()
    other_send, other_report = Mock(return_value={"status": "accepted"}), Mock()
    other = NoticeInputs(settings, DeviceInfo(name="Second indoor", identifiers="second-synthetic"),
                         "secondindoor", other_device, send=other_send, report=other_report, register=Mock(),
                         clock=lambda: controls.clock[0])
    for field, value in (("title", "Other title"), ("text", "Other body"), ("picture", "one.jpg")):
        callback = controls.callbacks[other.entities[field]._command_topic]
        callback(controls.client, controls.station, message(value))
    callback = controls.callbacks[other.button._command_topic]
    callback(controls.client, controls.station, message(other.button._entity.payload_press))
    other_send.assert_called_once()
    assert json.loads(other_send.call_args.args[0])["picture"] == "one.jpg"
    assert controls.inputs.fields["text"] == ""
    controls.sdk.NET_DVR_RemoteControl.assert_not_called()
