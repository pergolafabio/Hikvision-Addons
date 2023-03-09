import asyncio
from ctypes import c_void_p
from typing import Any, Optional, TypedDict, cast
from config import AppConfig

from doorbell import DeviceType, Doorbell, Registry
from event import EventHandler
from paho.mqtt.client import MQTTMessage
from ha_mqtt_discoverable import Settings, DeviceInfo, Discoverable
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo, SensorInfo, Sensor, SwitchInfo, Switch, DeviceTrigger, DeviceTriggerInfo
from loguru import logger
from home_assistant import sanitize_doorbell_name
from sdk.hcnetsdk import (NET_DVR_ALARMER,
                          NET_DVR_ALARMINFO_V30,
                          NET_DVR_VIDEO_INTERCOM_ALARM,
                          NET_DVR_VIDEO_INTERCOM_EVENT,
                          NET_DVR_ALARM_ISAPI_INFO,
                          VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN,
                          VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG,
                          VideoInterComAlarmType)
from typing_extensions import override


def extract_device_info(doorbell: Doorbell) -> DeviceInfo:
    device_info = doorbell.get_device_info()
    # Dict to contain the extracted device information
    parsed_device_info: dict[str, Optional[str]] = {}
    model_element = device_info.find('{*}model')
    parsed_device_info["model"] = model_element.text if model_element is not None and model_element.text else None
    firmware_element = device_info.find('{*}firmwareVersion')
    parsed_device_info["firmware"] = firmware_element.text if firmware_element is not None and firmware_element.text else None
    hw_element = device_info.find('{*}hardwareVersion')
    parsed_device_info["hardware"] = hw_element.text if hw_element is not None and hw_element.text else None

    # Define the device struct
    return DeviceInfo(
        name=doorbell._config.name,
        identifiers=doorbell._device_info.serialNumber(),
        manufacturer="Hikvision",
        model=parsed_device_info["model"],
        sw_version=parsed_device_info["firmware"],
        hw_version=parsed_device_info["hardware"]
    )


class DeviceTriggerMetadata(TypedDict):
    """Helper subclass defining the information of a device trigger.
    Used when building the DeviceTrigger entity"""
    name: str
    """Name of this device trigger"""
    type: str
    """Displayed in the HA UI"""
    subtype: str
    """Displayed in the HA UI"""


DEVICE_TRIGGERS_DEFINITIONS: dict[VideoInterComAlarmType, DeviceTriggerMetadata] = {
    VideoInterComAlarmType.ZONE_ALARM: DeviceTriggerMetadata(name='zone_alarm', type='alarm', subtype='zone'),
    VideoInterComAlarmType.TAMPERING_ALARM: DeviceTriggerMetadata(name='tampering_alarm', type='alarm', subtype='tampering'),
    VideoInterComAlarmType.HIJACKING_ALARM: DeviceTriggerMetadata(name='hijacking_alarm', type='alarm', subtype='hijacking'),
    VideoInterComAlarmType.MULTIPLE_PASSWORD_UNLOCK_FAILURE_ALARM: DeviceTriggerMetadata(name='multiple_passwords_unlock_failure', type='alarm', subtype='password unlock failures'),
    VideoInterComAlarmType.SOS: DeviceTriggerMetadata(name='sos', type='SOS', subtype=''),
    VideoInterComAlarmType.INTERCOM: DeviceTriggerMetadata(name='intercom', type='Intercom', subtype=''),
    VideoInterComAlarmType.SMART_LOCK_FINGERPRINT_ALARM: DeviceTriggerMetadata(name='smart_lock_fingerprint_alarm', type='smart lock alarm', subtype='fingerprint'),
    VideoInterComAlarmType.SMART_LOCK_PASSWORD_ALARM: DeviceTriggerMetadata(name='smart_lock_password_alarm', type='smart lock alarm', subtype='password'),
    VideoInterComAlarmType.SMART_LOCK_DOOR_PRYING_ALARM: DeviceTriggerMetadata(name='smart_lock_door_prying_alarm', type='smart lock alarm', subtype='door prying'),
    VideoInterComAlarmType.SMART_LOCK_DOOR_LOCK_ALARM: DeviceTriggerMetadata(name='smart_lock_door_lock_alarm', type='smart lock alarm', subtype='door lock'),
    VideoInterComAlarmType.SMART_LOCK_LOW_BATTERY_ALARM: DeviceTriggerMetadata(name='smart_lock_low_battery_alarm', type='smart lock alarm', subtype='low battery'),
    VideoInterComAlarmType.BLACKLIST_ALARM: DeviceTriggerMetadata(name='smart_lock_blacklist_alarm', type='alarm', subtype='blacklist'),
    VideoInterComAlarmType.SMART_LOCK_DISCONNECTED: DeviceTriggerMetadata(name='smart_lock_disconnected', type='smart lock disconnected', subtype=''),
    VideoInterComAlarmType.ACCESS_CONTROL_TAMPERING_ALARM: DeviceTriggerMetadata(name='access_control_tampering_alarm', type='alarm', subtype='access control tampering'),
}
"""Define the attributes of each DeviceTrigger entity, indexing them by the enum VideoInterComAlarmType"""


