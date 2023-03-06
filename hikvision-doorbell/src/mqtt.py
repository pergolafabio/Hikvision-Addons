import asyncio
from ctypes import c_void_p
from typing import Any, Optional, cast
from config import AppConfig

from doorbell import DeviceType, Doorbell, Registry
from event import EventHandler
from paho.mqtt.client import MQTTMessage
from ha_mqtt_discoverable import Settings, DeviceInfo, Discoverable
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo, SensorInfo, Sensor, SwitchInfo, Switch
from loguru import logger
from home_assistant import sanitize_doorbell_name
from sdk.hcnetsdk import (NET_DVR_ALARMER, NET_DVR_ALARMINFO_V30,
                          NET_DVR_VIDEO_INTERCOM_ALARM,
                          NET_DVR_VIDEO_INTERCOM_EVENT, VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING, VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG)
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


class MQTTHandler(EventHandler):
    name = 'MQTT'
    _sensors: dict[Doorbell, dict[str, Discoverable[Any]]] = {}

    def __init__(self, config: AppConfig.MQTT, doorbells: Registry) -> None:
        super().__init__()
        logger.info("Setting up event handler: {}", self.name)

        mqtt_settings = Settings.MQTT(
            host=config.host,
            username=config.username,
            password=config.password
        )
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
            # Motion sensor
            motion_sensor_info = BinarySensorInfo(
                name="Motion",
                unique_id=f"{sanitized_doorbell_name}_motion",
                device_class="motion",
                device=device,
                object_id=f"{sanitized_doorbell_name}_motion",
                off_delay=1)

            settings = Settings(mqtt=mqtt_settings, entity=motion_sensor_info, manual_availability=True)
            motion_sensor = BinarySensor(settings)
            motion_sensor.off()
            motion_sensor.set_availability(True)

            self._sensors[doorbell]['motion'] = motion_sensor
            ##################
            # Call state
            call_sensor_info = SensorInfo(
                name="Call state",
                unique_id=f"{sanitized_doorbell_name}_call_state",
                device=device,
                object_id=f"{sanitized_doorbell_name}_call_state",
                icon="mdi:bell")

            settings = Settings(mqtt=mqtt_settings, entity=call_sensor_info, manual_availability=True)
            call_sensor = Sensor(settings)
            call_sensor.set_state("idle")
            call_sensor.set_availability(True)
            self._sensors[doorbell]['call'] = call_sensor
            ##################
            # Create switch for output relays used to open doors
            # Range function stops before the second parameter, so we add + 1 to include it
            num_doors = doorbell.get_num_outputs()
            logger.debug("Configuring {} door switches", num_doors)
            for door_id in range(num_doors):
                door_switch_info = SwitchInfo(
                    name=f"Door {door_id+1} relay",
                    unique_id=f"{sanitized_doorbell_name}_door_relay_{door_id}",
                    device=device,
                    object_id=f"{sanitized_doorbell_name}_door_relay_{door_id}")
                settings = Settings(mqtt=mqtt_settings, entity=door_switch_info, manual_availability=True)
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
        motion_sensor = cast(BinarySensor, self._sensors[doorbell]['motion'])
        logger.debug("Updating sensor {}", motion_sensor._entity.name)
        motion_sensor.on()

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
            control_source = "".join([str(number) for number in alarm_info.uEventInfo.struUnlockRecord.byControlSrc[:]])
            door_sensor = cast(Switch, self._sensors[doorbell][f'door_{door_id}'])
            logger.info("Door {} unlocked by {}, updating sensor {}",
                        door_id+1,
                        control_source,
                        door_sensor._entity.name)
            # additional_attributes = {
            #     'Unlock': list(alarm_info.uEventInfo.struUnlockRecord.byControlSrc),
            # }
            door_sensor.on()
            # Wait some seconds, then turn off switch (the relay is momentary)
            await asyncio.sleep(2)
            door_sensor.off()

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

        if alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING:
            logger.info("Doorbell ringing, updating sensor {}", call_sensor)
            call_sensor.set_state('ringing')
        elif alarm_info.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL:
            logger.info("Call dismissed, updating sensor {}", call_sensor)
            call_sensor.set_state('dismissed')
            # Put sensor back to idle
            call_sensor.set_state('idle')

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
