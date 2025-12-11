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
                          NET_DVR_ACS_ALARM_INFO,
                          VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN,
                          VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG,
                          VideoInterComAlarmType,
                          VideoInterComEventType)
from sdk.acsalarminfo import (AcsAlarmInfoMajor, AcsAlarmInfoMajorAlarm, AcsAlarmInfoMajorException, AcsAlarmInfoMajorOperation, AcsAlarmInfoMajorEvent)
from typing_extensions import override
import xml.etree.ElementTree as ET
import json
import datetime

from sdk.utils import SDKError


def extract_device_info(doorbell: Doorbell) -> DeviceInfo:
    """Build and instance of DeviceInfo from the ISAPI /deviceinfo endpoint, if available, otherwise skip populating additional fields"""
    try:
        device_info = doorbell.get_device_info()
    except SDKError:
        # Cannot get device info using ISAPI, fallback to empty `device_info` XML element
        device_info = ET.Element("")

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
    """
    Helper dict class defining the information of a device trigger.
    Used when building the DeviceTrigger entity
    """
    name: str
    """Name of this device trigger"""
    type: str
    """Displayed in the HA UI"""
    subtype: str
    """Displayed in the HA UI"""
    payload: dict[str, str]
    """Optional payload sent in the trigger"""    

DEVICE_TRIGGERS_DEFINITIONS: dict[VideoInterComAlarmType, DeviceTriggerMetadata] = {
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
    VideoInterComAlarmType.ACCESS_CONTROL_TAMPERING_ALARM: DeviceTriggerMetadata(name='access_control_tampering_alarm', type='alarm', subtype='access control tampering alarm'),
    VideoInterComAlarmType.SOS_CANCELLED: DeviceTriggerMetadata(name='sos_cancelled', type='alarm', subtype='sos cancelled'),
    VideoInterComAlarmType.NO_MASK_ALARM: DeviceTriggerMetadata(name='no_mask_alarm', type='alarm', subtype='no mask alarm'),
    VideoInterComAlarmType.FIRE_INPUT_ALARM: DeviceTriggerMetadata(name='fire_input_alarm', type='alarm', subtype='fire input alarm'),
    VideoInterComAlarmType.FIRE_INPUT_RESTORED: DeviceTriggerMetadata(name='fire_input_restored', type='alarm', subtype='fire input restored'),
    VideoInterComAlarmType.TOILET_ALARM: DeviceTriggerMetadata(name='toilet_alarm', type='alarm', subtype='toilet alarm'),
    VideoInterComAlarmType.TOILET_ALARM_CANCELLED: DeviceTriggerMetadata(name='toilet_alarm_cancelled', type='alarm', subtype='toilet alarm cancelled'),
    VideoInterComAlarmType.DRESSING_REMINDER: DeviceTriggerMetadata(name='dressing_reminder', type='alarm', subtype='dressing reminder'),
    VideoInterComAlarmType.FACE_TEMPERATURE_ALARM: DeviceTriggerMetadata(name='face_temperature_alarm', type='alarm', subtype='face temperature alarm'),
    VideoInterComAlarmType.DRESSING_REMINDER_CANCELLED: DeviceTriggerMetadata(name='dressing_reminder_cancelled', type='force', subtype='dressing reminder cancelled'),
}
"""Define the attributes of each DeviceTrigger entity, indexing them by the enum VideoInterComAlarmType"""

