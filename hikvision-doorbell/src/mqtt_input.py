import json
from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry
from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Button, ButtonInfo
from home_assistant import sanitize_doorbell_name
from loguru import logger
from mqtt import extract_device_info
from paho.mqtt.client import MQTTMessage

from sdk.utils import SDKError


class MQTTInput():
    def __init__(self, config: AppConfig.MQTT, doorbells: Registry) -> None:
        logger.debug("Setting up MQTTInput")

        mqtt_settings = Settings.MQTT(
            host=config.host,
            username=config.username,
            password=config.password
        )
        for doorbell in doorbells.values():
            doorbell_name = doorbell._config.name
            device = extract_device_info(doorbell)

            # Remove spaces and - from doorbell name
            sanitized_doorbell_name = sanitize_doorbell_name(doorbell_name)
            
            ###########
            # Reboot button
            button_info = ButtonInfo(
                name="Reboot",
                unique_id=f"{sanitized_doorbell_name}_reboot",
                device_class="restart",
                device=device,
                object_id=f"{sanitized_doorbell_name}_reboot")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            reboot_button = Button(settings, self._reboot_callback, doorbell)
            reboot_button.set_availability(True)
            
            # Consider only indoor units for the next sensors
            if doorbell._type is not DeviceType.INDOOR:
                continue

            ###########
            # Reject call button
            button_info = ButtonInfo(
                name="Reject call",
                unique_id=f"{sanitized_doorbell_name}_reject_call",
                device=device,
                object_id=f"{sanitized_doorbell_name}_reject_call")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            reject_button = Button(settings, self._reject_call_callback, doorbell)
            reject_button.set_availability(True)

    def _reboot_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.debug("Received reboot command for doorbell: {}", doorbell._config.name)
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell.reboot_device()
        except SDKError as err:
            logger.error("Error while rebooting device: {}", err)
        
    def _reject_call_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.debug("Received reject command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/VideoIntercom/callSignal?format=json"
        requestBody = {
            "CallSignal": {
                "cmdType": "reject"
            }
        }
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, json.dumps(requestBody))
        except SDKError as err:
            logger.error("Error while rejecting call: {}", err)
