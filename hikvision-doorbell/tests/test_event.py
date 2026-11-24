import asyncio
from ctypes import POINTER, cast, create_string_buffer
from unittest.mock import Mock
import pytest
from doorbell import Registry
from event import EventManager, event_picture
from sdk.hcnetsdk import BYTE, NET_DVR_VIDEO_INTERCOM_EVENT, VideoInterComEventType


def _event(event_type: VideoInterComEventType, record_name: str, data: bytes):
    event = NET_DVR_VIDEO_INTERCOM_EVENT()
    event.byEventType = event_type
    record = getattr(event.uEventInfo, record_name)
    buffer = create_string_buffer(data, len(data))
    record.pImage = cast(buffer, POINTER(BYTE))
    record.dwPicDataLen = len(data)
    return event, buffer


@pytest.mark.parametrize("event_type, record_name", [
    (VideoInterComEventType.UNLOCK_LOG, 'struUnlockRecord'),
    (VideoInterComEventType.AUTHENTICATION_LOG, 'struAuthInfo'),
])
def test_picture_is_copied(event_type, record_name):
    event, buffer = _event(event_type, record_name, b'\xff\xd8\xff\xe0jpeg')
    picture = event_picture(event)
    buffer[0] = b'\x00'
    assert picture == b'\xff\xd8\xff\xe0jpeg'


def test_no_picture():
    event = NET_DVR_VIDEO_INTERCOM_EVENT()
    event.byEventType = VideoInterComEventType.UNLOCK_LOG
    assert event_picture(event) is None


def test_length_without_pointer():
    event = NET_DVR_VIDEO_INTERCOM_EVENT()
    event.byEventType = VideoInterComEventType.UNLOCK_LOG
    event.uEventInfo.struUnlockRecord.dwPicDataLen = 100
    assert event_picture(event) is None


def test_other_event_type():
    event, _ = _event(VideoInterComEventType.MAGNETIC_DOOR_STATUS, 'struUnlockRecord', b'\xff\xd8')
    assert event_picture(event) is None


@pytest.mark.parametrize(("exception_type", "expected_state"), [
    (0x8006, "offline"),
    (0x8016, "online"),
])
def test_sdk_connection_exceptions_update_online_sensor(exception_type, expected_state):
    doorbell = Mock()
    doorbell.user_id = 7
    doorbell._config.name = "Test doorbell"
    sensor = Mock()
    handler = Mock()
    handler.name = "MQTT"
    handler._sensors = {doorbell: {"online": sensor}}
    registry = Registry()
    registry[0] = doorbell

    async def process_exception():
        event_manager = EventManager(Mock(), registry)
        event_manager._handlers = {handler}
        await event_manager._process_exception(exception_type, 7)

    asyncio.run(process_exception())

    sensor.set_state.assert_called_once_with(expected_state)


def test_start_registers_sdk_exception_callback():
    sdk = Mock()
    sdk.NET_DVR_SetDVRMessageCallBack_V50.return_value = True
    sdk.NET_DVR_SetExceptionCallBack_V30.return_value = True

    async def start_event_manager():
        EventManager(sdk, Registry(), enable_exception_callback=True).start()

    asyncio.run(start_event_manager())

    sdk.NET_DVR_SetExceptionCallBack_V30.assert_called_once()


def test_start_skips_sdk_exception_callback_by_default():
    sdk = Mock()
    sdk.NET_DVR_SetDVRMessageCallBack_V50.return_value = True

    async def start_event_manager():
        EventManager(sdk, Registry()).start()

    asyncio.run(start_event_manager())

    sdk.NET_DVR_SetExceptionCallBack_V30.assert_not_called()
