import asyncio
from logging import config
import signal
import os
import json
import sys
import traceback
from dotenv import load_dotenv
from config import AppConfig
from doorbell import Doorbell, Registry
from event import ConsoleHandler, EventManager
from mqtt import MQTTHandler
from mqtt_input import MQTTInput
from config import mqtt_config_from_supervisor
from sdk.utils import SDKConfig, SDKError, loadSDK, setupSDK, shutdownSDK
from loguru import logger

from input import InputReader


async def retry_connection(index, doorbell_config, sdk, doorbell_registry, mqtt_handler=None):
    """Background task that retries connection for a specific doorbell indefinitely"""
    while True:
        await asyncio.sleep(30) # Wait 30 seconds before retrying
        if index not in doorbell_registry:
            try:
                logger.info(f"Retrying connection for {doorbell_config.name} (Index {index})...")
                doorbell = Doorbell(index, doorbell_config, sdk)
                doorbell.authenticate()
                doorbell.setup_alarm()

                doorbell_registry[index] = doorbell

                
                if mqtt_handler:
                    logger.info(f"Refreshing MQTT discovery for {doorbell_config.name}")
                    # This triggers the discovery/online message in HA
                    if hasattr(mqtt_handler, '_call_sensor_tasks'):
                        for task in mqtt_handler._call_sensor_tasks.values():
                            task.cancel()
                        mqtt_handler._call_sensor_tasks.clear()
                    
                    mqtt_handler.__init__(mqtt_handler._mqtt_settings, doorbell_registry)

                    from mqtt_input import MQTTInput
                    MQTTInput(mqtt_handler._mqtt_settings, doorbell_registry)

                logger.info(f"Doorbell {doorbell_config.name} is now ONLINE and armed.")
                break # Exit the loop once connected
            except Exception as e:
                logger.warning(f"Retry for {doorbell_config.name} failed: {e}")

