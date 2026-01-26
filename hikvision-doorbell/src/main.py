import asyncio
import signal
import socket
import os
import json
import sys
from config import AppConfig
from doorbell import Doorbell, Registry
from event import ConsoleHandler, EventManager
# from home_assistant import HomeAssistantAPI
from mqtt import MQTTHandler
from mqtt_input import MQTTInput
from config import mqtt_config_from_supervisor
from sdk.utils import SDKConfig, SDKError, loadSDK, setupSDK, shutdownSDK
from loguru import logger

from input import InputReader


async def main():
    """Main entrypoint of the application"""
    try:
        # Load data from file
        config_file = "/data/options.json"
        data = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
        
        # Ensure required fields exist
        if 'system' not in data:
            data['system'] = {}
        if 'doorbells' not in data:
            data['doorbells'] = []
        
        # Create config using Pydantic validation
        config = AppConfig(**data)
        
        # MANUALLY LOAD MQTT FROM SUPERVISOR if not provided
        if config.mqtt is None:
            try:
                mqtt_data = mqtt_config_from_supervisor()
                if mqtt_data:
                    config.mqtt = AppConfig.MQTT(**mqtt_data)
                    logger.info("MQTT configuration loaded from Supervisor")
            except Exception as mqtt_error:
                logger.warning(f"Could not load MQTT from supervisor: {mqtt_error}")
            
    except Exception as e:
        logger.error("Configuration error: {}", e)
        import traceback
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

    # Configure each doorbell
    for index, doorbell_config in enumerate(config.doorbells):
        doorbell = Doorbell(index, doorbell_config, sdk)
        doorbell.authenticate()
        # Add the doorbell to the registry, indexed by ID
        doorbell_registry[index] = doorbell

    event_manager = EventManager(sdk, doorbell_registry)
    console = ConsoleHandler()
    event_manager.register_handler(console)

    # If MQTT configuration is defined, register its event handler and its input manager
    if config.mqtt:
        mqtt = MQTTHandler(config.mqtt, doorbell_registry)
        event_manager.register_handler(mqtt)
        # Create the MQTT input to manage commands coming from HA
        _ = MQTTInput(config.mqtt, doorbell_registry)

    # Start listening for events
    event_manager.start()

    # Arm each doorbell
    for _, doorbell in doorbell_registry.items():
        doorbell.setup_alarm()

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
        except SDKError as e:
            user_message, sdk_code, sdk_message = e.args
            logger.error("{}: {} Error code: {}", user_message, sdk_message, sdk_code)
            if sdk_code == 7:
                logger.info("Failed to connect to the device, retrying again in 15 seconds...")
                await asyncio.sleep(15)
            else:
                sys.exit(1)
        except (OSError, ConnectionRefusedError) as e:
            logger.error("Error while connecting to MQTT broker: {}", e.strerror)
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main_loop())