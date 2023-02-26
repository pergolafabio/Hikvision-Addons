import asyncio
import sys
from unittest.mock import AsyncMock
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