DEVICE_TRIGGERS_DEFINITIONS_EVENT: dict[VideoInterComEventType, DeviceTriggerMetadata] = {
    VideoInterComEventType.AUTHENTICATION_LOG: DeviceTriggerMetadata(name='authentication_log', type='event', subtype='authentication log'),
    VideoInterComEventType.ANNOUNCEMENT_READING_RECEIPT: DeviceTriggerMetadata(name='announcement_reading_receipt', type='event', subtype='announcement reading receipt'),
    VideoInterComEventType.UPLOAD_PLATE_INFO: DeviceTriggerMetadata(name='upload_plate_info', type='event', subtype='upload plate info'),
    VideoInterComEventType.DOOR_STATION_ISSUED_CARD_LOG: DeviceTriggerMetadata(name='door_station_issued_card_log', type='event', subtype='door station issued card log'),
    VideoInterComEventType.MASK_DETECT_EVENT: DeviceTriggerMetadata(name='mask_detect_event', type='event', subtype='mask detect event'),
}
"""Define the attributes of each DeviceTrigger entity, indexing them by the enum VideoInterComEventType"""

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
            port=config.port,
            username=config.username,
            password=config.password
        )
        # Create the sensors for each doorbell:
        for doorbell in doorbells.values():

            logger.debug("Setting up entities for {}", doorbell._config.name)
            # Create an empty dict to hold the sensors
            self._sensors[doorbell] = {}
            doorbell_name = doorbell._config.name
            # Get the device information using ISAPI
            device = extract_device_info(doorbell)

            # Remove spaces and - from doorbell name
            sanitized_doorbell_name = sanitize_doorbell_name(doorbell_name)

            # No Callsensor for indoor
            if not doorbell._type is DeviceType.INDOOR:
                
                ##################
                # Call state
                call_sensor_info = SensorInfo(
                    name="Call state",
                    unique_id=f"{device.identifiers}-call_state",
                    device=device,
                    default_entity_id=f"{sanitized_doorbell_name}_call_state",
                    icon="mdi:bell")

                settings = Settings(mqtt=self._mqtt_settings, entity=call_sensor_info, manual_availability=True)
                call_sensor = Sensor(settings)
                call_sensor.set_state("idle")
                call_sensor.set_availability(True)
                self._sensors[doorbell]['call'] = call_sensor


                '''
                # If polling is defined, create a loop to update the call state periodically

                if not doorbell._config.call_state_poll is None:

                    call_state_poll_sec = doorbell._config.call_state_poll
                    
                    async def poll_call_sensor(d=doorbell, c=call_sensor):
                        while True:
                            try:
                                logger.info("Trying to get call status for doorbell: {} every {} sec", d._config.name, call_state_poll_sec)
                                url = "/ISAPI/VideoIntercom/callStatus?format=json"
                                requestBody = ""
                                try:
                                    response = d._call_isapi("GET", url, requestBody)
                                    logger.debug("Received call status with response: {} " , response)
                                    call_state = json.loads(response)["CallStatus"]["status"]
                                    # Error out if we don't find state
                                    if call_state is None:
                                        # Print a string representation of the response JSON
                                        raise RuntimeError(f'Unexpected JSON response: {response}')
                                    c.set_state(call_state)
                                    logger.info("Call sensor changed to {} for doorbell: {}", call_state, d._config.name)
                                except SDKError as err:
                                    logger.error("Error while getting call status with ISAPI: {}", err)
                                   
                            except RuntimeError:
                                # Ignore error to avoid crashing application
                                pass
                            await asyncio.sleep(call_state_poll_sec)
                            
                    loop = asyncio.get_event_loop()
                    new_task = loop.create_task(poll_call_sensor())
                    if not hasattr(self, '_call_sensor_tasks'):
                        self._call_sensor_tasks = {}
                
                    self._call_sensor_tasks[doorbell] = new_task
                '''
            ##################
            # Doors
            # Create switches for output relays used to open doors

            if not doorbell._type is DeviceType.INDOOR:
                num_doors = doorbell.get_num_outputs()
            else:
                num_doors = doorbell.get_num_outputs_indoor()
            logger.debug("Configuring {} door switches", num_doors)
            for door_id in range(num_doors):
                door_switch_info = SwitchInfo(
                    name=f"Door {door_id+1} relay",
                    unique_id=f"{device.identifiers}-door_relay_{door_id}",
                    device=device,
                    default_entity_id=f"{sanitized_doorbell_name}_door_relay_{door_id}")
                settings = Settings(mqtt=self._mqtt_settings, entity=door_switch_info, manual_availability=True)
                door_switch = Switch(settings, self.door_switch_callback, (doorbell, door_id))
                door_switch.off()
                door_switch.set_availability(True)
                self._sensors[doorbell][f'door_{door_id}'] = door_switch

            ##################
            # Output ports
            # Create com1 and com2 ports for indoor stations

            if doorbell._type is DeviceType.INDOOR:
                
                num_coms = doorbell.get_num_coms_indoor()
                logger.debug("Configuring {} door switches", num_coms)
                for com_id in range(num_coms):
                    com_switch_info = SwitchInfo(
                        name=f"Com {com_id+1} relay",
                        unique_id=f"{device.identifiers}-com_relay_{com_id}",
                        device=device,
                        default_entity_id=f"{sanitized_doorbell_name}_com_relay_{com_id}")
                    settings = Settings(mqtt=self._mqtt_settings, entity=com_switch_info, manual_availability=True, assume_state=False)
                    com_switch = Switch(settings, self.com_switch_callback, (doorbell, com_id))
                    com_switch.off()
                    com_switch.set_availability(True)
                    self._sensors[doorbell][f'com_{com_id}'] = com_switch

    def com_switch_callback(self, client, user_data: tuple[Doorbell, int], message: MQTTMessage):
        doorbell, com_id = user_data
        command = message.payload.decode("utf-8")
        logger.debug("Received command: {}, com_id: {}, doorbell: {}", command, com_id, doorbell._config.name)
        match command:
            case "ON":
                doorbell.unlock_com(com_id)
            case "OFF":
                doorbell.lock_com(com_id)

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
        now = datetime.datetime.now()
        attributes = {'motion_detected': now.strftime("%Y-%m-%d %H:%M:%S")}
        metadata = DeviceTriggerMetadata(name="motion_detection", type="Motion detected", subtype="motion_detection", payload=attributes)
        self.handle_device_trigger(doorbell, metadata)

    @override
    async def acs_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ACS_ALARM_INFO,
            buffer_length,
            user_pointer: c_void_p):
        
        # Extract the type of alarm as a Python enum
        try:
            major = alarm_info.dwMajor
            minor = alarm_info.dwMinor
            door_id = alarm_info.struAcsEventInfo.dwDoorNo
            employee_id = alarm_info.struAcsEventInfo.dwEmployeeNo
            logger.debug("Access control event occured, trying to find the event for Major: {} : Minor: {}", major, minor)
            major_alarm = AcsAlarmInfoMajor(major)
            match major:
                case AcsAlarmInfoMajor.MAJOR_ALARM.value:
                    minor_alarm = AcsAlarmInfoMajorAlarm(minor)
                case AcsAlarmInfoMajor.MAJOR_EXCEPTION.value:
                    minor_alarm = AcsAlarmInfoMajorException(minor)
                case AcsAlarmInfoMajor.MAJOR_OPERATION.value:
                    minor_alarm = AcsAlarmInfoMajorOperation(minor)
                case AcsAlarmInfoMajor.MAJOR_EVENT.value:
                    minor_alarm = AcsAlarmInfoMajorEvent(minor)
            logger.info("Access control event: {} found with event: {}", major_alarm.name.lower(), minor_alarm.name.lower())
            match minor_alarm.name:
                case "MINOR_FACE_VERIFY_PASS":
                    logger.debug("Minor control event: {} found on door {} with employee id: {}", minor_alarm.name.lower(), door_id, employee_id)
                    attributes = {
                        'employee_id': employee_id,
                    }
                    trigger = DeviceTriggerMetadata(name=f"{major_alarm.name.lower()} {minor_alarm.name.lower()}", type=f"", subtype=f"{major_alarm.name.lower()} {minor_alarm.name.lower()}", payload=attributes)
                    self.handle_device_trigger(doorbell, trigger)
                case "MINOR_FINGERPRINT_COMPARE_PASS":
                    logger.debug("Minor control event: {} found on door {} with employee id: {}", minor_alarm.name.lower(), door_id, employee_id)
                    attributes = {
                        'employee_id': employee_id,
                    }
                    trigger = DeviceTriggerMetadata(name=f"{major_alarm.name.lower()} {minor_alarm.name.lower()}", type=f"", subtype=f"{major_alarm.name.lower()} {minor_alarm.name.lower()}", payload=attributes)
                    self.handle_device_trigger(doorbell, trigger)
                case _:
                    trigger = DeviceTriggerMetadata(name=f"{major_alarm.name.lower()} {minor_alarm.name.lower()}", type=f"", subtype=f"{major_alarm.name.lower()} {minor_alarm.name.lower()}")
                    self.handle_device_trigger(doorbell, trigger)
        except:
            logger.warning("Received unknown Access control event with Major: {} Minor: {}", major, minor)
            return

    @override
    async def isapi_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARM_ISAPI_INFO,
            buffer_length,
            user_pointer: c_void_p):
        alarmData = alarm_info.pAlarmData
        logger.debug("Isapi alarm from {} with Alarmdata: {} ", doorbell._config.name, alarmData)

    @override
    async def video_intercom_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_VIDEO_INTERCOM_EVENT,
            buffer_length,
            user_pointer: c_void_p):

        async def update_door_entities(door_id: str, control_source: str):
            """
            Helper function to update the sensor and device trigger of a given door
            """
            logger.info("Door {} unlocked by {} , updating sensor and device trigger", door_id+1, control_source)
            
            entity_id = f'door_{door_id}'
            door_sensor = cast(Switch, self._sensors[doorbell].get(entity_id))
            attributes = {
                'control_source': control_source,
            }
            door_sensor.set_attributes(attributes)
            door_sensor.on()
            trigger = DeviceTriggerMetadata(name=f"Door unlocked", type="door open", subtype=f"door {door_id}", payload=attributes)
            self.handle_device_trigger(doorbell, trigger)

            # Wait some seconds, then turn off the switch entity (since the door relay in the doorbell is momentary)
            await asyncio.sleep(2)
            door_sensor.off()
            
        # Extract the type of event as a Python enum
        try:
            event_type = VideoInterComEventType(alarm_info.byEventType)
        except ValueError:
            logger.warning("Received unknown Event type: {}", alarm_info.byEventType)
            return
        
        match event_type:
            case VideoInterComEventType.UNLOCK_LOG:
                door_id = alarm_info.uEventInfo.struUnlockRecord.wLockID
                control_source = alarm_info.uEventInfo.struUnlockRecord.controlSource()
                # card_number = alarm_info.uEventInfo.struAuthInfo.cardNo()
                # Name of the entity inside the dict array containing all the sensors
                entity_id = f'door_{door_id}'
                # Extract the sensor entity from the dict and cast to know type
                door_sensor = cast(Switch, self._sensors[doorbell].get(entity_id))
                # If the SDK returns a lock ID that is not starting from 0, 
                # we don't know what switch to update in HA -> trigger both of them
                # Make sure the switch is back in "OFF" position in case it was trigger by the switch
                if not door_sensor:
                    logger.warning("Received unknown lockID: {}", door_id)
                    # logger.debug("Changing switches back to OFF position")
                    num_doors = doorbell.get_num_outputs()
                    for door_id in range(num_doors):
                        await update_door_entities(door_id, control_source)
                    return
                await update_door_entities(door_id, control_source)

            case VideoInterComEventType.ILLEGAL_CARD_SWIPING_EVENT:
                control_source = alarm_info.uEventInfo.struUnlockRecord.controlSource()
                attributes = {
                    'control_source': control_source,
                }
                trigger = DeviceTriggerMetadata(name='illegal_card_swiping_event', type='event', subtype='illegal card_swiping event', payload=attributes)
                self.handle_device_trigger(doorbell, trigger)

            case VideoInterComEventType.MAGNETIC_DOOR_STATUS:
                door_id = alarm_info.uEventInfo.struUnlockRecord.wLockID
                logger.info("Magnetic door event detected on door {}", door_id + 1)
                attributes = {
                    'door_id': door_id + 1,
                }
                trigger = DeviceTriggerMetadata(name='magnetic door status', type='event', subtype='magnetic_door_status', payload=attributes)
                self.handle_device_trigger(doorbell, trigger)

            case _:
                """Generic event: create the device trigger entity according to the information inside the DEVICE_TRIGGERS_DEFINITIONS dict"""
                
                logger.info("Video intercom event {} detected on {}", event_type.name.lower(), doorbell._config.name)
                self.handle_device_trigger(doorbell, DEVICE_TRIGGERS_DEFINITIONS_EVENT[event_type])

    @override
    async def video_intercom_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_VIDEO_INTERCOM_ALARM,
            buffer_length,
            user_pointer: c_void_p):
        
        if not doorbell._type is DeviceType.INDOOR:
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
                logger.info("Updating doorbell sensor back to 'idle' after 60 seconds")
                await asyncio.sleep(60)
                call_sensor.set_state('idle')
            case VideoInterComAlarmType.DISMISS_INCOMING_CALL:
                logger.info("Call dismissed, updating sensor {}", call_sensor)
                call_sensor.set_state('dismissed')
                # Put sensor back to idle
                call_sensor.set_state('idle')
            case VideoInterComAlarmType.ZONE_ALARM:
                #zone_name = str(alarm_info.uAlarmInfo.struZoneAlarm.byZoneName,'UTF-8')
                zone_type_id = alarm_info.uAlarmInfo.struZoneAlarm.byZoneType
                zone_number = alarm_info.uAlarmInfo.struZoneAlarm.dwZonendex
                match zone_type_id:
                    case 0:
                        zone_type= "Panic button"
                    case 1:
                        zone_type= "Door magnetic"
                    case 2:
                        zone_type= "Smoke detector"
                    case 3:
                        zone_type= "Active infrared"
                    case 4:
                        zone_type= "Passive infrared"
                    case 11:
                        zone_type= "Gas detector"
                    case 21:
                        zone_type= "Doorbell"                                                                                                 
                    case _:
                        zone_type= f"Unknown type {zone_type_id}"
                
                logger.info("Zone alarm detected on doorbell {}, zone type: {}, zone number: {} ", doorbell._config.name, zone_type, (zone_number+1))
                trigger = DeviceTriggerMetadata(name=f"Zone {zone_number+1}", type="alarm", subtype=f"alarm_{zone_number+1}")
                self.handle_device_trigger(doorbell, trigger)
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
                
            case VideoInterComAlarmType.DOOR_OPEN_BY_EXTERNAL_FORCE:
                # Get information about the door that caused this alarm
                door_id = alarm_info.wLockID
                logger.info("External force detected on door {}", door_id + 1)
                attributes = {
                    'door_id': door_id + 1,
                }
                trigger = DeviceTriggerMetadata(name='door open by external force', type='event', subtype='door_open_by_external_force', payload=attributes)
                self.handle_device_trigger(doorbell, trigger)

            case _:
                """Generic alarm: create the device trigger entity according to the information inside the DEVICE_TRIGGERS_DEFINITIONS dict"""
                
                logger.info("Video intercom alarm {} detected on {}", alarm_type.name.lower(), doorbell._config.name)
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
        logger.info("Invoking device trigger automation{}", trigger)
        
        # Serialize the payload, if provided as part of the trigger
        json_payload = json.dumps(trigger['payload']) if trigger.get('payload') else None
        device_trigger.trigger(json_payload)