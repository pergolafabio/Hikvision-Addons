import json
import os
from types import SimpleNamespace
from typing import Optional
from loguru import logger

from sdk.utils import LogLevel

ADDON_CONFIG_PATH = os.getenv("CONFIG_PATH", "/data/options.json")
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')


class Config:
    ''' Used only for static type checking
    '''
    class System():
        log_level: str
        sdk_log_level: str

        def validate(self):
            try:
                LogLevel[self.sdk_log_level]
            except KeyError:
                raise ValueError("Please configure a valid SDK log level")

    def __init__(self) -> None:
        self.system = Config.System()

    def validate(self):
        if not self.ip:
            raise ValueError("Please configure a valid IP for the doorbell!")
        if not self.username:
            raise ValueError("Please configure a valid IP for the doorbell!")
        if not self.password:
            raise ValueError("Please configure a valid IP for the doorbell!")

    # To connect to the doorbell
    ip: str
    ip_indoor: Optional[str]
    username: str
    password: str
    # Name of the sensors in HA
    sensor_door: str
    sensor_callstatus: str
    sensor_motion: str
    sensor_tamper: str
    sensor_dismiss: str


def loadConfig(path: Optional[str] = None) -> Config:
    '''Try to load the configuration file at the given path. If not found, fallback to reading environment variables.'''
    if path and os.path.isfile(path):
        logger.debug("Loading config from file {}", path)
        with open(path) as fd:
            config = json.load(fd, object_hook=lambda d: SimpleNamespace(**d))
    else:
        logger.debug("Loading config from env variables")
        config = Config()
        config.ip = os.getenv("IP", "")
        config.ip_indoor = os.getenv("IP_INDOOR")    # Optional
        config.username = os.getenv("USERNAME", "")
        config.password = os.getenv("PASSWORD", "")

        config.sensor_door = os.getenv("SENSOR_DOOR", "hikvision_door")
        config.sensor_callstatus = os.getenv("SENSOR_CALLSTATUS", "hikvision_callstatus")
        config.sensor_motion = os.getenv("SENSOR_MOTION", "hikvision_motion")
        config.sensor_tamper = os.getenv("SENSOR_TAMPER", "hikvision_tamper")
        config.sensor_dismiss = os.getenv("SENSOR_DISMISS", "hikvision_dismiss")

        config.system.log_level = os.getenv("LOG_LEVEL", "WARNING")
        config.system.sdk_log_level = os.getenv("SDK_LOG_LEVEL", "NONE")

        config.validate()

    return config
