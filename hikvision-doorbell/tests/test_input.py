import asyncio
import sys
from unittest.mock import AsyncMock, Mock
from types import SimpleNamespace
import pytest
from pytest_mock import MockerFixture
from input import InputReader
from sdk.utils import SDKError


def test_unlock_command(mocker: MockerFixture):
    registry = mocker.patch('doorbell.Registry')
    reader = InputReader(registry)
    command = "unlock"
    reader.execute_command(command)
    registry.assert_not_called()


def test_unlock_command_wrong_name(mocker: MockerFixture):
    mocked_registry = mocker.patch('doorbell.Registry', autospec=True)
    reader = InputReader(mocked_registry)
    command = "unlock non_existing 1"
    reader.execute_command(command)
    mocked_registry.getByName.assert_called_once_with("non_existing")


def test_unlock_command_correct(mocker: MockerFixture):
    mocked_registry = mocker.patch('doorbell.Registry', autospec=True)
    reader = InputReader(mocked_registry)
    command = "unlock existing 1"
    reader.execute_command(command)
    mocked_registry.getByName.assert_called_once_with("existing")
    mocked_doorbell = mocked_registry.getByName('')
    mocked_doorbell.unlock_door.assert_called_once_with(0)


def test_callsignal_command(mocker: MockerFixture):
    mocked_registry = mocker.patch('doorbell.Registry', autospec=True)
    reader = InputReader(mocked_registry)
    command = "answer doorbell"
    reader.execute_command(command)
    mocked_registry.getByName.assert_called_once_with("doorbell")
    mocked_doorbell = mocked_registry.getByName('doorbell')
    mocked_doorbell._call_isapi.assert_called_once_with('PUT', '/ISAPI/VideoIntercom/callSignal?format=json', '{"CallSignal": {"cmdType": "answer"}}')


def test_reboot_command(mocker: MockerFixture):
    mocked_registry = mocker.patch('doorbell.Registry', autospec=True)
    reader = InputReader(mocked_registry)
    command = "reboot doorbell"
    reader.execute_command(command)
    mocked_registry.getByName.assert_called_once_with("doorbell")
    mocked_doorbell = mocked_registry.getByName('doorbell')
    mocked_doorbell.reboot_device.assert_called_once()


def test_debug_command(mocker: MockerFixture):
    mocked_registry = mocker.patch('doorbell.Registry', autospec=True)
    reader = InputReader(mocked_registry)
    command = "debug doorbell get_test"
    reader.execute_command(command)

    mocked_registry.getByName.assert_called_once_with("doorbell")
    mocked_doorbell = mocked_registry.getByName('doorbell')
    mocked_doorbell.get_test.assert_called_once()


def test_not_raise_exception(mocker: MockerFixture):
    """If there is an SDKError, the program should catch it and not crash"""
    mocked_registry = mocker.patch('doorbell.Registry', autospec=True)
    # Create a fake stdin reader
    stdin = mocker.patch('asyncio.StreamReader')
    mocker.patch('input.connect_stdin', side_effect=AsyncMock(return_value=stdin))
    # Configure the list of commands to feed the mocked stdin
    commands = [AsyncMock(return_value=bytes("reboot doorbell", 'utf-8'))(), AsyncMock(return_value=bytes("", 'utf-8'))()]
    mocker.patch.object(stdin, 'readline', side_effect=commands)
    
    # Configure doorbell to raise exception when reboot is called
    mocked_doorbell = mocked_registry.getByName('doorbell')
    mocked_doorbell.reboot_device.side_effect = SDKError(mocker.patch("ctypes.CDLL"), "")
    
    reader = InputReader(mocked_registry)

    asyncio.run(reader.loop_forever())


def test_stdin_notice_uses_existing_field_sender(mocker):
    door, service = Mock(), Mock()
    registry = Mock()
    registry.getByName.return_value = door
    mocker.patch("input.get_mqtt_input", return_value=service)
    stdin = SimpleNamespace(readline=AsyncMock(side_effect=[b'"sendNotice indoor"\n', b""]))
    mocker.patch("input.connect_stdin", new=AsyncMock(return_value=stdin))
    asyncio.run(InputReader(registry).loop_forever())
    registry.getByName.assert_called_once_with("indoor")
    service.send_notice.assert_called_once_with(door)


@pytest.mark.parametrize("command", ["sendNotice", "sendNotice missing"])
def test_stdin_notice_without_a_valid_device_does_not_send(command, mocker):
    registry = Mock()
    registry.getByName.return_value = None
    get = mocker.patch("input.get_mqtt_input")
    InputReader(registry).execute_command(command)
    get.assert_not_called()


def test_stdin_notice_before_inputs_are_ready_does_not_crash(mocker):
    mocker.patch("input.get_mqtt_input", return_value=None)
    InputReader(Mock()).execute_command("sendNotice indoor")
