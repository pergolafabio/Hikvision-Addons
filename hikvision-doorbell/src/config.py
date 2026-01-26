from enum import Enum
import os
from typing import Any, Optional, ClassVar
from goodconf import GoodConf
from pydantic import Field, BaseModel, AnyHttpUrl, field_validator, ConfigDict # Update imports
import requests
from sdk.utils import SDKLogLevel
from loguru import logger


def ha_token_from_env():
    """
    Factory function to read the environment variable SUPERVISOR_TOKEN.
    Returns the token if found, otherwise an empty string to be caught by validators.
    """
    return os.getenv('SUPERVISOR_TOKEN') or ""


def mqtt_config_from_supervisor():
    addon_token = os.getenv('SUPERVISOR_TOKEN')
    if not addon_token:
        return None

    auth_headers = {"Authorization": f"Bearer {addon_token}"}
    logger.debug("Requesting MQTT service configuration from supervisor")
    
    try:
        response = requests.get("http://supervisor/services/mqtt", headers=auth_headers, timeout=5)
        if response.status_code == 200:
            data = response.json().get('data', {})
            # RETURN A DICT, NOT AppConfig.MQTT(...)
            return {
                "host": data.get('host'),
                "port": int(data.get('port')),
                "ssl": data.get('ssl', False),
                "username": data.get('username'),
                "password": data.get('password')
            }
    except Exception as e:
        logger.error(f"Supervisor API unreachable: {e}")
    return None


class LogLevel(str, Enum):
    ERROR = 'ERROR'
    WARNING = 'WARNING'
    INFO = 'INFO'
    DEBUG = 'DEBUG'


class AppConfig(GoodConf):
    "Configuration for the application"

    # Fix: Replaces 'class Config' to stop deprecation warnings
    model_config = ConfigDict(
        env_nested_delimiter="__",
        file_env_var="CONFIG_FILE_PATH",
    )
    
    default_files: ClassVar[list[str]] = ["/data/options.json", "default_config.yaml"]

    class Doorbell(BaseModel):
        name: str = Field(description="Custom name of the doorbell")
        ip: str
        port: Optional[int] = 8000
        username: str
        password: str
        output_relays: Optional[int] = None
        scenes: Optional[bool] = False
        call_state_poll: Optional[int] = None

    class HomeAssistant(BaseModel):
        url: AnyHttpUrl = Field(description="Base url of Home Assistant")
        # Add min_length=1 to ensure "" triggers a ValidationError
        token: str = Field(
            description="Auth token", 
            default_factory=ha_token_from_env,
            min_length=1  
        )

        @field_validator('url')
        @classmethod
        def check_url_path(cls, v: AnyHttpUrl):
            if str(v).endswith('/'):
                raise ValueError("Url must not end with /")
            return v

    class MQTT(BaseModel):
        host: str
        port: Optional[int] = 1883
        ssl: Optional[bool] = Field(default=False)
        username: Optional[str] = None
        password: Optional[str] = None

    class System(BaseModel):
        log_level: LogLevel = LogLevel.WARNING
        sdk_log_level: SDKLogLevel = SDKLogLevel.NONE

        @field_validator('sdk_log_level', mode='before')
        @classmethod
        def from_string_to_enum(cls, v):
            try:
                return SDKLogLevel[v] if isinstance(v, str) else v
            except KeyError:
                raise ValueError(f"Supported levels: {[e.name for e in SDKLogLevel]}")

    doorbells: list[Doorbell] = Field(default_factory=list, description="List of doorbells")
    home_assistant: Optional[HomeAssistant] = None
    mqtt: Optional[MQTT] = None
    system: System = System()

    @field_validator('mqtt', mode='before')
    @classmethod
    def load_mqtt_config(cls, v):
        # If the user actually typed something in the HA config UI for MQTT, use it
        if isinstance(v, dict) and v.get('host'):
            return v
        
        # If v is None, empty, or missing, go to the supervisor
        logger.debug("MQTT config not found in options, fetching from supervisor")
        config_data = mqtt_config_from_supervisor()
        
        return config_data
