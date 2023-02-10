import json
import os
import pathlib
import sys
from typing import Optional, TypedDict
from loguru import logger

ADDON_CONFIG_PATH = "/data/options.json"
SUPERVISOR_TOKEN = os.getenv('SUPERVISOR_TOKEN')

class Config(TypedDict):
    ''' Used only for static type checking
    '''

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
    
    system: dict

def loadConfig(path: Optional[str]=None) -> Config:
    '''Try to load the configuration file at the given path. If not found, fallback to reading environment variables.'''
    if path and os.path.isfile(path):
        logger.debug("Loading config from file {}", path)
        with open(path) as fd:
            return json.load(fd)
    else:
        logger.debug("Loading config from env variables")
        config: Config = {
            "ip": os.getenv("IP", ""),
            "ip_indoor": os.getenv("IP_INDOOR"),    # Optional
            "username": os.getenv("USERNAME", ""),
            "password": os.getenv("PASSWORD", ""),

            "sensor_door": os.getenv("SENSOR_DOOR", "hikvision_door"),
            "sensor_callstatus": os.getenv("SENSOR_CALLSTATUS", "hikvision_callstatus"),
            "sensor_motion": os.getenv("SENSOR_MOTION", "hikvision_motion"),
            "sensor_tamper": os.getenv("SENSOR_TAMPER", "hikvision_tamper"),
            "sensor_dismiss": os.getenv("SENSOR_DISMISS", "hikvision_dismiss"),

            "system": {
                "log_level": os.getenv("LOG_LEVEL", "WARNING")
            }
        }
        return config


def validateConfig(config: Config):
    if not config['ip']:
        logger.error("Please configure a valid IP for the doorbell!")
        raise ValueError
    if not config['username']:
        logger.error("Please configure a valid username for the doorbell!")
        raise ValueError
    if not config['password']:
        logger.error("Please configure a valid password for the doorbell!")
        raise ValueError
