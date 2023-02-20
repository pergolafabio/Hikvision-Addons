import asyncio
import signal
import sys
from config import AppConfig
from doorbell import Doorbell, Registry
from event import ConsoleHandler, EventManager
from home_assistant import HomeAssistantAPI
from sdk.utils import SDKConfig, loadSDK, setupSDK, shutdownSDK
from loguru import logger

from input import InputReader


async def main():
    """Main entrypoint of the application"""

    # Disable type warnings since the object is populated at runtime using goodconfig library
    config = AppConfig()  # type:ignore
    config.load()

    # Remove the default handler installed by loguru (it redirects to stderr)
    logger.remove()
    logger.add(sys.stdout, colorize=True, level=config.system.log_level.value)
    logger.debug('Importing Hikvision SDK')

    # Setup the SDK
    sdk = loadSDK()
    logger.debug("Hikvision SDK loaded")
    sdk_config: SDKConfig = {
        "log_level": config.system.sdk_log_level,
        "log_dir": "./SDKLogs"
    }
    setupSDK(sdk, sdk_config)

    doorbell_registry = Registry()

    # Configure each doorbell
    for index, doorbell_config in enumerate(config.doorbells):
        doorbell = Doorbell(index, doorbell_config, sdk)
        doorbell.authenticate()

        # Add the doorbell to the registry, indexed by ID
        doorbell_registry[index] = doorbell

    event_manager = EventManager(sdk, doorbell_registry)
    console = ConsoleHandler()
    event_manager.register_handler(console)

    if config.home_assistant:
        ha_api = HomeAssistantAPI(config.sensors, config.home_assistant, doorbell_registry)
        event_manager.register_handler(ha_api)

    # Start listening for events
    event_manager.start()

    # Arm each doorbell
    for _, doorbell in doorbell_registry.items():
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
