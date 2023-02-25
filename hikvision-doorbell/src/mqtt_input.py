
from doorbell import DeviceType, Registry
from ha_mqtt_discoverable import Settings, DeviceInfo, Discoverable, EntityInfo, EntityType
from ha_mqtt_discoverable.sensors import Button, ButtonInfo
from paho.mqtt.client import MQTTMessage
from home_assistant import sanitize_doorbell_name
from loguru import logger

from mqtt import extract_device_info


class MQTTInput():
    def __init__(self, doorbells: Registry) -> None:
        mqtt_settings = Settings.MQTT(host="localhost")
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
            settings = Settings(mqtt=mqtt_settings, entity=button_info)
            reboot_button = Button(settings)
            reboot_button.set_callback(self._reboot_callback)
            
            # Consider only indoor units
            if doorbell._type is not DeviceType.INDOOR:
                continue

            ###########
            # Reject call button
            button_info = ButtonInfo(
                name="Reject call",
                unique_id=f"{sanitized_doorbell_name}_reject_call",
                device=device,
                object_id=f"{sanitized_doorbell_name}_reject_call")
            settings = Settings(mqtt=mqtt_settings, entity=button_info)
            reboot_button = Button(settings)
            reboot_button.set_callback(self._reject_call_callback)

    def _reboot_callback(self, client, user_data, message: MQTTMessage):
        command = message.payload.decode("utf-8")
        logger.debug("Received command from Home Assistant: {}", command)

    def _reject_call_callback(self, client, user_data, message: MQTTMessage):
        command = message.payload.decode("utf-8")
        logger.debug("Received command from Home Assistant: {}", command)