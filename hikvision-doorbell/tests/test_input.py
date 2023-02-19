import pytest
from pytest_mock import MockerFixture
from input import InputReader


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
    mocked_doorbell.call_signal.assert_called_once_with("answer")


def test_reboot_command(mocker: MockerFixture):
    mocked_registry = mocker.patch('doorbell.Registry', autospec=True)
    reader = InputReader(mocked_registry)
    command = "reboot doorbell"
    reader.execute_command(command)
    mocked_registry.getByName.assert_called_once_with("doorbell")
    mocked_doorbell = mocked_registry.getByName('doorbell')
    mocked_doorbell.reboot_device.assert_called_once()