class MQTTHandler(EventHandler):
    name = 'MQTT'
    _sensors: dict[Doorbell, dict[str, Discoverable[Any]]] = {}
    """Keep references to the Discoverable entities created for each doorbell, indexed by their name"""

    def __init__(self, config: AppConfig.MQTT, doorbells: Registry) -> None:
        super().__init__()
        logger.info("Setting up event handler: {}", self.name)
        
        # Save the MQTT settings as an attribute
        self._mqtt_settings = Settings.MQTT(
            host=config.host,
            username=config.username,
            password=config.password
        )
        # Create the sensors for each doorbell:
        for doorbell in doorbells.values():
            # Consider only outdoor units
            if doorbell._type is DeviceType.INDOOR:
                continue

            logger.debug("Setting up entities for {}", doorbell._config.name)
            # Create an empty dict to hold the sensors
            self._sensors[doorbell] = {}
            doorbell_name = doorbell._config.name
            # Get the device information using ISAPI
            device = extract_device_info(doorbell)

            # Remove spaces and - from doorbell name
            sanitized_doorbell_name = sanitize_doorbell_name(doorbell_name)

            ##################
            # Call state
            call_sensor_info = SensorInfo(
                name="Call state",
                unique_id=f"{device.identifiers}-call_state",
                device=device,
                object_id=f"{sanitized_doorbell_name}_call_state",
                icon="mdi:bell")

            settings = Settings(mqtt=self._mqtt_settings, entity=call_sensor_info, manual_availability=True)
            call_sensor = Sensor(settings)
            call_sensor.set_state("idle")
            call_sensor.set_availability(True)
            self._sensors[doorbell]['call'] = call_sensor
            ##################
            # Doors
            # Create switches for output relays used to open doors
            num_doors = doorbell.get_num_outputs()
            logger.debug("Configuring {} door switches", num_doors)
            for door_id in range(num_doors):
                door_switch_info = SwitchInfo(
                    name=f"Door {door_id+1} relay",
                    unique_id=f"{device.identifiers}-door_relay_{door_id}",
                    device=device,
                    object_id=f"{sanitized_doorbell_name}_door_relay_{door_id}")
                settings = Settings(mqtt=self._mqtt_settings, entity=door_switch_info, manual_availability=True)
                door_switch = Switch(settings, self.door_switch_callback, (doorbell, door_id))
                door_switch.off()
                door_switch.set_availability(True)
                self._sensors[doorbell][f'door_{door_id}'] = door_switch

    def door_switch_callback(self, client, user_data: tuple[Doorbell, int], message: MQTTMessage):
        doorbell, door_id = user_data
        command = message.payload.decode("utf-8")
        logger.debug("Received command: {}, door_id: {}, doorbell: {}", command, door_id, doorbell._config.name)
        match command:
            case "ON":
                doorbell.unlock_door(door_id)

    @override
    async def motion_detection(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARMINFO_V30,
            buffer_length,
            user_pointer: c_void_p):
        metadata = DeviceTriggerMetadata(name="motion_detection", type="Motion detected", subtype="")
        self.handle_device_trigger(doorbell, metadata)

    @override
    async def isapi_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARM_ISAPI_INFO,
            buffer_length,
            user_pointer: c_void_p):
        logger.debug("Isapi alarm from {}", doorbell._config.name)

    @override
    async def video_intercom_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_VIDEO_INTERCOM_EVENT,
            buffer_length,
            user_pointer: c_void_p):
        if alarm_info.byEventType == VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG:
            door_id = alarm_info.uEventInfo.struUnlockRecord.wLockID
            control_source = alarm_info.uEventInfo.struUnlockRecord.controlSource()
            door_sensor = cast(Switch, self._sensors[doorbell][f'door_{door_id}'])
            logger.info("Door {} unlocked by {}, updating sensor {}",
                        door_id+1,
                        control_source,
                        door_sensor._entity.name)
            attributes = {
                'control source': control_source,
            }
            door_sensor.on()
            door_sensor.set_attributes(attributes)
            # Wait some seconds, then turn off the switch entity (since the relay is momentary)
            await asyncio.sleep(2)
            door_sensor.off()
        else:
            logger.warning("Unhandled eventType: {}", alarm_info.byEventType)

    @override
    async def video_intercom_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_VIDEO_INTERCOM_ALARM,
            buffer_length,
            user_pointer: c_void_p):
        call_sensor = cast(Sensor, self._sensors[doorbell]['call'])

        # Extract the type of alarm as a Python enum
        try:
            alarm_type = VideoInterComAlarmType(alarm_info.byAlarmType)
        except ValueError:
            logger.warning("Received unknown alarm type: {}", alarm_info.byAlarmType)
            return
        
        match alarm_type:
            case VideoInterComAlarmType.DOORBELL_RINGING:
                logger.info("Doorbell ringing, updating sensor {}", call_sensor)
                call_sensor.set_state('ringing')
            case VideoInterComAlarmType.DISMISS_INCOMING_CALL:
                logger.info("Call dismissed, updating sensor {}", call_sensor)
                call_sensor.set_state('dismissed')
                # Put sensor back to idle
                call_sensor.set_state('idle')
            case VideoInterComAlarmType.DOOR_NOT_OPEN | VideoInterComAlarmType.DOOR_NOT_CLOSED:
                # Get information about the door that caused this alarm
                door_id = alarm_info.wLockID
                logger.info("Alarm {} detected on door {}", alarm_info.uAlarmInfo, door_id)
                
                # Create the key to extract the entity from the `sensors` dict, depending on the alarm type
                # use `subtype` to display doors starting from index 1 in the UI
                if alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN:
                    trigger = DeviceTriggerMetadata(name=f"door_not_open_{door_id}", type="not open", subtype=f"Door {door_id+1}")
                else:
                    trigger = DeviceTriggerMetadata(name=f"door_not_closed_{door_id}", type="not closed", subtype=f"Door {door_id+1}")

                self.handle_device_trigger(doorbell, trigger)
            case _:
                """Generic alarm: create the device trigger entity according to the information inside the DEVICE_TRIGGERS_DEFINITIONS dict"""
                
                logger.info("Video intercom alarm {} detected on {}", alarm_type.name, doorbell._config.name)
                self.handle_device_trigger(doorbell, DEVICE_TRIGGERS_DEFINITIONS[alarm_type])

    @override
    async def unhandled_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info_pointer,
            buffer_length,
            user_pointer: c_void_p):
        logger.warning("Unknown event from {}", doorbell._config.name)

    def handle_device_trigger(self, doorbell: Doorbell, trigger: DeviceTriggerMetadata):
        """
        Generate a device trigger event.
        Create the device trigger entity if it doesn't exist, and save it as part of the `sensors` dict
        """
        # Get the device trigger from the `sensors` dict, if it exists
        device_trigger = self._sensors[doorbell].get(trigger['name'])
        # If it doesn't exist, create it
        if not device_trigger:
            device_info = extract_device_info(doorbell)

            # This is the first time we encounter this alarm, first create the Python entity
            device_trigger_info = DeviceTriggerInfo(name=trigger['name'], 
                                                    device=device_info,
                                                    type=trigger['type'], 
                                                    subtype=trigger["subtype"],
                                                    unique_id=f"{device_info.identifiers}-{trigger['name']}")
            settings = Settings(mqtt=self._mqtt_settings, entity=device_trigger_info)
            device_trigger = DeviceTrigger(settings)
            # Save the entity in the dict for future reference
            self._sensors[doorbell][trigger["name"]] = device_trigger

        # Cast to know type DeviceTrigger
        device_trigger = cast(DeviceTrigger, device_trigger)
        # Trigger the event
        logger.debug("Invoking device trigger {}", trigger)
        device_trigger.trigger()
