from enum import Enum
import os
from typing import Any, Optional
from goodconf import GoodConf
from pydantic import validator, Field, BaseModel, AnyHttpUrl
import requests
from sdk.utils import SDKLogLevel
from loguru import logger


def ha_token_from_env():
    """
    Factory function to read the environment variable SUPERVISOR_TOKEN provided when running as a HA addon.
    Invoked by pydantic when there is no HOME_ASSISTANT__TOKEN env variable set
    """
    addon_token = os.getenv('SUPERVISOR_TOKEN')
    if not addon_token:
        raise ValueError("Configure a token to authenticate to Home Assistant")
    return addon_token


def mqtt_config_from_supervisor():
    """Factory function to read MQTT configuration from the HA supervisor, used when running as a HA addon.
    If the configuration cannot be read (MQTT add-on not configured), do nothing.
    """
    # Try to get the token from the environment
    addon_token = os.getenv('SUPERVISOR_TOKEN')
    if not addon_token:
        # We are not running as an add-on, skip this step
        return

    auth_headers = {
        "Authorization": f"Bearer {addon_token}"
    }
    # Use the supervisor API to get the token configuration
    logger.debug("Requesting MQTT service configuration to supervisor")
    service_response = requests.get("http://supervisor/services/mqtt", headers=auth_headers)
    if service_response.status_code == 400:
        # MQTT addon is not configured
        logger.error("MQTT service not available")
        raise RuntimeError("This addon needs the Mosquitto broker to work correctly. Please see the Documentation tab for details.")

    if service_response.status_code != 200:
        raise RuntimeError(f"Unexpected response while requesting MQTT service: {service_response.text}")

    mqtt_config: dict[str, Any] = service_response.json()['data']

    return AppConfig.MQTT(
        host=mqtt_config['host'],
        port=mqtt_config['port'],
        ssl=mqtt_config.get('ssl'),
        username=mqtt_config.get('username'),
        password=mqtt_config.get('password')
    )


class LogLevel(str, Enum):
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'
    DEBUG = 'DEBUG'


class AppConfig(GoodConf):
    "Configuration for the application"

    class Doorbell(BaseModel):
        name: str = Field(description="Custom name of the doorbell")
        ip: str
        port: Optional[int] = 8000
        username: str
        password: str
        output_relays: Optional[int] = None   # TODO: validate it is in acceppable range!
        scenes: Optional[bool] = False

    class HomeAssistant(BaseModel):
        url: AnyHttpUrl = Field(description="Base url of Home Assistant")
        # Cannot load directly SUPERVISOR_TOKEN env variable here, since it is not supported by Pydantic
        # https://github.com/pydantic/pydantic/issues/4982
        # Use a factory function to read SUPERVISOR_TOKEN if this this field is not set by HOME_ASSISTANT__TOKEN
        token: str = Field(description="Authentication token to access the API", default_factory=ha_token_from_env)

        @validator('url')
        def check_url_path(cls, v):
            if v.path and v.path.endswith('/'):
                raise ValueError("Url must not end with /")
            return v

    class MQTT(BaseModel):
        host: str
        port: Optional[int] = 1883
        ssl: Optional[bool] = Field(default=False, description="Set to true to enable SSL")
        username: Optional[str] = None
        password: Optional[str] = None

    class System(BaseModel):
        log_level: LogLevel = LogLevel.WARNING
        sdk_log_level: SDKLogLevel = SDKLogLevel.NONE

        @validator('sdk_log_level', pre=True)
        def from_string_to_enum(cls, v):
            '''Convert from a string representation fo the SDKLogLevel enum to the actual enum instance'''
            try:
                level = SDKLogLevel[v]
            except KeyError:
                raise ValueError(f"Supported log levels: {list(value.name for value in SDKLogLevel)}")
            return level

    doorbells: list[Doorbell] = Field(description="List of doorbells to connect to")
    home_assistant: Optional[HomeAssistant]
    # Use a factory function to automatically load the MQTT configuration using the supervisor API, if MQTT is available
    mqtt: Optional[MQTT] = Field(default_factory=mqtt_config_from_supervisor)
    system: System

    @validator('mqtt', pre=True)
    def load_mqtt_config(cls, v):
        '''
        Load the MQTT configuration from the user-supplied values, if provided, or fallback to asking the HA supervisor for the integrated MQTT add-on
        '''
        # If we have no value in input, skip validation
        if v is None:
            return
        
        # If the user supplied some configuration values, ues them
        if v:
            return v

        # Try to load configuration from the HA supervisor, if running as an add-on
        logger.debug("Loading MQTT configuration from supervisor")
        config = mqtt_config_from_supervisor()
        if not config:
            raise ValueError("Cannot load MQTT configuration from supervisor")
        return config

    class Config:
        env_nested_delimiter = "__"
        # Name of the environment variable defining the path to the configuration file
        file_env_var = "CONFIG_FILE_PATH"
        # Load file provided by Home Assistant supervisor when starting as a container
        # If env variable CONFIG_FILE_PATH is defined read from the provided file
        # Fallback to reading default values in `config.default.yaml``
        default_files = ["/data/options.json", "default_config.yaml"]
