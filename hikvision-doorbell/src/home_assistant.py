import asyncio
from ctypes import c_void_p
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
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL,
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED,
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING,
    VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM,
    VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT,
    VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG)
from loguru import logger
import requests


def sanitize_doorbell_name(doorbell_name: str) -> str:
    """Given a doorbell name, lowercase it and substitute spaces with underscore"""
    return doorbell_name.lower().replace(" ", "_")


class Sensor(TypedDict):
    name: str
    type: str
    attributes: dict[str, Any]


class HomeAssistantAPI(EventHandler):
    name = "HomeAssistantAPI"
    _sensors: dict[str, Sensor] = {}

    def __init__(self, config: AppConfig.HomeAssistant, doorbells: Registry) -> None:
        super().__init__()
        logger.info("Setting up event handler: Home Assistant API")

        self._config = config
        self._doorbells = doorbells

        self._sensors['door'] = Sensor(
            name="door",
            type="binary_sensor",
            attributes={"device_class": "door"}
        )
        self._sensors['callstatus'] = Sensor(
            name="callstatus",
            type="binary_sensor",
            attributes={"device_class": "sound"}
        )
        self._sensors['motion'] = Sensor(
            name="motion",
            type="binary_sensor",
            attributes={"device_class": "motion"}
        )
        self._sensors['tamper'] = Sensor(
            name='tamper',
            type="binary_sensor",
            attributes={"device_class": "tamper"}
        )
        self._sensors['dismiss'] = Sensor(
            name='dismiss',
            type="binary_sensor",
            attributes={}
        )

        # For each outdoor doorbell, initialize the sensors inside HA
        for doorbell in doorbells.values():
            if not doorbell._type == DeviceType.OUTDOOR:
                continue
            for name, sensor in self._sensors.items():
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
        logger.info("Motion detected from {}, updating sensor {}", doorbell._config.name, self._sensors['motion'])
        self.update_sensor(doorbell._config.name, self._sensors['motion'], 'on')
        await asyncio.sleep(1)
        self.update_sensor(doorbell._config.name, self._sensors['motion'], 'off')

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
            logger.info("Door {} unlocked by {}, updating sensor {}",
                        alarm_info.uEventInfo.struUnlockRecord.wLockID,
                        list(alarm_info.uEventInfo.struUnlockRecord.byControlSrc),
                        self._sensors['door'])
            additional_attributes = {
                'Unlock': list(alarm_info.uEventInfo.struUnlockRecord.byControlSrc),
                'DoorID': alarm_info.uEventInfo.struUnlockRecord.wLockID
            }
            # Add additional attributes to the sensor
            original_attributes = self._sensors['door']['attributes']
            self._sensors['door']['attributes'] = original_attributes | additional_attributes
            self.update_sensor(doorbell._config.name, self._sensors['door'], 'on')
            await asyncio.sleep(1)
            # Revert back to original attributes
            self._sensors['door']['attributes'] = original_attributes
            self.update_sensor(doorbell._config.name, self._sensors['door'], 'off')

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
            logger.info("Doorbell ringing, updating sensor {}", self._sensors['callstatus'])
            self.update_sensor(doorbell._config.name, self._sensors['callstatus'], 'on')
            await asyncio.sleep(1)
            self.update_sensor(doorbell._config.name, self._sensors['callstatus'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL:
            logger.info("Call dismissed, updating sensor {}", self._sensors['dismiss'])
            self.update_sensor(doorbell._config.name, self._sensors['dismiss'], 'on')
            await asyncio.sleep(1)
            self.update_sensor(doorbell._config.name, self._sensors['dismiss'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM:
            logger.info("Tampering alarm, updating sensor {}", self._sensors['tamper'])
            self.update_sensor(doorbell._config.name, self._sensors['tamper'], 'on')
            await asyncio.sleep(1)
            self.update_sensor(doorbell._config.name, self._sensors['tamper'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED:
            logger.info("Door not closed alarm")
        else:
            logger.warning("Unhandled alarmType: {}", alarm_info.byAlarmType)

    @override
    async def unhandled_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info_pointer,
            buffer_length,
            user_pointer: c_void_p):
        raise NotImplementedError
