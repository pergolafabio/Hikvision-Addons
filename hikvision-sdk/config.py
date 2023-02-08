import json
import os
import logging
import sys
from typing import TypedDict

logger = logging.getLogger(__name__)

CONFIGURATION_FILE_PATH = "/data/options.json"

# Used only for static type checking
class Config(TypedDict):
    # To connect to the doorbell
    ip: str
    ip_indoor: str
    username: str
    password: str
    # Name of the sensors in HA
    sensor_door: str
    sensor_callstatus: str
    sensor_motion: str
    sensor_tamper: str
    sensor_dismiss: str

# Try to load the configuration file provided by HA supervisor. If not found, fallback to env variables
if os.path.isfile(CONFIGURATION_FILE_PATH):
    logger.debug("Loading config from file")
    with open("/data/options.json") as fd:
        config: Config = json.load(fd)
else:
    logger.debug("Loading config from env variables")
    config: Config = {
        "ip": os.getenv("IP"),
        "ip_indoor": os.getenv("IP_INDOOR"),    # Optional
        "username": os.getenv("USERNAME"),
        "password": os.getenv("PASSWORD"),

        "sensor_door": os.getenv("SENSOR_DOOR", "hikvision_door"),
        "sensor_callstatus": os.getenv("SENSOR_CALLSTATUS", "hikvision_callstatus"),
        "sensor_motion": os.getenv("SENSOR_MOTION", "hikvision_motion"),
        "sensor_tamper": os.getenv("SENSOR_TAMPER", "hikvision_tamper"),
        "sensor_dismiss": os.getenv("SENSOR_DISMISS", "hikvision_dismiss")
    }


def validateConfig(config: Config):
    if not config['ip']:
        logger.error("Please configure a valid IP for the doorbell!")
        sys.exit(1)
    if not config['username']:
        logger.error("Please configure a valid username for the doorbell!")
        sys.exit(1)
    if not config['password']:
        logger.error("Please configure a valid password for the doorbell!")
        sys.exit(1)

supervisor_token = os.getenv('SUPERVISOR_TOKEN')

# Validate configuration after loading it
validateConfig(config)
