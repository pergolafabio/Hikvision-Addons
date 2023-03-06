import asyncio
from ctypes import c_void_p
import re
from typing import Any, TypedDict
from typing_extensions import override
from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry
from event import EventHandler
from sdk.hcnetsdk import (
    NET_DVR_ALARMER,
    NET_DVR_ALARMINFO_V30,
    NET_DVR_VIDEO_INTERCOM_ALARM,
    NET_DVR_VIDEO_INTERCOM_EVENT,
    NET_DVR_ALARM_ISAPI_INFO,
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL,
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN,
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED,
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING,
    VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM,
    VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT,
    VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG)
from loguru import logger
import requests


def sanitize_doorbell_name(doorbell_name: str) -> str:
    """Given a doorbell name, lowercase it and substitute whitespaces and `-` with `_`"""
    return re.sub(r"\s|-", "_", doorbell_name.lower())


class Sensor(TypedDict):
    name: str
    type: str
    attributes: dict[str, Any]


class HomeAssistantAPI(EventHandler):
    name = "HomeAssistantAPI"
    _sensors: dict[Doorbell, dict[str, Sensor]] = {}

    def __init__(self, config: AppConfig.HomeAssistant, doorbells: Registry) -> None:
        super().__init__()
        logger.info("Setting up event handler: Home Assistant API")

        self._config = config
        self._doorbells = doorbells

        # For each outdoor doorbell, initialize the sensors inside HA
        for doorbell in doorbells.values():
            # Skip if we have an indoor unit, since it does not support all the events for now
            if doorbell._type == DeviceType.INDOOR:
                continue
            # Create dict to contain the sensors of each doorbell
            self._sensors[doorbell] = {}
            sensors = self._sensors[doorbell]
            sensors['door'] = Sensor(
                name="door",
                type="binary_sensor",
                attributes={"device_class": "door"}
            )
            sensors['callstatus'] = Sensor(
                name="callstatus",
                type="binary_sensor",
                attributes={"device_class": "sound"}
            )
            sensors['motion'] = Sensor(
                name="motion",
                type="binary_sensor",
                attributes={"device_class": "motion"}
            )
            sensors['tamper'] = Sensor(
                name='tamper',
                type="binary_sensor",
                attributes={"device_class": "tamper"}
            )
            sensors['dismiss'] = Sensor(
                name='dismiss',
                type="binary_sensor",
                attributes={}
            )
            sensors['alarm'] = Sensor(
                name='alarm',
                type="binary_sensor",
                attributes={"device_class": "door"}
            )
            for name, sensor in sensors.items():
                doorbell_name = doorbell._config.name
                # Add friendly name attribute to existing attributes dict containing the doorbell name + sensor name
                sensor['attributes'] = sensor['attributes'] | {'friendly_name': f"{doorbell_name} {name}"}
                # Create the sensor in HA starting with `off` value
                self.update_sensor(doorbell_name, sensor, "off")

    def update_sensor(self, doorbell_name: str, sensor: Sensor, state: str):
        """ Update the sensor by invoking the Home Assistant HTTP API
        """
        HTTP_HEADERS = {
            'Authorization': f'Bearer {self._config.token}'
        }

        data = {'state': state, 'attributes': sensor['attributes']}
        device_name = sanitize_doorbell_name(doorbell_name)
        try:
            response = requests.post(f"{self._config.url}/api/states/{sensor['type']}.{device_name}_{sensor['name']}", headers=HTTP_HEADERS, json=data)
            # Check that the server returned a successful HTTP response code
            response.raise_for_status()
            logger.debug("Response {} {}", response.text, response.json())
        except:
            logger.exception("Cannot update sensor")

    @override
    async def motion_detection(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARMINFO_V30,
            buffer_length,
            user_pointer: c_void_p):
        logger.info("Motion detected from {}, updating sensor {}", doorbell._config.name, self._sensors[doorbell]['motion'])
        self.update_sensor(doorbell._config.name, self._sensors[doorbell]['motion'], 'on')
        await asyncio.sleep(5)
        self.update_sensor(doorbell._config.name, self._sensors[doorbell]['motion'], 'off')

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
            # Convert the controlSource to a string, removing suffix `0`s
            control_source = alarm_info.uEventInfo.struUnlockRecord.controlSource()
            logger.info("Door {} unlocked by {}, updating sensor {}",
                        alarm_info.uEventInfo.struUnlockRecord.wLockID,
                        control_source,
                        self._sensors[doorbell]['door'])
            additional_attributes = {
                # TODO: better rename to `control source`, similar to the original field?
                'Unlock': control_source,
                'DoorID': alarm_info.uEventInfo.struUnlockRecord.wLockID
            }
            # Add additional attributes to the sensor
            original_attributes = self._sensors[doorbell]['door']['attributes']
            self._sensors[doorbell]['door']['attributes'] = original_attributes | additional_attributes
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['door'], 'on')
            await asyncio.sleep(5)
            # Revert back to original attributes
            self._sensors[doorbell]['door']['attributes'] = original_attributes
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['door'], 'off')

        elif alarm_info.byEventType == VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT:
            logger.info("Illegal card swiping")
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
        if alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING:
            logger.info("Doorbell ringing, updating sensor {}", self._sensors[doorbell]['callstatus'])
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['callstatus'], 'on')
            await asyncio.sleep(5)
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['callstatus'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL:
            logger.info("Call dismissed, updating sensor {}", self._sensors[doorbell]['dismiss'])
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['dismiss'], 'on')
            await asyncio.sleep(5)
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['dismiss'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM:
            logger.info("Tampering alarm, updating sensor {}", self._sensors[doorbell]['tamper'])
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['tamper'], 'on')
            await asyncio.sleep(5)
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['tamper'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN or VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED:
            logger.info("Alarm {} detected on lock {}, updating sensor {}",
                        alarm_info.uAlarmInfo,
                        alarm_info.wLockID,
                        self._sensors[doorbell]['alarm'])
            additional_attributes = {
                'AlarmInfo': alarm_info.uAlarmInfo,
                'AlarmType': alarm_info.byAlarmType,
                'LockID': alarm_info.wLockID
            }
            # Add additional attributes to the sensor
            original_attributes = self._sensors[doorbell]['alarm']['attributes']
            self._sensors[doorbell]['alarm']['attributes'] = original_attributes | additional_attributes
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['alarm'], 'on')
            await asyncio.sleep(6)
            # Revert back to original attributes
            self._sensors[doorbell]['alarm']['attributes'] = original_attributes
            self.update_sensor(doorbell._config.name, self._sensors[doorbell]['alarm'], 'off')
        else:
            logger.warning("Unhandled alarmType: {}", alarm_info.byAlarmType)
    
    @override
    async def isapi_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARM_ISAPI_INFO,
            buffer_length,
            user_pointer: c_void_p):
        logger.info("Isapi alarm detected from {}, file saved in: {}",
                    doorbell._config.name,
                    alarm_info.szFilename)

    @override
    async def unhandled_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info_pointer,
            buffer_length,
            user_pointer: c_void_p):
        # Do nothing if we receive an unknown event
        pass
