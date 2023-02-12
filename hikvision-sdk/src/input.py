
import asyncio
import sys
from loguru import logger

from doorbell import Registry


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
            logger.debug("Received: {}", command)
            self.execute_command(command)

    def execute_command(self, command: str):
        # Callsignal keywords : "request,cancle,answer,reject,bellTimeout,hangUp,deviceOnCall"
        match command:
            case "unlock1":
                # TODO handle multiple doorbells?
                logger.info("Unlocking door 1 on doorbell {}", 0)
                self._registry[0].unlock_door(0)
            case "unlock2":
                # TODO handle multiple doorbells?
                logger.info("Unlocking door 2 on doorbell {}", 0)
                self._registry[0].unlock_door(0)
            case "answer":
                logger.info("Answering the call")
                # callsignal("answer")
            case "reject":
                logger.info("Rejecting the call")
                # callsignal("reject")
            case "cancle":
                # TODO: fix typo
                logger.info("Cancelling the call")
                # callsignal("cancle")
            case "hangUp":
                logger.info("Hanging up the call")
                # callsignal("hangUp")
            case "request":
                logger.info("Requesting call")
                # callsignal("request")
            case "bellTimeout":
                logger.info("Bell timeout")
                # callsignal("bellTimeout")
            case "deviceOnCall":
                logger.info("Device on call")
                # callsignal("deviceOnCall")
            case "reboot":
                logger.info("Rebooting doorstation")
                # reboot_device()
            case _:
                logger.error("Command not recognized: `{}`. Please see the documentation for the list of supported commands.", command)
