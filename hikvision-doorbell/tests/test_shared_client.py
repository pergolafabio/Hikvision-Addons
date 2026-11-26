"""Behaviour of the MQTT client shared by the entities of a doorbell, against a minimal in-process broker."""
import asyncio
import json
import socket
import struct
import threading
import time
from typing import Optional

import pytest
from ha_mqtt_discoverable import DeviceInfo, Settings
from ha_mqtt_discoverable.sensors import Button, ButtonInfo
from paho.mqtt.client import Client
from pytest_mock import MockerFixture

import main
import mqtt
from config import AppConfig
from doorbell import Registry


class StubBroker:
    """Accept MQTT connections, remember the will and the messages received, and allow to publish to the clients"""

    def __init__(self, port: int = 0, answer_connect: bool = True):
        self.answer_connect = answer_connect
        self.wills: list[Optional[tuple[str, bytes, bool]]] = []
        self.published: dict[str, bytes] = {}
        self.subscribed: set[str] = set()
        self._connections: list[socket.socket] = []
        self._server = socket.create_server(("127.0.0.1", port))
        self.port = self._server.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def open_connections(self) -> int:
        return len(self._connections)

    def publish(self, topic: str, payload: bytes):
        body = struct.pack("!H", len(topic)) + topic.encode() + payload
        for connection in self._connections:
            connection.sendall(bytes([0x30]) + self._encode_length(len(body)) + body)

    def close(self):
        for connection in [self._server, *self._connections]:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # Already closed
        self._server.close()

    @staticmethod
    def _encode_length(length: int) -> bytes:
        encoded = bytearray()
        while True:
            length, digit = length // 128, length % 128
            encoded.append(digit | (0x80 if length else 0))
            if not length:
                return bytes(encoded)

    def _accept(self):
        while True:
            try:
                connection, _ = self._server.accept()
            except OSError:
                return
            self._connections.append(connection)
            threading.Thread(target=self._serve, args=(connection,), daemon=True).start()

    def _serve(self, connection: socket.socket):
        stream = connection.makefile("rb")
        try:
            while True:
                header = stream.read(1)
                if not header:
                    break
                length, shift = 0, 0
                while True:
                    digit = stream.read(1)[0]
                    length |= (digit & 0x7F) << shift
                    shift += 7
                    if not digit & 0x80:
                        break
                self._handle(connection, header[0], stream.read(length))
        except (OSError, IndexError, ValueError):
            pass
        finally:
            self._connections.remove(connection)

    def _handle(self, connection: socket.socket, header: int, body: bytes):
        packet = header >> 4
        if packet == 1:  # CONNECT
            self.wills.append(self._parse_will(body))
            if self.answer_connect:
                connection.sendall(b"\x20\x02\x00\x00")
        elif packet == 3:  # PUBLISH
            size = struct.unpack("!H", body[:2])[0]
            topic, rest = body[2:2 + size].decode(), body[2 + size:]
            if (header >> 1) & 3:
                connection.sendall(b"\x40\x02" + rest[:2])
                rest = rest[2:]
            self.published[topic] = rest
        elif packet == 8:  # SUBSCRIBE
            size = struct.unpack("!H", body[2:4])[0]
            self.subscribed.add(body[4:4 + size].decode())
            connection.sendall(b"\x90\x03" + body[:2] + b"\x01")

    @staticmethod
    def _parse_will(body: bytes) -> Optional[tuple[str, bytes, bool]]:
        # Protocol name (6 bytes), protocol level, flags, keep alive (2 bytes), client ID
        flags, position = body[7], 10

        def field() -> bytes:
            nonlocal position
            size = struct.unpack("!H", body[position:position + 2])[0]
            value = body[position + 2:position + 2 + size]
            position += 2 + size
            return value
        field()
        if not flags & 0x04:
            return None
        return field().decode(), field(), bool(flags & 0x20)


def wait_until(condition, timeout: float = 5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.01)
    return False


def free_port() -> int:
    with socket.create_server(("127.0.0.1", 0)) as server:
        return server.getsockname()[1]


