import asyncio
import signal
import sys
from typing import Coroutine
from config import ADDON_CONFIG_PATH, loadConfig
from doorbell import Doorbell, Config, Registry
from event import ConsoleHandler, EventManager
from home_assistant import HomeAssistantAPI
from sdk.utils import LogLevel, SDKConfig, loadSDK, setupSDK, shutdownSDK
from loguru import logger

from input import InputReader


async def main():
    config = loadConfig(ADDON_CONFIG_PATH)

    # Remove the default handler installed by loguru (it redirects to stderr)
    logger.remove()
    logger.add(sys.stdout, colorize=True, level=config.system.log_level)
    logger.debug('Importing Hikvision SDK')

    # Setup the SDK
    sdk = loadSDK()
    logger.debug("Hikvision SDK loaded")
    sdk_log_level = config.system.sdk_log_level
    sdk_config: SDKConfig = {
        "log_level": LogLevel[sdk_log_level],
        "log_dir": "./SDKLogs"
    }
    setupSDK(sdk, sdk_config)

    event_manager = EventManager(sdk)
    console = ConsoleHandler()
    event_manager.register_handler(console)

    ha_api = HomeAssistantAPI(config)
    event_manager.register_handler(ha_api)

    doorbell_registry = Registry()
    doorbell_config: Config = {
        'ip': config.ip,
        'username': config.username,
        'password': config.password
    }
    doorbell = Doorbell(sdk, doorbell_config)
    doorbell.authenticate()

    # Add the doorbell to the registry, indexed by ID
    doorbell_registry[0] = doorbell

    # Start listening for events
    event_manager.start()
    doorbell.setup_alarm()

    input_reader = InputReader(doorbell_registry)

    input_task = asyncio.create_task(input_reader.loop_forever(), name="Input reader")

    # Register signal callback for graceful shutdown on CTRL+C or docker stopping the container
    asyncio.get_event_loop().add_signal_handler(signal.SIGINT, signal_handler, input_task)
    asyncio.get_event_loop().add_signal_handler(signal.SIGTERM, signal_handler, input_task)

    # Wait indefinitely (until we receive EOF or SIGINT and the task is cancelled)
    try:
        await input_task
    except asyncio.CancelledError:
        # The task has been cancelled by the signal handler
        pass

    logger.info("Shutting down")
    shutdownSDK(sdk)


def signal_handler(task: asyncio.Task):
    logger.debug("Received SIGINT, terminating task")
    task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
