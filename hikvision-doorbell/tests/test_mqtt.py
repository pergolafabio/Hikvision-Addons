import asyncio
import pytest
from pytest_mock import MockerFixture
from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry
from mqtt import DEVICE_TRIGGERS_DEFINITIONS, MQTTHandler
from ha_mqtt_discoverable import DeviceInfo

from sdk.hcnetsdk import VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN, VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM, VideoInterComAlarmType


def test_init(mocker: MockerFixture):
    registry = Registry()
    # Create a fake doorbell and set the parameters read by the handler
    mocked_doorbell = mocker.patch('doorbell.Doorbell')
    mocked_doorbell._type = DeviceType.OUTDOOR
    mocked_doorbell._config.name = "Test doorbell"
    mocked_doorbell._device_info.serialNumber = lambda: "123"

    registry[0] = mocked_doorbell
    
    # Mock call to get DeviceInfo
    extract_device_info = mocker.patch('mqtt.extract_device_info', autospec=True)
    dev_info = DeviceInfo(name="test", identifiers="id")
    extract_device_info.return_value = dev_info

    # Fake MQTT settings
    mqtt_config = AppConfig.MQTT(host="localhost")

    # Mock the sensors so no MQTT connection is made
    mocker.patch("mqtt.BinarySensor")
    mocker.patch("mqtt.Sensor")
    mocker.patch("mqtt.Switch")

    handler = MQTTHandler(mqtt_config, registry)
    assert handler is not None


class TestDeviceTrigger:

    @classmethod
    @pytest.fixture()
    def doorbell(cls, mocker: MockerFixture) -> Doorbell:
        # Create a fake doorbell and set the parameters read by the handler
        mocked_doorbell = mocker.patch('doorbell.Doorbell')
        mocked_doorbell._type = DeviceType.OUTDOOR
        mocked_doorbell._config.name = "Test doorbell"
        mocked_doorbell._device_info.serialNumber = lambda: "123"
        return mocked_doorbell
    
    @classmethod
    @pytest.fixture()
    def handler(cls, doorbell: Doorbell, mocker: MockerFixture) -> MQTTHandler:
        registry = Registry()

        registry[0] = doorbell

        # Mock call to get DeviceInfo
        extract_device_info = mocker.patch('mqtt.extract_device_info', autospec=True)
        dev_info = DeviceInfo(name="Outdoor unit", identifiers="id")
        extract_device_info.return_value = dev_info

        # Fake MQTT settings
        mqtt_config = AppConfig.MQTT(host="localhost")

        # Mock the sensors so no MQTT connection is made
        mocker.patch("mqtt.Sensor")
        mocker.patch("mqtt.Switch")
        mocker.patch("mqtt.DeviceTrigger")

        # Instantiate the handler
        handler = MQTTHandler(mqtt_config, registry)
        return handler

    def test_door_not_open(self, doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN
        video_intercom_alarm.wLockID = 0
        
        asyncio.run(handler.video_intercom_alarm(doorbell, 0, None, video_intercom_alarm, 0, None))

        # Check that the entity is saved in the dict
        assert handler._sensors[doorbell]["door_not_open_0"] is not None

    def test_door_not_closed(self, doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED
        video_intercom_alarm.wLockID = 0
        
        asyncio.run(handler.video_intercom_alarm(doorbell, 0, None, video_intercom_alarm, 0, None))

        # Check that the entity is saved in the dict
        assert handler._sensors[doorbell]["door_not_closed_0"] is not None

    @pytest.mark.parametrize(argnames="alarm_type", argvalues=list(VideoInterComAlarmType))
    def test_all_alarm_types(self, doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture, alarm_type: VideoInterComAlarmType):
        if alarm_type in (VideoInterComAlarmType.DOOR_NOT_OPEN, 
                          VideoInterComAlarmType.DOOR_NOT_CLOSED,
                          VideoInterComAlarmType.DOORBELL_RINGING,
                          VideoInterComAlarmType.DISMISS_INCOMING_CALL
                          ):
            pytest.skip("Tested in another function")
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = alarm_type.value

        asyncio.run(handler.video_intercom_alarm(doorbell, 0, None, video_intercom_alarm, 0, None))

        entity_key_name = DEVICE_TRIGGERS_DEFINITIONS[alarm_type]['name']

        # Check that the entity is saved in the dict
        assert handler._sensors[doorbell][entity_key_name] is not None
    
    def test_motion_detection(self, doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        alarm_info = mocker.patch("sdk.hcnetsdk.NET_DVR_ALARMINFO_V30")

        asyncio.run(handler.motion_detection(doorbell, 0, None, alarm_info, 0, None))

        # Check that the entity is saved in the dict
        assert handler._sensors[doorbell]["motion_detection"] is not None

    def test_unknown_alarm_type(self, doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = 999

        asyncio.run(handler.video_intercom_alarm(doorbell, 0, None, video_intercom_alarm, 0, None))
