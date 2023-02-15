from enum import Enum
import os
from typing import Optional
from goodconf import GoodConf
from pydantic import validator, Field, BaseModel, AnyHttpUrl
from sdk.utils import SDKLogLevel


def ha_token_from_env():
    """
    Factory function to read the environment variable SUPERVISOR_TOKEN provided when running as a HA addon.
    Invoked by pydantic when there is no HOME_ASSISTANT__TOKEN env variable set
    """
    addon_token = os.getenv('SUPERVISOR_TOKEN')
    if not addon_token:
        raise ValueError("Configure a token to authenticate to Home Assistant")
    return addon_token


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
        username: str
        password: str

    class Sensors(BaseModel):
        door: str
        callstatus: str
        motion: str
        tamper: str
        dismiss: str

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
    sensors: Sensors
    home_assistant: Optional[HomeAssistant]
    system: System

    class Config:
        env_nested_delimiter = "__"
        # Name of the environment variable defining the path to the configuration file
        file_env_var = "CONFIG_FILE_PATH"
        # Load file provided by Home Assistant supervisor when starting as a container
        # If env variable CONFIG_FILE_PATH is defined read from the provided file
        # Fallback to reading default values in `config.default.yaml``
        default_files = ["/data/options.json", "default_config.yaml"]
