import asyncio
from ctypes import c_void_p
import sys
from config import ADDON_CONFIG_PATH, loadConfig
from doorbell import Doorbell, Config
from event import EventHandler, EventManager
from sdk.hcnetsdk import NET_DVR_ALARMER, NET_DVR_ALARMINFO_V30, NET_DVR_VIDEO_INTERCOM_ALARM, NET_DVR_VIDEO_INTERCOM_EVENT
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

    manager = EventManager(sdk)
    handler = ConsoleHandler()
    manager.register_handler(handler)

    doorbell_config: Config = {
        'ip': config.ip,
        'username': config.username,
        'password': config.password
    }
    doorbell = Doorbell(sdk, doorbell_config)
    doorbell.authenticate()
    manager.start()
    doorbell.setup_alarm()

    # Wait for event
    await handler.end.wait()


class ConsoleHandler(EventHandler):
    name = 'ConsoleOutput'
    
    end = asyncio.Event()
    
    async def motion_detection(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_ALARMINFO_V30, buffer_length, user_pointer: c_void_p):
        logger.info("Motion detected from {}", device.deviceIP())
    
    async def video_intercom_event(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_VIDEO_INTERCOM_EVENT, buffer_length, user_pointer: c_void_p):
        raise NotImplementedError
    
    async def video_intercom_alarm(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_VIDEO_INTERCOM_ALARM, buffer_length, user_pointer: c_void_p):
        raise NotImplementedError

    async def unhandled_event(self, command: int, device: NET_DVR_ALARMER, alarm_info_pointer, buffer_length, user_pointer: c_void_p):
        raise NotImplementedError


if __name__ == "__main__":
    asyncio.run(main())
