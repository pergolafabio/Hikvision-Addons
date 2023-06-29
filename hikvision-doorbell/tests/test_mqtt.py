import asyncio
from ctypes import c_void_p
import pytest
from pytest_mock import MockerFixture
from config import AppConfig
from doorbell import DeviceType, Doorbell, Registry
from mqtt import DEVICE_TRIGGERS_DEFINITIONS, MQTTHandler, extract_device_info
from ha_mqtt_discoverable import DeviceInfo
import xml.etree.ElementTree as ET

from sdk.hcnetsdk import VIDEO_INTERCOM_ALARM_ALARMTYPE_ZONE_ALARM, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN, VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM, VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG, VideoInterComAlarmType
from sdk.utils import SDKError


@pytest.fixture()
def mocked_doorbell(mocker: MockerFixture) -> Doorbell:
    # Create a fake doorbell and set the parameters read by the handler
    mocked_doorbell = mocker.patch('doorbell.Doorbell')
    mocked_doorbell._type = DeviceType.OUTDOOR
    mocked_doorbell._config.name = "Test doorbell"
    mocked_doorbell._device_info.serialNumber = lambda: "123"
    return mocked_doorbell


@pytest.fixture()
def handler(mocked_doorbell: Doorbell, mocker: MockerFixture) -> MQTTHandler:
    registry = Registry()

    registry[0] = mocked_doorbell

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


def test_init(mocked_doorbell, mocker: MockerFixture):
    registry = Registry()

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


def test_extract_device_info(mocker: MockerFixture):
    # Create a fake doorbell and set the parameters read by the handler
    attributes = {'_config.name': 'test', '_device_info.serialNumber.return_value': "123"}
    mocked_doorbell = mocker.patch('doorbell.Doorbell', **attributes)
    mocked_doorbell.get_device_info.return_value = ET.Element("")
    info = extract_device_info(mocked_doorbell)
    assert info is not None


def test_extract_device_info_with_exception(mocker: MockerFixture):
    # Define a subclass of SDKError that does nothing, to be raised during the test
    class MockSDKError(SDKError):
        def __init__(self):
            pass

    # Create a fake doorbell and set the parameters read by the handler
    attributes = {'_config.name': 'test', '_device_info.serialNumber.return_value': "123", "get_device_info.side_effect": MockSDKError}
    mocked_doorbell = mocker.patch('doorbell.Doorbell', **attributes)
    info = extract_device_info(mocked_doorbell)
    assert info is not None


def test_video_intercom_event(mocker: MockerFixture, mocked_doorbell: Doorbell, handler: MQTTHandler):
    alarmer = mocker.patch('sdk.hcnetsdk.NET_DVR_ALARMER')
    video_intercom_event = mocker.patch('sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_EVENT')
    video_intercom_event.byEventType = VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG
    video_intercom_event.uEventInfo.struUnlockRecord.wLockID = 0
    video_intercom_event.uEventInfo.struUnlockRecord.controlSource = lambda: "test_source"
    
    asyncio.run(handler.video_intercom_event(mocked_doorbell, 0, alarmer, video_intercom_event, 0, c_void_p(None)))


def test_video_intercom_event_non_existing_id(mocker: MockerFixture, mocked_doorbell: Doorbell, handler: MQTTHandler):
    """The returned lock ID from the SDK is not valid"""
    alarmer = mocker.patch('sdk.hcnetsdk.NET_DVR_ALARMER')
    video_intercom_event = mocker.patch('sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_EVENT')
    video_intercom_event.byEventType = VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG
    # Set to return a "strange" door ID
    video_intercom_event.uEventInfo.struUnlockRecord.wLockID = 24322
    
    asyncio.run(handler.video_intercom_event(mocked_doorbell, 0, alarmer, video_intercom_event, 0, c_void_p(None)))


class TestDeviceTrigger:

    def test_zone_alarm(self, mocked_doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = VIDEO_INTERCOM_ALARM_ALARMTYPE_ZONE_ALARM
        video_intercom_alarm.uAlarmInfo.struZoneAlarm.byZoneType = 1
        video_intercom_alarm.uAlarmInfo.struZoneAlarm.dwZonendex = 1
        
        asyncio.run(handler.video_intercom_alarm(mocked_doorbell, 0, None, video_intercom_alarm, 0, None))

        # Check that the entity is saved in the dict
        #assert handler._sensors[mocked_doorbell]["zone_alarm_0"] is not None
 
    def test_door_not_open(self, mocked_doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN
        video_intercom_alarm.wLockID = 0
        
        asyncio.run(handler.video_intercom_alarm(mocked_doorbell, 0, None, video_intercom_alarm, 0, None))

        # Check that the entity is saved in the dict
        assert handler._sensors[mocked_doorbell]["door_not_open_0"] is not None

    def test_door_not_closed(self, mocked_doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED
        video_intercom_alarm.wLockID = 0
        
        asyncio.run(handler.video_intercom_alarm(mocked_doorbell, 0, None, video_intercom_alarm, 0, None))

        # Check that the entity is saved in the dict
        assert handler._sensors[mocked_doorbell]["door_not_closed_0"] is not None

    @pytest.mark.parametrize(argnames="alarm_type", argvalues=list(VideoInterComAlarmType))
    def test_all_alarm_types(self, mocked_doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture, alarm_type: VideoInterComAlarmType):
        if alarm_type in (VideoInterComAlarmType.DOOR_NOT_OPEN, 
                          VideoInterComAlarmType.DOOR_NOT_CLOSED,
                          VideoInterComAlarmType.ZONE_ALARM,
                          VideoInterComAlarmType.DOORBELL_RINGING,
                          VideoInterComAlarmType.DISMISS_INCOMING_CALL
                          ):
            pytest.skip("Tested in another function")
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = alarm_type.value

        asyncio.run(handler.video_intercom_alarm(mocked_doorbell, 0, None, video_intercom_alarm, 0, None))

        entity_key_name = DEVICE_TRIGGERS_DEFINITIONS[alarm_type]['name']

        # Check that the entity is saved in the dict
        assert handler._sensors[mocked_doorbell][entity_key_name] is not None
    
    def test_motion_detection(self, mocked_doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        alarm_info = mocker.patch("sdk.hcnetsdk.NET_DVR_ALARMINFO_V30")

        asyncio.run(handler.motion_detection(mocked_doorbell, 0, None, alarm_info, 0, None))

        # Check that the entity is saved in the dict
        assert handler._sensors[mocked_doorbell]["motion_detection"] is not None

    def test_unknown_alarm_type(self, mocked_doorbell: Doorbell, handler: MQTTHandler, mocker: MockerFixture):
        video_intercom_alarm = mocker.patch("sdk.hcnetsdk.NET_DVR_VIDEO_INTERCOM_ALARM")
        video_intercom_alarm.byAlarmType = 999

        asyncio.run(handler.video_intercom_alarm(mocked_doorbell, 0, None, video_intercom_alarm, 0, None))
