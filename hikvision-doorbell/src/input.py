import asyncio
import json
import sys
from typing import Callable
from loguru import logger

from doorbell import Doorbell, Registry
from sdk.utils import SDKError


async def connect_stdin():
    '''Create a reader that can read from stdin in an async-friendly way'''
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader


class InputReader():
    '''Read a string from stdin containing an instruction to execute on the remote device
    '''

    def __init__(self, doorbell_registry: Registry) -> None:
        self._registry = doorbell_registry

    async def loop_forever(self):
        stdin = await connect_stdin()
        logger.debug("Waiting for input command")
        loop = True
        while loop:
            input_bytes = await stdin.readline()
            # Check if we have reached EOF, exit loop
            if not len(input_bytes):
                return
            command = input_bytes.decode('utf-8').strip()
            # Remove double quotes if found in the input string
            command_sanitized = command.replace('"', "")
            logger.debug("Received: {}", command_sanitized)
            try:
                self.execute_command(command_sanitized)
            except SDKError as e:
                logger.error(f"Command failed: {e.args}")

    def _send_callsignal(self, doorbell: Doorbell, command: str):
        url = "/ISAPI/VideoIntercom/callSignal?format=json"
        requestBody = {
            "CallSignal": {
                "cmdType": command
            }
        }
        try:
            doorbell._call_isapi("PUT", url, json.dumps(requestBody))
        except RuntimeError:
            # Ignore error to avoid crashing application
            pass

    def _send_scene(self, doorbell: Doorbell, command: str):
        url = "/ISAPI/VideoIntercom/scene/nowMode"
        requestBody = "<SceneNowMode><nowMode>" + command  + "</nowMode></SceneNowMode>"
        try:
            doorbell._call_isapi("PUT", url, requestBody)
        except RuntimeError:
            # Ignore error to avoid crashing application
            pass       

    def _send_alarm(self, doorbell: Doorbell, command: str):
        url = "/ISAPI/SecurityCP/AlarmControlByPhone"
        requestBody = "<AlarmControlByPhoneCfg><commandType>" + command + "</commandType></AlarmControlByPhoneCfg>"
        try:
            doorbell._call_isapi("PUT", url, requestBody)
        except RuntimeError:
            # Ignore error to avoid crashing application
            pass

    def execute_command(self, command: str):
        # Split the input string in various parts
        # Expected input:
        # <command> <doorbell_name> <optional_argument>
        # Example:
        # unlock main_door door1
        arguments = command.split()
        if not arguments:
            logger.error("Received empty command")
            return

        # We expected at least a second argument: doorbell_name
        if not len(arguments) > 1:
            logger.error("Please provide the doorbell name in addition to the command")
            return

        # Get the doorbell by name from the registry
        doorbell = self._registry.getByName(arguments[1])
        if not doorbell:
            logger.error("No doorbell named {}. Remember to use lowercase characters and substitute any whitespace with _", arguments[1])
            return

        # Match the <command> part
        match arguments[0]:
            case "unlock":
                # Command is
                # unlock <doorbell_name> <door_number>
                if not len(arguments) == 3:
                    logger.error("Please provide the doorbell name and the door number to unlock")
                    return
                doorNumber = int(arguments[2])
                logger.info("Unlocking door {} on doorbell {}", doorNumber, doorbell)
                # User specifies doors starting from 1, we instead index door by 0
                doorbell.unlock_door(doorNumber - 1)
            case "answer":
                logger.info("Answering the call")
                self._send_callsignal(doorbell, "answer")
            case "reject":
                logger.info("Rejecting the call")
                self._send_callsignal(doorbell, "reject")
            case "cancel":
                logger.info("Cancelling the call")
                self._send_callsignal(doorbell, "cancle")
            case "hangUp":
                logger.info("Hanging up the call")
                self._send_callsignal(doorbell, "hangUp")
            case "request":
                logger.info("Requesting call")
                self._send_callsignal(doorbell, "request")
            case "bellTimeout":
                logger.info("Bell timeout")
                self._send_callsignal(doorbell, "bellTimeout")
            case "deviceOnCall":
                logger.info("Device on call")
                self._send_callsignal(doorbell, "deviceOnCall")
            case "atHome":
                logger.info("At home")
                self._send_scene(doorbell, "atHome")
            case "goOut":
                logger.info("Go out")
                self._send_scene(doorbell, "goOut")
            case "goToBed":
                logger.info("Go to bed")
                self._send_scene(doorbell, "goToBed")
            case "custom":
                logger.info("Custom")
                self._send_scene(doorbell, "custom")
            case "setupAlarm":
                logger.info("Alarm on")
                self._send_alarm(doorbell, "setupAlarm")
            case "closeAlarm":
                logger.info("Alarm off")
                self._send_alarm(doorbell, "closeAlarm")                
            case "reboot":
                logger.info("Rebooting door station")
                doorbell.reboot_device()
            case "debug":
                # This is a special command that accept the name of a method,
                # calls the method on the doorbell instance and outputs the result
                if not len(arguments) >= 3:
                    return
                method = arguments[2]
                try:
                    doorbell_method: Callable = getattr(doorbell, method)
                    if not callable(doorbell_method):
                        logger.error("Method {} is not a valid instance method", method)
                        return
                    logger.info("Invoking instance method {}", method)
                    result = doorbell_method()
                    logger.info("Method returned {}", result)
                except AttributeError:
                    logger.error("Instance method {} not found", method)
            case _:
                logger.error("Command not recognized: `{}`. Please see the documentation for the list of supported commands.", command)