@pytest.fixture
def broker():
    broker = StubBroker()
    yield broker
    broker.close()


@pytest.fixture(autouse=True)
def clients(monkeypatch: pytest.MonkeyPatch):
    """Start without shared clients, and stop the ones created by the test"""
    clients: dict[str, mqtt.mqtt.Client] = {}
    monkeypatch.setattr(mqtt, "_shared_clients", clients)
    monkeypatch.setattr(mqtt, "_registered_entities", {})
    monkeypatch.setattr(mqtt, "_mqtt_broker_online", True)
    yield clients
    for client in clients.values():
        client.disconnect()
        client.loop_stop()


def get_client(port: int, doorbell_name: str = "Door"):
    return mqtt.get_shared_client(AppConfig.MQTT(host="127.0.0.1", port=port), doorbell_name)


def add_button(client, broker: StubBroker, name: str, callback, doorbell_name: str = "Door") -> Button:
    info = ButtonInfo(name=name, unique_id=name, device=DeviceInfo(name=doorbell_name, identifiers=doorbell_name))
    settings = Settings(mqtt=Settings.MQTT(host="127.0.0.1", client=client), entity=info, manual_availability=True)
    button = Button(settings, callback)
    button.set_availability(True)
    mqtt._register_reconnect_handler(button)
    assert wait_until(lambda: f"hmd/button/{doorbell_name}/{name}/command" in broker.subscribed)
    return button


def published_availability_topic(broker: StubBroker, doorbell_name: str = "Door") -> str:
    """The topic Home Assistant reads the availability of the entity from"""
    config_topic = f"homeassistant/button/{doorbell_name}/Unlock/config"
    assert wait_until(lambda: config_topic in broker.published)
    return json.loads(broker.published[config_topic])["availability_topic"]


def test_connection_error_is_reported_and_the_next_call_connects():
    port = free_port()
    with pytest.raises(OSError):
        get_client(port)

    broker = StubBroker(port)
    try:
        assert get_client(port).is_connected()
    finally:
        broker.close()


def test_client_is_connected_when_returned(broker: StubBroker):
    # Entities created before the connection is established may never subscribe to their command topic
    assert get_client(broker.port).is_connected()


