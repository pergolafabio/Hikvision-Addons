import os
import sys
sys.path.append("src")

import asyncio
from ctypes import c_void_p

from doorbell import Config, Doorbell
from event import EventHandler, EventManager
from loguru import logger
from sdk.hcnetsdk import (NET_DVR_ALARMER, NET_DVR_ALARMINFO_V30)
from sdk.utils import LogLevel, SDKConfig, loadSDK, setupSDK


class ConsoleHandler(EventHandler):
    name='ConsoleHandler'

    async def motion_detection(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_ALARMINFO_V30, buffer_length, user_pointer: c_void_p):
        logger.debug("Hello from console handler!")
        await asyncio.sleep(10)

async def event_handler():        

    sdk = loadSDK()
    sdk_config: SDKConfig = {
        'log_level': LogLevel.DEBUG,
        'log_dir': str('/tmp/SDKLog')
    }
    setupSDK(sdk, sdk_config)

    config: Config = {
        "ip": os.getenv("IP", ""),
        "username": os.getenv("USERNAME", ""),
        "password": os.getenv("PASSWORD", ""),
    }

    event_handler = EventManager(sdk)

    a = Doorbell(sdk, config)
    a.authenticate()
    console_handler = ConsoleHandler()
    event_handler.register_handler(console_handler)
    event_handler.start()

    a.start_listening()
    
    await asyncio.sleep(1000000)

asyncio.run(event_handler())