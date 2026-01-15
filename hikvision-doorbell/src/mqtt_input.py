import json
import asyncio
from typing import Any, cast
from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry, sanitize_doorbell_name
from ha_mqtt_discoverable import Settings, Discoverable
from ha_mqtt_discoverable.sensors import Button, ButtonInfo, Text, TextInfo, SensorInfo, Sensor
# from home_assistant import sanitize_doorbell_name
from loguru import logger
from mqtt import extract_device_info
from paho.mqtt.client import MQTTMessage
from sdk.hcnetsdk import (NET_DVR_JPEGPARA, NET_DVR_DEVICEINFO_V30)
import xml.etree.ElementTree as ET

from sdk.utils import SDKError


class MQTTInput():
    _sensors: dict[Doorbell, dict[str, Discoverable[Any]]] = {}

    def __init__(self, config: AppConfig.MQTT, doorbells: Registry) -> None:
        logger.debug("Setting up MQTTInput")
        # self._doorbells = doorbells
        mqtt_settings = Settings.MQTT(
            host=config.host,
            port=config.port,
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
                default_entity_id=f"{sanitized_doorbell_name}_reboot")
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
                default_entity_id=f"{sanitized_doorbell_name}_reject_call")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            reject_button = Button(settings, self._reject_call_callback, doorbell)
            reject_button.set_availability(True)

            ###########
            # Hangup call button
            button_info = ButtonInfo(
                name="Hangup call",
                unique_id=f"{sanitized_doorbell_name}_hangup_call",
                device=device,
                icon="mdi:phone-cancel",
                default_entity_id=f"{sanitized_doorbell_name}_hangup_call")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            hangup_button = Button(settings, self._hangup_call_callback, doorbell)
            hangup_button.set_availability(True)
            
            ###########
            # Answer call button
            button_info = ButtonInfo(
                name="Answer call",
                unique_id=f"{sanitized_doorbell_name}_answer_call",
                device=device,
                icon="mdi:phone-check",
                default_entity_id=f"{sanitized_doorbell_name}_answer_call")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            answer_button = Button(settings, self._answer_call_callback, doorbell)
            answer_button.set_availability(True)

            ###########
            # Mute audio output button
            button_info = ButtonInfo(
                name="Mute audio output",
                unique_id=f"{sanitized_doorbell_name}_mute_audio_output",
                device=device,
                icon="mdi:volume-mute",
                default_entity_id=f"{sanitized_doorbell_name}_mute_audio_output")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            mute_button = Button(settings, self._mute_audio_output_callback, doorbell)
            mute_button.set_availability(True)

            ###########
            # Unmute audio output button
            button_info = ButtonInfo(
                name="Unmute audio output",
                unique_id=f"{sanitized_doorbell_name}_unmute_audio_output",
                device=device,
                icon="mdi:volume-high",
                default_entity_id=f"{sanitized_doorbell_name}_unmute_audio_output")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            unmute_button = Button(settings, self._unmute_audio_output_callback, doorbell)
            unmute_button.set_availability(True)

            ###########
            # ISAPI request input text
            text_info = TextInfo(
                name="ISAPI request",
                unique_id=f"{sanitized_doorbell_name}_isapi_request",
                device=device,
                # enabled_by_default=False,
                # entity_category="diagnostic",
                default_entity_id=f"{sanitized_doorbell_name}_isapi_request")
            settings = Settings(mqtt=mqtt_settings, entity=text_info, manual_availability=True)
            isapi_text = Text(settings, self._isapi_input_callback, doorbell)
            isapi_text.set_availability(True)
            self._sensors[doorbell]['isapi_text'] = isapi_text
     
            ###########
            # Caller_info call button
            button_info = ButtonInfo(
                name="Caller info",
                unique_id=f"{sanitized_doorbell_name}_caller_info",
                device=device,
                icon="mdi:phone-log",
                default_entity_id=f"{sanitized_doorbell_name}_caller_info")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            caller_info_button = Button(settings, self._caller_info_callback, doorbell)
            caller_info_button.set_availability(True)
            self._sensors[doorbell]['caller_info'] = caller_info_button
            
            ###########
            # Call_status button
            button_info = ButtonInfo(
                name="Call status",
                unique_id=f"{sanitized_doorbell_name}_call_status",
                device=device,
                icon="mdi:phone-log",
                default_entity_id=f"{sanitized_doorbell_name}_call_status")
            settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
            call_status_button = Button(settings, self._call_status_callback, doorbell)
            call_status_button.set_availability(True)
            self._sensors[doorbell]['call_status'] = call_status_button

            if not doorbell._type is DeviceType.INDOOR:
                ###########
                # Take_snapshot button
                button_info = ButtonInfo(
                    name="Take Snapshot",
                    unique_id=f"{sanitized_doorbell_name}_take_snapshot",
                    device=device,
                    icon="mdi:camera",
                    default_entity_id=f"{sanitized_doorbell_name}_take_snapshot")
                settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
                take_snapshot_button = Button(settings, self._take_snapshot_callback, doorbell)
                take_snapshot_button.set_availability(True)
                self._sensors[doorbell]['take_snapshot'] = take_snapshot_button

            """
            ###########
            # Capture Stream button
            stream_button_info = ButtonInfo(
                name="Capture Stream",
                unique_id=f"{sanitized_doorbell_name}_capture_stream",
                device=device,
                icon="mdi:video",
                default_entity_id=f"{sanitized_doorbell_name}_capture_stream"
            )
            stream_settings = Settings(mqtt=mqtt_settings, entity=stream_button_info, manual_availability=True)
            capture_stream_button = Button(stream_settings, self._capture_stream_callback, doorbell)
            capture_stream_button.set_availability(True)
            self._sensors[doorbell]['capture_stream'] = capture_stream_button
            """


            if doorbell._config.scenes is True:
                # Define scene/alarm buttons for indoor stations: "atHome", "goOut", "goToBed", "custom", and 2 poll sensors

                ##################
                # Scene state poll sensor
                scene_sensor_info = SensorInfo(
                    name="Scene",
                    unique_id=f"{device.identifiers}-scene",
                    device=device,
                    default_entity_id=f"{sanitized_doorbell_name}_scene",
                    icon="mdi:shield")

                settings = Settings(mqtt=mqtt_settings, entity=scene_sensor_info, manual_availability=True)
                scene_sensor = Sensor(settings)
                scene_sensor.set_availability(True)
                self._sensors[doorbell]['scene_sensor'] = scene_sensor

                async def poll_scene_sensor(d=doorbell, s=scene_sensor):
                    while True:
                        try:
                            xml_string = d._call_isapi("GET", "/ISAPI/VideoIntercom/scene/nowMode")
                            root = ET.fromstring(xml_string)
                            element = root[0].text
                            # Error out if we don't find attribute
                            if element is None:
                                # Print a string representation of the response XML
                                raise RuntimeError(f'Unexpected XML response: {xml_string}')
                            s.set_state(element)
                            logger.debug("Scene sensor changed to {}", element)
                        except RuntimeError:
                            # Ignore error to avoid crashing application
                            pass
                        await asyncio.sleep(15)
                        logger.debug("Polling scene sensor every 15 sec")
                        
                loop = asyncio.get_event_loop()
                # scene_sensor_task = loop.create_task(poll_scene_sensor())
                new_task = loop.create_task(poll_scene_sensor())
                if not hasattr(self, '_scene_sensor_tasks'):
                    self._scene_sensor_tasks = {}
            
                self._scene_sensor_tasks[doorbell] = new_task

                ##################
                # alarm state poll sensor
                alarm_sensor_info = SensorInfo(
                    name="Alarm",
                    unique_id=f"{device.identifiers}-alarm",
                    device=device,
                    default_entity_id=f"{sanitized_doorbell_name}_alarm",
                    icon="mdi:alarm-check")

                settings = Settings(mqtt=mqtt_settings, entity=alarm_sensor_info, manual_availability=True)
                alarm_sensor = Sensor(settings)
                alarm_sensor.set_availability(True)
                self._sensors[doorbell]['alarm_sensor'] = alarm_sensor

                async def poll_alarm_sensor(d=doorbell, a=alarm_sensor):
                    while True:
                        try:
                            xml_string = d._call_isapi("GET", "/ISAPI/SecurityCP/AlarmControlByPhone")
                            root = ET.fromstring(xml_string)
                            element = root[0].text
                            # Error out if we don't find attribute
                            if element is None:
                                # Print a string representation of the response XML
                                raise RuntimeError(f'Unexpected XML response: {xml_string}')
                            a.set_state(element)
                            logger.debug("Alarm sensor changed to {}", element)
                        except RuntimeError:
                            # Ignore error to avoid crashing application
                            pass
                        await asyncio.sleep(15)
                        logger.debug("Polling alarm sensor every 15 sec")
                        
                loop = asyncio.get_event_loop()
                # alarm_sensor_task = loop.create_task(poll_alarm_sensor())
                new_task = loop.create_task(poll_alarm_sensor())
                if not hasattr(self, '_alarm_sensor_tasks'):
                    self._alarm_sensor_tasks = {}
            
                self._alarm_sensor_tasks[doorbell] = new_task

                ###########
                # atHome Button
                button_info = ButtonInfo(
                    name="At home",
                    unique_id=f"{sanitized_doorbell_name}_at_home",
                    device=device,
                    icon="mdi:shield-home",
                    default_entity_id=f"{sanitized_doorbell_name}_at_home")
                settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
                at_home_button = Button(settings, self._at_home_callback, doorbell)
                at_home_button.set_availability(True)

                ###########
                # goOut Button
                button_info = ButtonInfo(
                    name="Go out",
                    unique_id=f"{sanitized_doorbell_name}_go_out",
                    device=device,
                    icon="mdi:shield-lock",
                    default_entity_id=f"{sanitized_doorbell_name}_go_out")
                settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
                go_out_button = Button(settings, self._go_out_callback, doorbell)
                go_out_button.set_availability(True)

                ###########
                # goToBed Button
                button_info = ButtonInfo(
                    name="Go to bed",
                    unique_id=f"{sanitized_doorbell_name}_go_to_bed",
                    device=device,
                    icon="mdi:shield-moon",
                    default_entity_id=f"{sanitized_doorbell_name}_go_to_bed")
                settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
                go_to_bed_button = Button(settings, self._go_to_bed_callback, doorbell)
                go_to_bed_button.set_availability(True)

                ###########
                # custom Button
                button_info = ButtonInfo(
                    name="Custom",
                    unique_id=f"{sanitized_doorbell_name}_custom",
                    device=device,
                    icon="mdi:shield-star",
                    default_entity_id=f"{sanitized_doorbell_name}_custom")
                settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
                custom_button = Button(settings, self._custom_callback, doorbell)
                custom_button.set_availability(True)

                ###########
                # setupAlarm Button
                button_info = ButtonInfo(
                    name="Alarm on",
                    unique_id=f"{sanitized_doorbell_name}_setupAlarm",
                    device=device,
                    icon="mdi:alarm",
                    default_entity_id=f"{sanitized_doorbell_name}_setupAlarm")
                settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
                setupAlarm_button = Button(settings, self._setupAlarm_callback, doorbell)
                setupAlarm_button.set_availability(True)

                ###########
                # closeAlarm Button
                button_info = ButtonInfo(
                    name="Alarm off",
                    unique_id=f"{sanitized_doorbell_name}_closeAlarm",
                    device=device,
                    icon="mdi:alarm-off",
                    default_entity_id=f"{sanitized_doorbell_name}_closeAlarm")
                settings = Settings(mqtt=mqtt_settings, entity=button_info, manual_availability=True)
                closeAlarm_button = Button(settings, self._closeAlarm_callback, doorbell)
                closeAlarm_button.set_availability(True)

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
            # If error code is 23 on some indoor stations, ISAPI failed, fallback to SDK method
            logger.error("Error while rejecting the call with ISAPI: {}", err)
            error_code = err.args[1]
            if error_code == 23:
                try:
                    logger.debug("Rejecting call failed with ISAPI method, with error {} fallback to SDK method", error_code)
                    doorbell.callsignal(3)
                except SDKError as err:
                    logger.error("Error while rejecting the call with SDK: {}", err)

    def _hangup_call_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received hangup command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/VideoIntercom/callSignal?format=json"
        requestBody = {
            "CallSignal": {
                "cmdType": "hangUp"
            }
        }
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, json.dumps(requestBody))
        except SDKError as err:
            # If error code is 23 on some indoor stations, ISAPI failed, fallback to SDK method
            logger.error("Error while Hanging up the call with ISAPI: {}", err)
            error_code = err.args[1]
            if error_code == 23:
                try:
                    logger.debug("Hangup call failed with ISAPI method, with error {} fallback to SDK method", error_code)
                    doorbell.callsignal(5)
                except SDKError as err:
                    logger.error("Error while hanging up the call with SDK: {}", err)           

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
            # If error code is 23 on some indoor stations, ISAPI failed, fallback to SDK method
            logger.error("Error while answering call with ISAPI: {}", err)
            error_code = err.args[1]
            if error_code == 23:
                try:
                    logger.debug("Answering call failed with ISAPI method, with error {} fallback to SDK method", error_code)
                    doorbell.callsignal(2)
                except SDKError as err:
                    logger.error("Error while answering call with SDK: {}", err)
           
    def _caller_info_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Trying to get caller info for doorbell: {}", doorbell._config.name)
        url = "/ISAPI/VideoIntercom/callerInfo?format=json"
        requestBody = ""
        caller_info_button = cast(Button, self._sensors[doorbell]['caller_info'])
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            response = doorbell._call_isapi("GET", url, requestBody)
            logger.info("Received caller info: {} and show it as an attribute" , response)
            caller_info_button.set_attributes(json.loads(response))
        except SDKError as err:
            logger.error("Error while getting caller info with ISAPI: {}", err)
            attributes = {
                "CallerInfo": "Error while getting caller info with error code: " + str(err.args[1])
            }
            caller_info_button.set_attributes(attributes)
            
    def _call_status_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Trying to get call status for doorbell: {}", doorbell._config.name)
        url = "/ISAPI/VideoIntercom/callStatus?format=json"
        requestBody = ""
        call_status_button = cast(Button, self._sensors[doorbell]['call_status'])
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            response = doorbell._call_isapi("GET", url, requestBody)
            logger.info("Received call status: {} and show it as an attribute" , response)
            call_status_button.set_attributes(json.loads(response))
        except SDKError as err:
            logger.error("Error while getting call status with ISAPI: {}", err)
            attributes = {
                "CallStatus": "Error while getting call status with error code: " + str(err.args[1])
            }
            call_status_button.set_attributes(attributes)


    def _take_snapshot_callback(self, client, user_data: tuple[Doorbell, int], message: MQTTMessage):
        doorbell = user_data
        logger.debug("Received take snapshot commmand, doorbell: {}", doorbell._config.name)
        doorbell.take_snapshot()

    """
    def _take_snapshot_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        try:
            import os
            import re
            from datetime import datetime
            from ctypes import c_char, c_ulong, byref, c_long

            sdk = doorbell._sdk

            # Use outdoor IP if configured; otherwise fallback to general device IP
            outdoor_ip = getattr(doorbell._config, "outdoor_ip", None) or doorbell._config.ip
            if not outdoor_ip:
                logger.error("No IP configured for doorbell: {}", doorbell._config.name)
                return

            logger.info("Snapshot triggered for {}. Connecting to device on IP: {}", doorbell._config.name, outdoor_ip)

            # Login to device
            device_info = NET_DVR_DEVICEINFO_V30()
            user_id = sdk.NET_DVR_Login_V30(
                outdoor_ip.encode('utf-8'),
                8000,
                doorbell._config.username.encode('utf-8'),
                doorbell._config.password.encode('utf-8'),
                byref(device_info)
            )
            if user_id < 0:
                logger.error("Login Failed for {}: Error {}", outdoor_ip, sdk.NET_DVR_GetLastError())
                return

            try:
                # Prepare JPEG parameters
                lpJpegPara = NET_DVR_JPEGPARA()
                lpJpegPara.wPicSize = 2
                lpJpegPara.wPicQuality = 1

                # Allocate buffer
                buffer_size = 2 * 1024 * 1024  # 2MB buffer
                sJpegBuffer = (c_char * buffer_size)()
                lpRetSize = c_ulong()

                # Capture snapshot
                res = sdk.NET_DVR_CaptureJPEGPicture_NEW(
                    user_id, c_long(1), byref(lpJpegPara), sJpegBuffer, buffer_size, byref(lpRetSize)
                )
                if not res:
                    logger.error("SDK FAILURE: Error {} during capture", sdk.NET_DVR_GetLastError())
                    return

                image_data = sJpegBuffer[:lpRetSize.value]

                # Sanitize doorbell name for folder creation
                folder_name = re.sub(r'\s+', '_', doorbell._config.name.lower())

                # Determine base path
                base_path = "/media" if os.path.isdir("/media") else os.path.expanduser("~")
                output_dir = os.path.join(base_path, folder_name)
                os.makedirs(output_dir, exist_ok=True)

                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(output_dir, f"snapshot_{timestamp}.jpg")

                # Save snapshot to file
                with open(filename, "wb") as f:
                    f.write(image_data)

                logger.info("SUCCESS: Snapshot saved to {}", filename)

            finally:
                # Always logout after capturing
                sdk.NET_DVR_Logout(user_id)

        except Exception as e:
            logger.error("Internal snapshot exception: {}", str(e))
    """

    def _at_home_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received at home command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/VideoIntercom/scene/nowMode"
        requestBody = "<SceneNowMode><nowMode>atHome</nowMode></SceneNowMode>"
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, requestBody)
            scene_sensor = cast(Sensor, self._sensors[doorbell]['scene_sensor'])
            scene_sensor.set_state("atHome")
        except SDKError as err:
            logger.error("Error setting scene: {}", err)

    def _go_out_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received go out command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/VideoIntercom/scene/nowMode"
        requestBody = "<SceneNowMode><nowMode>goOut</nowMode></SceneNowMode>"
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, requestBody)
            scene_sensor = cast(Sensor, self._sensors[doorbell]['scene_sensor'])
            scene_sensor.set_state("goOut")
        except SDKError as err:
            logger.error("Error setting scene: {}", err)

    def _go_to_bed_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received go to bed command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/VideoIntercom/scene/nowMode"
        requestBody = "<SceneNowMode><nowMode>goToBed</nowMode></SceneNowMode>"
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, requestBody)
            scene_sensor = cast(Sensor, self._sensors[doorbell]['scene_sensor'])
            scene_sensor.set_state("goToBed")
        except SDKError as err:
            logger.error("Error setting scene: {}", err)

    def _custom_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received custom command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/VideoIntercom/scene/nowMode"
        requestBody = "<SceneNowMode><nowMode>custom</nowMode></SceneNowMode>"
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, requestBody)
            scene_sensor = cast(Sensor, self._sensors[doorbell]['scene_sensor'])
            scene_sensor.set_state("custom")
        except SDKError as err:
            logger.error("Error setting scene: {}", err)

    def _setupAlarm_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received setupAlarm command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/SecurityCP/AlarmControlByPhone"
        requestBody = "<AlarmControlByPhoneCfg><commandType>setupAlarm</commandType></AlarmControlByPhoneCfg>"
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, requestBody)
            alarm_sensor = cast(Sensor, self._sensors[doorbell]['alarm_sensor'])
            alarm_sensor.set_state("setupAlarm")
        except SDKError as err:
            logger.error("Error setting scene: {}", err)

    def _closeAlarm_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received closeAlarm command for doorbell: {}", doorbell._config.name)

        url = "/ISAPI/SecurityCP/AlarmControlByPhone"
        requestBody = "<AlarmControlByPhoneCfg><commandType>closeAlarm</commandType></AlarmControlByPhoneCfg>"
        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            doorbell._call_isapi("PUT", url, requestBody)
            alarm_sensor = cast(Sensor, self._sensors[doorbell]['alarm_sensor'])
            alarm_sensor.set_state("closeAlarm")
        except SDKError as err:
            logger.error("Error setting scene: {}", err)

    def _mute_audio_output_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received mute audio output command for doorbell: {}", doorbell._config.name)

        try:
            doorbell.mute_audio_output()
        except SDKError as err:
            logger.error("Error muting: {}", err)

    def _unmute_audio_output_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received unmute audio output command for doorbell: {}", doorbell._config.name)

        try:
            doorbell.unmute_audio_output()
        except SDKError as err:
            logger.error("Error unmuting: {}", err)

    def _isapi_input_callback(self, client, doorbell: Doorbell, message: MQTTMessage):
        logger.info("Received input text for doorbell: {}", doorbell._config.name)

        text_string = message.payload.decode('utf-8')

        text_entity = cast(Text, self._sensors[doorbell]['isapi_text'])
        text_entity.set_text(text_string)
        
        # Decode the HTTP method, URL and request body by splitting the input string
        http_method, url, *request_body = text_string.split()
        
        # If the user has not provided a request body, default to an empty string
        if not request_body:
            request_body = [""]

        # Avoid crashing inside the callback, otherwise we lose the MQTT client
        try:
            response = doorbell._call_isapi(http_method, url, request_body[0])
            attributes = {
                "request": text_string,
                "response": response
            }
            text_entity.set_attributes(attributes)
        except SDKError as err:
            logger.error("Error while invoking ISAPI endpoint: {}", err)