def test_broker_that_never_accepts_the_connection_is_reported(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(mqtt, "CONNECT_TIMEOUT_SECONDS", 0.3)
    broker = StubBroker(answer_connect=False)
    try:
        with pytest.raises(OSError):
            get_client(broker.port)
        # The failed client must not stay around and keep reconnecting
        assert wait_until(lambda: broker.open_connections() == 0)

        broker.answer_connect = True
        assert get_client(broker.port).is_connected()
    finally:
        broker.close()


def test_client_is_shared_by_the_entities_of_a_doorbell(broker: StubBroker):
    assert get_client(broker.port, "Front") is get_client(broker.port, "Front")
    assert get_client(broker.port, "Front") is not get_client(broker.port, "Indoor")


def test_last_will_marks_the_entities_unavailable(broker: StubBroker):
    add_button(get_client(broker.port), broker, "Unlock", lambda *_: None)

    assert broker.wills[0] is not None, "the client has no last will"
    topic, payload, retain = broker.wills[0]
    assert topic == published_availability_topic(broker)
    assert payload == b"offline"
    assert retain


def test_entities_are_available_after_connecting(broker: StubBroker):
    add_button(get_client(broker.port), broker, "Unlock", lambda *_: None)

    assert wait_until(lambda: broker.published.get(published_availability_topic(broker)) == b"online")


def test_doorbell_that_is_not_set_up_is_not_available(broker: StubBroker):
    # The entities of a doorbell that is offline at startup are still known by Home Assistant
    previous_run = StubBroker()
    get_client(previous_run.port, "Indoor")
    previous_run.close()
    assert previous_run.wills[0] is not None, "the client has no last will"
    indoor_topic = previous_run.wills[0][0]

    add_button(get_client(broker.port, "Front"), broker, "Unlock", lambda *_: None, "Front")

    assert wait_until(lambda: broker.published.get(published_availability_topic(broker, "Front")) == b"online")
    assert indoor_topic not in broker.published


def test_exception_in_a_command_does_not_stop_the_other_commands(broker: StubBroker):
    client = get_client(broker.port)
    unlocked = threading.Event()

    def failing(*_):
        raise AttributeError("'NoneType' object has no attribute '_config'")

    add_button(client, broker, "Failing", failing)
    add_button(client, broker, "Unlock", lambda *_: unlocked.set())

    broker.publish("hmd/button/Door/Failing/command", b"PRESS")
    broker.publish("hmd/button/Door/Unlock/command", b"PRESS")

    assert unlocked.wait(3), "the MQTT thread stopped"


def test_slow_command_does_not_delay_another_doorbell(broker: StubBroker):
    release, started, unlocked = threading.Event(), threading.Event(), threading.Event()

    def slow(*_):
        started.set()
        release.wait(5)

    add_button(get_client(broker.port, "Indoor"), broker, "Scene", slow, "Indoor")
    add_button(get_client(broker.port, "Front"), broker, "Unlock", lambda *_: unlocked.set(), "Front")
    try:
        broker.publish("hmd/button/Indoor/Scene/command", b"PRESS")
        assert started.wait(3)
        broker.publish("hmd/button/Front/Unlock/command", b"PRESS")
        assert unlocked.wait(3), "the command waited for the one of the other doorbell"
    finally:
        release.set()


def test_commands_and_availability_are_restored_after_reconnecting(broker: StubBroker):
    client = get_client(broker.port)
    pressed = threading.Event()
    add_button(client, broker, "Unlock", lambda *_: pressed.set())
    topic, port = published_availability_topic(broker), broker.port
    broker.close()
    assert wait_until(lambda: not client.is_connected())

    restarted = StubBroker(port)
    try:
        assert wait_until(lambda: "hmd/button/Door/Unlock/command" in restarted.subscribed, 10)
        assert wait_until(lambda: restarted.published.get(topic) == b"online")
        restarted.publish("hmd/button/Door/Unlock/command", b"PRESS")
        assert pressed.wait(3)
    finally:
        restarted.close()


@pytest.fixture
def recovering(mocker: MockerFixture):
    """A doorbell that was offline at startup, and is back online when the connection is retried"""
    for entity in ("Sensor", "Switch"):
        mocker.patch(f"mqtt.{entity}")
    mocker.patch("mqtt_input.MQTTInput")
    mocker.patch("mqtt.extract_device_info", return_value=DeviceInfo(name="Front", identifiers="id"))
    # Give up after a few attempts
    mocker.patch("main.asyncio.sleep", side_effect=[None, None, TimeoutError("the doorbell was not recovered")])
    doorbell = mocker.patch("main.Doorbell").return_value
    doorbell._config.name = "Front"
    doorbell._config.call_state_poll = None
    doorbell._config.online_sensor = False
    doorbell.get_num_outputs.return_value = 0
    return doorbell


def test_recovered_doorbell_connects_with_the_same_config(recovering, mocker: MockerFixture):
    config = AppConfig.MQTT(host="localhost", ssl=True, username="user")
    get_shared_client = mocker.patch("mqtt.get_shared_client", return_value=Client())
    registry = Registry()
    handler = mqtt.MQTTHandler(config, registry)

    asyncio.run(main.retry_connection(0, recovering._config, None, registry, handler))

    get_shared_client.assert_called_once_with(config, "Front")


def test_recovery_is_retried_when_the_broker_is_down(recovering, mocker: MockerFixture):
    mocker.patch("mqtt.get_shared_client", side_effect=[ConnectionRefusedError, Client()])
    registry = Registry()
    handler = mqtt.MQTTHandler(AppConfig.MQTT(host="localhost"), registry)

    asyncio.run(main.retry_connection(0, recovering._config, None, registry, handler))

    assert "call" in handler._sensors[recovering]
    # Do not log in twice, the events would be received twice
    recovering.authenticate.assert_called_once()
