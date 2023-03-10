import json
from typing import Any
from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry
from ha_mqtt_discoverable import Settings, Discoverable
from ha_mqtt_discoverable.sensors import Button, ButtonInfo, Text, TextInfo
from home_assistant import sanitize_doorbell_name
from loguru import logger
from mqtt import extract_device_info
from paho.mqtt.client import MQTTMessage

from sdk.utils import SDKError


class MQTTInput():
    _sensors: dict[Doorbell, dict[str, Discoverable[Any]]] = {}

    def __init__(self, config: AppConfig.MQTT, doorbells: Registry) -> None:
        logger.debug("Setting up MQTTInput")

        mqtt_settings = Settings.MQTT(
            host=config.host,
            username=config.username,
            password=config.password
        )
        for doorbell in doorbells.values():
            self._sensors[doorbell] = {}

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
            # if doorbell._type is not DeviceType.INDOOR:
            #    continue

            ###########
            # Reject call button
            button_info = ButtonInfo(
                name="Reject call",
                unique_id=f"{sanitized_doorbell_name}_reject_call",
                device=device,
                icon="mdi:phone-cancel",
                object_id=f"{sanitized_doorbell_name}_reject_call")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            reject_button = Button(settings, self._reject_call_callback, doorbell)
            reject_button.set_availability(True)

            ###########
            # Answer call button
            button_info = ButtonInfo(
                name="Answer call",
                unique_id=f"{sanitized_doorbell_name}_answer_call",
                device=device,
                icon="mdi:phone-check",
                object_id=f"{sanitized_doorbell_name}_answer_call")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            answer_button = Button(settings, self._answer_call_callback, doorbell)
            answer_button.set_availability(True)

            ###########
            # ISAPI command input text
            text_info = TextInfo(
                name="ISAPI endpoint",
                unique_id=f"{sanitized_doorbell_name}_isapi_endpoint",
                device=device,
                enabled_by_default=False,
                entity_category="diagnostic",
                object_id=f"{sanitized_doorbell_name}_isapi_endpoint")
            settings = Settings(mqtt=mqtt_settings, entity=text_info, manual_availability=True)
            isapi_input = Text(settings, self._isapi_input_callback, doorbell)
            isapi_input.set_availability(True)
            self._sensors[doorbell]['isapi_input'] = isapi_input

    def _reboot_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received reboot command for doorbell: {}", doorbell._config.name)
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell.reboot_device()
        except SDKError as err:
            logger.error("Error while rebooting device: {}", err)
        
    def _reject_call_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received reject command for doorbell: {}", doorbell._config.name)

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

    def _answer_call_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received answer command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/VideoIntercom/callSignal?format=json"
        requestBody = {
            "CallSignal": {
                "cmdType": "answer"
            }
        }
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, json.dumps(requestBody))
        except SDKError as err:
            logger.error("Error while answering call: {}", err)

    def _isapi_input_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.debug("Received input text for doorbell: {}", doorbell._config.name)

        text_string = message.payload.decode('utf-8')
        self._sensors[doorbell]['isapi_input'].set_text(text_string)
        
        # Decode the HTTP method and URL by splitting the input string
        http_method, url = text_string.split()
        request_body = ""

        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            response = doorbell._call_isapi(http_method, url, request_body)
            attributes = {
                "request": text_string,
                "response": response
            }
            self._sensors[doorbell]['isapi_input'].set_attributes(attributes)
        except SDKError as err:
            logger.error("Error while invoking ISAPI endpoint: {}", err)
