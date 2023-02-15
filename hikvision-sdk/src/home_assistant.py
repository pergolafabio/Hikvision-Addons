import asyncio
from ctypes import c_void_p
from config import AppConfig
from event import EventHandler
from sdk.hcnetsdk import NET_DVR_ALARMER, NET_DVR_ALARMINFO_V30, NET_DVR_VIDEO_INTERCOM_ALARM, NET_DVR_VIDEO_INTERCOM_EVENT, VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING, VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM, VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT, VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG
from loguru import logger
import requests


class HomeAssistantAPI(EventHandler):
    name = "HomeAssistantAPI"
    _sensors = {}

    def __init__(self, sensors: AppConfig.Sensors, config: AppConfig.HomeAssistant) -> None:
        super().__init__()
        logger.info("Setting up event handler: Home Assistant API")

        self._sensors['door'] = "sensor." + sensors.door
        self._sensors['callstatus'] = "sensor." + sensors.callstatus
        self._sensors['motion'] = "sensor." + sensors.motion
        self._sensors['tamper'] = "sensor." + sensors.tamper
        self._sensors['dismiss'] = "sensor." + sensors.dismiss

        self._config = config

    def update_sensor(self, sensor_name: str, state: str, attr: dict = {}):
        """ Update the sensor by invoking the Home Assistant HTTP API
        """
        HTTP_HEADERS = {
            'Authorization': f'Bearer {self._config.token}'
        }

        data = {'state': state, 'attributes': attr}
        try:
            response = requests.post(f"{self._config.url}/api/states/{sensor_name}", headers=HTTP_HEADERS, json=data)
            # Check that the server returned a successful HTTP response code
            response.raise_for_status()
            logger.debug("Response {} {}", response.text, response.json())
        except:
            logger.exception("Cannot update sensor")

    async def motion_detection(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_ALARMINFO_V30, buffer_length, user_pointer: c_void_p):
        logger.info("Motion detected, updating sensor {}", self._sensors['motion'])
        self.update_sensor(self._sensors['motion'], 'on')
        await asyncio.sleep(1)
        self.update_sensor(self._sensors['motion'], 'off')

    async def video_intercom_event(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_VIDEO_INTERCOM_EVENT, buffer_length, user_pointer: c_void_p):
        if alarm_info.byEventType == VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG:
            logger.info("Door {} unlocked by {}, updating sensor {}",
                        alarm_info.uEventInfo.struUnlockRecord.wLockID,
                        list(alarm_info.uEventInfo.struUnlockRecord.byControlSrc),
                        self._sensors['door'])
            attributes = {
                'Unlock': list(alarm_info.uEventInfo.struUnlockRecord.byControlSrc),
                'DoorID': alarm_info.uEventInfo.struUnlockRecord.wLockID
            }
            self.update_sensor(self._sensors['door'], 'on', attributes)
            await asyncio.sleep(1)
            self.update_sensor(self._sensors['door'], 'off', attributes)

        elif alarm_info.byEventType == VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT:
            logger.info("Illegal card swiping")
        else:
            logger.warning("Unhandled eventType: {}", alarm_info.byEventType)

    async def video_intercom_alarm(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_VIDEO_INTERCOM_ALARM, buffer_length, user_pointer: c_void_p):
        if alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING:
            logger.info("Doorbell ringing, updating sensor {}", self._sensors['callstatus'])
            self.update_sensor(self._sensors['callstatus'], 'on')
            await asyncio.sleep(1)
            self.update_sensor(self._sensors['callstatus'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL:
            logger.info("Call dismissed, updating sensor {}", self._sensors['dismiss'])
            self.update_sensor(self._sensors['dismiss'], 'on')
            await asyncio.sleep(1)
            self.update_sensor(self._sensors['dismiss'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM:
            logger.info("Tampering alarm, updating sensor {}", self._sensors['tamper'])
            self.update_sensor(self._sensors['tamper'], 'on')
            await asyncio.sleep(1)
            self.update_sensor(self._sensors['tamper'], 'off')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED:
            logger.info("Door not closed alarm")
        else:
            logger.warning("Unhandled alarmType: {}", alarm_info.byAlarmType)

    async def unhandled_event(self, command: int, device: NET_DVR_ALARMER, alarm_info_pointer, buffer_length, user_pointer: c_void_p):
        raise NotImplementedError
