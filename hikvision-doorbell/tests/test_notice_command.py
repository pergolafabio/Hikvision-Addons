"""Exercise actual Doorbell/MQTT adapters with no device or broker."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry
from indoor_notice import NoticeError, NoticeService
import mqtt
from mqtt_input import MQTTInput


@pytest.fixture
def station(tmp_path):
    sdk = Mock()
    sdk.NET_DVR_RemoteControl.return_value = 1
    config = AppConfig.Doorbell(name="Indoor", ip="example.invalid", username="example", password="example")
    device = Doorbell(0, config, sdk)
    device._type = DeviceType.INDOOR
    device._device_info = SimpleNamespace(serialNumber=lambda: "synthetic-station")
    device.user_id = 0
    device._call_isapi = Mock(return_value='{"CallStatus":{"status":"idle"}}')
    service = NoticeService(tmp_path / "journal", tmp_path / "pictures", lambda: 1793674800.0)
    return device, service


def payload(**changes):
    return json.dumps({"id": "ha-test", "title": "Проверка", "text": "Текст с кавычками: \"да\"",
                       "expires_at": 1793674860, **changes}, ensure_ascii=False).encode()


def test_actual_adapter_uses_existing_login_and_exact_command(station):
    device, service = station
    result = device.send_indoor_notice(payload(level="alarm"), service)
    assert result["status"] == "accepted"
    device._call_isapi.assert_called_once_with("GET", "/ISAPI/VideoIntercom/callStatus?format=json")
    assert device._sdk.NET_DVR_RemoteControl.call_args.args[0:2] == (0, 16008)
    assert device.send_indoor_notice(payload(level="alarm"), service)["duplicate"]
    device._sdk.NET_DVR_RemoteControl.assert_called_once()
    device._sdk.NET_DVR_Login_V30.assert_not_called()


@pytest.mark.parametrize("status", ["ring", "ringing", "calling", "onCall", "unknown", "unavailable", ""])
def test_busy_or_unknown_does_not_write(station, status):
    device, service = station
    device._call_isapi.return_value = json.dumps({"CallStatus": {"status": status}})
    with pytest.raises(NoticeError, match="device_not_idle"):
        device.send_indoor_notice(payload(), service)
    device._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_wrong_type_or_missing_identity_does_not_write(station):
    device, service = station
    device._type = DeviceType.OUTDOOR
    with pytest.raises(NoticeError, match="indoor_device_required"):
        device.send_indoor_notice(payload(), service)
    device._type = DeviceType.INDOOR
    device._device_info.serialNumber = lambda: ""
    with pytest.raises(NoticeError, match="identity_unavailable"):
        device.send_indoor_notice(payload(), service)
    device._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_mqtt_retained_is_rejected_and_private_payload_is_not_published(station):
    device, service = station
    reader = MQTTInput.__new__(MQTTInput)
    reader._notice_service = service
    client = Mock()
    message = SimpleNamespace(payload=payload(), retain=True)
    result = reader._notice_callback(client, device, message)
    assert result["status"] == "not_sent"
    device._sdk.NET_DVR_RemoteControl.assert_not_called()
    message.retain = False
    result = reader._notice_callback(client, device, message)
    assert result["status"] == "accepted"
    topic, output = client.publish.call_args.args
    assert topic == "hikvision/indoor/notice/result"
    assert "Текст" not in output and "synthetic-station" not in output
    assert client.publish.call_args.kwargs == {"qos": 1, "retain": False}


@pytest.mark.parametrize("raw", [b"{}", b"bad", payload(expires_at=0), payload(picture="../secret.jpg")])
def test_mqtt_bad_commands_do_not_crash_or_send(station, raw):
    device, service = station
    reader = MQTTInput.__new__(MQTTInput)
    reader._notice_service = service
    result = reader._notice_callback(Mock(), device, SimpleNamespace(payload=raw, retain=False))
    assert result["status"] == "not_sent"
    device._sdk.NET_DVR_RemoteControl.assert_not_called()


def test_exact_topic_registration_survives_reconnect(monkeypatch):
    monkeypatch.setattr(mqtt, "_command_topics", {})
    monkeypatch.setattr(mqtt, "_registered_entities", {})
    client, callback = Mock(), Mock()
    mqtt._register_command_topic(client, "hikvision/indoor/notice/set", callback)
    client.message_callback_add.assert_called_once_with("hikvision/indoor/notice/set", callback)
    client.subscribe.reset_mock()
    mqtt._on_connect(client, None)
    client.subscribe.assert_called_once_with("hikvision/indoor/notice/set", qos=1)


def test_ambiguous_names_disable_notice_topic(station, mocker):
    device, service = station
    second = Doorbell(1, AppConfig.Doorbell(name="In-door", ip="example.invalid", username="x", password="x"), Mock())
    second._type = DeviceType.INDOOR
    second._device_info = device._device_info
    second.user_id = 1
    registry = Registry()
    registry[0], registry[1] = device, second
    mocker.patch("mqtt_input.get_shared_client", return_value=Mock(spec=mqtt.mqtt.Client))
    from ha_mqtt_discoverable import DeviceInfo
    mocker.patch("mqtt_input.extract_device_info", return_value=DeviceInfo(name="example", identifiers="fixture"))
    for name in ("Button", "Text", "Image", "Select", "Sensor", "_register_reconnect_handler"):
        mocker.patch("mqtt_input." + name)
    register = mocker.patch("mqtt_input._register_command_topic")
    MQTTInput(AppConfig.MQTT(host="example.invalid"), registry)
    register.assert_not_called()
