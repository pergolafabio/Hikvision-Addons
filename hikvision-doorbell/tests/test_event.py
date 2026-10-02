from ctypes import POINTER, cast, create_string_buffer
import pytest
from event import event_picture
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
