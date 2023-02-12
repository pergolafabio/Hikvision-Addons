import asyncio
import sys
from config import ADDON_CONFIG_PATH, loadConfig
from doorbell import Doorbell, Config
from event import ConsoleHandler, EventManager
from home_assistant import HomeAssistantAPI
from sdk.utils import LogLevel, SDKConfig, loadSDK, setupSDK
from loguru import logger


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

    doorbell_config: Config = {
        'ip': config.ip,
        'username': config.username,
        'password': config.password
    }
    doorbell = Doorbell(sdk, doorbell_config)
    doorbell.authenticate()
    event_manager.start()
    doorbell.setup_alarm()

    # Wait indefinitely
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