async def main():
    """Main entrypoint of the application"""
    try:
        # Load data from file
        config_file = "/data/options.json"
        data = {}

        if not os.path.exists(config_file):
            # Try to load from environment variables for development
            env_files = [
                'development.env',
                '.env',
                '../development.env',
                '../.env'
            ]
            
            loaded = False
            for env_file in env_files:
                if os.path.exists(env_file):
                    load_dotenv(env_file)
                    logger.info(f"Loaded environment from {env_file}")
                    loaded = True
                    break
            
            if not loaded:
                logger.warning("No .env file found, using default values")
            
            data = {}
            
            # DOORBELLS is a JSON string in .env, parse it
            doorbells_json = os.getenv('DOORBELLS')
            if doorbells_json:
                try:
                    data['doorbells'] = json.loads(doorbells_json)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid DOORBELLS JSON in .env: {e}")
                    data['doorbells'] = []
            else:
                data['doorbells'] = []
            
            # System from env - using __ delimiter
            data['system'] = {
                'log_level': os.getenv('SYSTEM__LOG_LEVEL', 'DEBUG'),
                'sdk_log_level': os.getenv('SYSTEM__SDK_LOG_LEVEL', 'NONE')
            }
            
            # MQTT from env - using __ delimiter
            mqtt_host = os.getenv('MQTT__HOST')
            if mqtt_host:
                data['mqtt'] = {
                    'host': mqtt_host,
                    'port': int(os.getenv('MQTT__PORT', '1883')),
                    'ssl': os.getenv('MQTT__SSL', '').lower() == 'true',
                    'username': os.getenv('MQTT__USERNAME'),
                    'password': os.getenv('MQTT__PASSWORD')
                }
        else:
            with open(config_file, 'r') as f:
                data = json.load(f)
        
        # Ensure required fields exist
        if 'system' not in data:
            data['system'] = {}
        if 'doorbells' not in data:
            data['doorbells'] = []
        
        # If mqtt is an empty dict, remove it (will be loaded from supervisor)
        if data.get('mqtt') == {}:
            del data['mqtt']

        # Create config using Pydantic validation
        config = AppConfig(**data)
        
        # MANUALLY LOAD MQTT FROM SUPERVISOR if not provided
        if config.mqtt is None:
            try:
                mqtt_data = mqtt_config_from_supervisor()
                if mqtt_data:
                    config.mqtt = AppConfig.MQTT(**mqtt_data)
                    logger.info("MQTT configuration loaded from Supervisor")
                # ADD THIS FOR LOCAL DEVELOPMENT:
                elif not os.getenv('SUPERVISOR_TOKEN'):
                    mqtt_host = os.getenv('MQTT__HOST') 
                    if mqtt_host:
                        config.mqtt = AppConfig.MQTT(
                            host=mqtt_host,
                            port=int(os.getenv('MQTT__PORT', '1883')),
                            ssl=os.getenv('MQTT__SSL', '').lower() == 'true',
                            username=os.getenv('MQTT__USERNAME'),
                            password=os.getenv('MQTT__PASSWORD')
                        )
                        logger.info(f"Using MQTT from .env: {mqtt_host}")
            except Exception as mqtt_error:
                logger.warning(f"Could not load MQTT from supervisor: {mqtt_error}")
                if not os.getenv('SUPERVISOR_TOKEN'):
                    mqtt_host = os.getenv('MQTT__HOST')
                    if mqtt_host:
                        config.mqtt = AppConfig.MQTT(
                            host=mqtt_host,
                            port=int(os.getenv('MQTT__PORT', '1883')),
                            ssl=os.getenv('MQTT__SSL', '').lower() == 'true',
                            username=os.getenv('MQTT__USERNAME'),
                            password=os.getenv('MQTT__PASSWORD')
                        )
                        logger.info(f"Using MQTT from .env after error: {mqtt_host}")
            
    except Exception as e:
        logger.error("Configuration error: {}", e)

        traceback.print_exc()
        sys.exit(1)

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
    failed_indices = []
    # Configure each doorbell
    '''
    for index, doorbell_config in enumerate(config.doorbells):
        doorbell = Doorbell(index, doorbell_config, sdk)
        doorbell.authenticate()
        # Add the doorbell to the registry, indexed by ID
        doorbell_registry[index] = doorbell
    '''
    for index, doorbell_config in enumerate(config.doorbells):
        try:
            doorbell = Doorbell(index, doorbell_config, sdk)
            doorbell.authenticate()
            doorbell_registry[index] = doorbell
            logger.info(f"Doorbell {index} ({doorbell_config.name}) authenticated.")
        except Exception as e:
            logger.error(f"Doorbell {index} offline: {e}. Starting background recovery.")
            # START BACKGROUND TASK: Keep trying this specific doorbell
            failed_indices.append(index)

    event_manager = EventManager(sdk, doorbell_registry)
    console = ConsoleHandler()
    event_manager.register_handler(console)

    # If MQTT configuration is defined, register its event handler and its input manager
    mqtt_inst = None
    if config.mqtt:
        mqtt_inst = MQTTHandler(config.mqtt, doorbell_registry)
        event_manager.register_handler(mqtt_inst)
        # Create the MQTT input to manage commands coming from HA
        _ = MQTTInput(config.mqtt, doorbell_registry)

    # Start listening for events
    event_manager.start()

    # Arm each doorbell

    '''
    for _, doorbell in doorbell_registry.items():
        doorbell.setup_alarm()
    '''
    for index in failed_indices:
        asyncio.create_task(retry_connection(index, config.doorbells[index], sdk, doorbell_registry, mqtt_inst))

        # Arm the ones that are online
    for index, doorbell in list(doorbell_registry.items()):
        try:
            doorbell.setup_alarm()
        except Exception as e:
            logger.error(f"Failed to arm doorbell {index}: {e}")
            del doorbell_registry[index]
            # Also start retry if arming fails
            asyncio.create_task(retry_connection(index, config.doorbells[index], sdk, doorbell_registry, mqtt_inst))

    # Create reader to receive commands from STDIN
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

async def main_loop():
    while True:
        try:
            await main()
            break 
        except (OSError, ConnectionRefusedError) as e:
            logger.error(f"MQTT/Network error: {e}. Retrying in 30 seconds...")
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Restarting in 15 seconds...")
            await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(main_loop())