from ctypes import CFUNCTYPE, Structure, POINTER, c_char_p, c_ushort, c_ulong, c_long, c_bool, c_char, c_byte, c_void_p, c_short, Union, sizeof, c_uint
from enum import Enum, IntEnum
import re

BOOL = c_bool
WORD = c_ushort
DWORD = c_ulong if sizeof(c_ulong) == 4 else c_uint
LONG = c_long
BYTE = c_byte
SHORT = c_short
char = c_char

SERIALNO_LEN = 48
NAME_LEN = 32
MACADDR_LEN = 6
MAX_ANALOG_ALARM_OUT = 32
MAX_IP_ALARM_OUT = 64
MAX_ALARMOUT_V30 = MAX_ANALOG_ALARM_OUT + MAX_IP_ALARM_OUT
MAX_ANALOG_CHANNUM = 32
MAX_IP_CHANNUM = 32
MAX_CHANNUM_V30 = MAX_ANALOG_CHANNUM + MAX_IP_CHANNUM
MAX_DISKNUM_V30 = 33
MAX_DEV_NUMBER_LEN = 32
ACS_CARD_NO_LEN = 32
LOCK_NAME_LEN = 32
MAX_NOTICE_NUMBER_LEN = 32
MAX_FILE_PATH_LEN = 256

NET_DVR_DEV_ADDRESS_MAX_LEN = 129
NET_DVR_LOGIN_USERNAME_MAX_LEN = 64
NET_DVR_LOGIN_PASSWD_MAX_LEN = 64

COMM_ALARM_RULE = 0x1102
COMM_ALARM_PDC = 0x1103
COMM_UPLOAD_FACESNAP_RESULT = 0x1112
COMM_ALARM_FACE_DETECTION = 0x4010
COMM_SNAP_MATCH_ALARM = 0x2902
COMM_FACESNAP_RAWDATA_ALARM = 0x6015
COMM_ALARM_VQD_EX = 0x1116
COMM_DIAGNOSIS_UPLOAD = 0x5100
COMM_ALARM_VQD = 0x6000
COMM_SCENECHANGE_DETECTION_UPLOAD = 0x1130
COMM_CROSSLINE_ALARM = 0x1131
COMM_ALARM_AUDIOEXCEPTION = 0x1150
COMM_ALARM_DEFOCUS = 0x1151
COMM_UPLOAD_HEATMAP_RESULT = 0x4008
COMM_SWITCH_LAMP_ALARM = 0x6002
COMM_ALARM_TFS = 0x1113
COMM_ALARM_TPS_V41 = 0x1114
COMM_ALARM_AID_V41 = 0x1115
COMM_ITS_PLATE_RESULT = 0x3050
COMM_ITS_TRAFFIC_COLLECT = 0x3051
COMM_ITS_GATE_VEHICLE = 0x3052
COMM_ITS_GATE_FACE = 0x3053
COMM_ITS_GATE_COSTITEM = 0x3054
COMM_ITS_GATE_HANDOVER = 0x3055
COMM_ITS_PARK_VEHICLE = 0x3056
COMM_ITS_BLACKLIST_ALARM = 0x3057
COMM_VEHICLE_CONTROL_LIST_DSALARM = 0x3058
COMM_VEHICLE_CONTROL_ALARM = 0x3059
COMM_FIRE_ALARM = 0x3060
COMM_VEHICLE_RECOG_RESULT = 0x3062
COMM_SIGNAL_LAMP_ABNORMAL = 0x3080
COMM_ALARM_TPS_REAL_TIME = 0x3081
COMM_ALARM_TPS_STATISTICS = 0x3082
COMM_ITC_STATUS_DETECT_RESULT = 0x2810
COMM_ITS_ROAD_EXCEPTION = 0x4500
COMM_ITS_EXTERNAL_CONTROL_ALARM = 0x4520
COMM_SENSOR_VALUE_UPLOAD = 0x1120
COMM_SENSOR_ALARM = 0x1121
COMM_SWITCH_ALARM = 0x1122
COMM_ALARMHOST_EXCEPTION = 0x1123
COMM_ALARMHOST_SAFETYCABINSTATE = 0x1125
COMM_ALARMHOST_ALARMOUTSTATUS = 0x1126
COMM_ALARMHOST_CID_ALARM = 0x1127
COMM_ALARMHOST_EXTERNAL_DEVICE_ALARM = 0x1128
COMM_ALARMHOST_DATA_UPLOAD = 0x1129
COMM_ALARM_WIRELESS_INFO = 0x122b
COMM_ALARM = 0x1100
COMM_ALARM_V30 = 0x4000
COMM_ALARM_V40 = 0x4007
COMM_IPCCFG = 0x4001
COMM_IPCCFG_V31 = 0x4002
COMM_IPC_AUXALARM_RESULT = 0x2820
COMM_ALARM_DEVICE = 0x4004
COMM_ALARM_DEVICE_V40 = 0x4009
COMM_ALARM_CVR = 0x4005
COMM_TRADEINFO = 0x1500
COMM_ALARM_HOT_SPARE = 0x4006
COMM_ALARM_BUTTON_DOWN_EXCEPTION = 0x1152
COMM_ALARM_ACS = 0x5002
COMM_ALARM_LCD = 0x5011
COMM_UPLOAD_VIDEO_INTERCOM_EVENT = 0x1132
COMM_ALARM_VIDEO_INTERCOM = 0x1133
COMM_ALARM_DEC_VCA = 0x5010
COMM_ALARM_STORAGE_DETECTION = 0x4015
COMM_CONFERENCE_CALL_ALARM = 0x5012
COMM_INQUEST_ALARM = 0x6005
COMM_PANORAMIC_LINKAGE_ALARM = 0x5213
COMM_ISAPI_ALARM = 0x6009
COMM_CLUSTER_ALARM = 0x6020
COMM_FACE_THERMOMETRY_ALARM = 0x4994

ALARMINFO_V30_ALARMTYPE_SEMAPHORE_ALARM = 0
ALARMINFO_V30_ALARMTYPE_HARD_DISK_FULL = 1
ALARMINFO_V30_ALARMTYPE_VIDEO_LOST = 2
ALARMINFO_V30_ALARMTYPE_MOTION_DETECTION = 3
ALARMINFO_V30_ALARMTYPE_HARD_DISK_UNFORMATTED = 4
ALARMINFO_V30_ALARMTYPE_HARD_DISK_ERROR = 5
ALARMINFO_V30_ALARMTYPE_TAMPERING_DETECTION = 6
ALARMINFO_V30_ALARMTYPE_UNMATCHED_VIDEO_FORMAT = 7
ALARMINFO_V30_ALARMTYPE_ILLEGAL_ACCESS = 8
ALARMINFO_V30_ALARMTYPE_VIDEO_SIGNAL_IS_ABNORMAL = 9
ALARMINFO_V30_ALARMTYPE_RECORDING_OR_CAPTURE_IS_ABNORMAL = 10
ALARMINFO_V30_ALARMTYPE_INTELLIGENT_SCENE_CHANGED = 11
ALARMINFO_V30_ALARMTYPE_RAID_IS_ABNORMAL = 12
ALARMINFO_V30_ALARMTYPE_RECORDING_RESOLUTION_DOES_NOT_MATCH_WITH_WHICH_OF_FRONT_END_CAMERA = 13
ALARMINFO_V30_ALARMTYPE_VCA = 15
ALARMINFO_V30_ALARMTYPE_POE_POWER_SUPPLY_EXCEPTION = 16
ALARMINFO_V30_ALARMTYPE_FLASHLIGHT_EXCEPTION = 17
ALARMINFO_V30_ALARMTYPE_HDD_FULL_LOAD_EXCEPTION_ALARM = 18
ALARMINFO_V30_ALARMTYPE_AUDIO_LOSS = 19
ALARMINFO_V30_ALARMTYPE_PULSE_ALARM = 23
ALARMINFO_V30_ALARMTYPE_FACE_PICTURE_LIBRARY_HDD_EXCEPTION = 24
ALARMINFO_V30_ALARMTYPE_FACE_PICTURE_LIBRARY_CHANGE = 25
ALARMINFO_V30_ALARMTYPE_PICTURE_OF_FACE_PICTURE_LIBRARY_CHANGE = 26
ALARMINFO_V30_ALARMTYPE_POC_EXCEPTION = 27
ALARMINFO_V30_ALARMTYPE_CAMERA_VIEW_ANGLE_EXCEPTION = 28

VIDEO_INTERCOM_ALARM_ALARMTYPE_ZONE_ALARM = 1
VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM = 2
VIDEO_INTERCOM_ALARM_ALARMTYPE_DURESS_ALARM = 3
VIDEO_INTERCOM_ALARM_ALARMTYPE_PASSWORD_OPEN_DOOR_OVER_TIMES_ALARM = 4
VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_OPEN = 5
VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED = 6
VIDEO_INTERCOM_ALARM_ALARMTYPE_PANIC_ALARM = 7
VIDEO_INTERCOM_ALARM_ALARMTYPE_INTERCOM_ALARM = 8
VIDEO_INTERCOM_ALARM_ALARMTYPE_SMART_LOCK_DURESS_ALARM_FINGERPRINT = 9
VIDEO_INTERCOM_ALARM_ALARMTYPE_SMART_LOCK_DURESS_ALARM_PASSWORD = 10
VIDEO_INTERCOM_ALARM_ALARMTYPE_SMART_LOCK_TAMPERING_ALARM = 11
VIDEO_INTERCOM_ALARM_ALARMTYPE_SMART_LOCK_LOCK_UP_ALARM = 12
VIDEO_INTERCOM_ALARM_ALARMTYPE_SMART_LOCK_LOW_BATTERY_ALARM = 13
VIDEO_INTERCOM_ALARM_ALARMTYPE_BLACKLIST_ALARM = 14
VIDEO_INTERCOM_ALARM_ALARMTYPE_SMART_LOCK_DISCONNECTED = 15
VIDEO_INTERCOM_ALARM_ALARMTYPE_ACCESS_CONTROL_MODULE_ANTI_TAMPERING_ALARM = 16
VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING = 17
VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL = 18

VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG = 1
VIDEO_INTERCOM_EVENT_EVENTTYPE_ANNOUNCEMENT_READING_RECEIPT = 2
VIDEO_INTERCOM_EVENT_EVENTTYPE_AUTHENTICATION_LOG = 3
VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT = 5
VIDEO_INTERCOM_EVENT_EVENTTYPE_DOOR_STATION_ISSUED_CARD_LOG = 6

###########################################
# Enums


class VideoInterComAlarmType(IntEnum):
    ZONE_ALARM = 1
    TAMPERING_ALARM = 2
    HIJACKING_ALARM = 3
    MULTIPLE_PASSWORD_UNLOCK_FAILURE_ALARM = 4
    DOOR_NOT_OPEN = 5
    DOOR_NOT_CLOSED = 6
    SOS = 7
    INTERCOM = 8
    SMART_LOCK_FINGERPRINT_ALARM = 9    # fingerprint alarm for smart lock hijacking
    SMART_LOCK_PASSWORD_ALARM = 10      # password alarm for smart lock hijacking
    SMART_LOCK_DOOR_PRYING_ALARM = 11   # door prying alarm for smart lock
    SMART_LOCK_DOOR_LOCK_ALARM = 12     # door lock lock alarm for smart lock
    SMART_LOCK_LOW_BATTERY_ALARM = 13   # low battery alarm for smart lock
    BLACKLIST_ALARM = 14
    SMART_LOCK_DISCONNECTED = 15
    ACCESS_CONTROL_TAMPERING_ALARM = 16  # Access control security module tamper alarm
    DOORBELL_RINGING = 17
    DISMISS_INCOMING_CALL = 18


class DeviceCapabilityType(Enum):
    DEVICE_VIDEOPIC_ABILITY = 0x00e
    DEVICE_NETAPP_ABILITY = 0x00d
    DEVICE_ABILITY_INFO = 0x011


class DeviceAbilityType(IntEnum):
    IP_VIEW_DEV_ABILITY = 0x014


###########################
# Struct

class LPNET_DVR_DEVICE_INFO(Structure):
    _fields_ = [
        ("sSerialNumber", BYTE * SERIALNO_LEN),
        ("byAlarmInPortNum", BYTE),
        ("byAlarmOutPortNum", BYTE),
        ("byDiskNum", BYTE),
        ("byDVRType", BYTE),
        ("byChanNum", BYTE),
        ("byStartChan", BYTE),
        ("byAudioChanNum", BYTE),
        ("byIPChanNum", BYTE),
        ("byZeroChanNum", BYTE),
        ("byMainProto", BYTE),
        ("bySubProto", BYTE),
        ("bySupport", BYTE),
        ("bySupport1", BYTE),
        ("bySupport2", BYTE),
        ("wDevType", WORD),
        ("bySupport3", BYTE),
        ("byMultiStreamProto", BYTE),
        ("byStartDChan", BYTE),
        ("byStartDTalkChan", BYTE),
        ("byHighDChanNum", BYTE),
        ("bySupport4", BYTE),
        ("byVoiceInChanNum", BYTE),
        ("byStartVoiceInChanNo", BYTE),
        ("bySupport5", BYTE),
        ("bySupport6", BYTE),
        ("byMirrorChanNum", BYTE),
        ("wStartMirrorChanNo", WORD),
        ("bySupport7", BYTE),
        ("byRes2", BYTE)
    ]


cbLoginResult = CFUNCTYPE(c_void_p, LONG, DWORD,
                          LPNET_DVR_DEVICE_INFO, c_void_p)


class NET_DVR_USER_LOGIN_INFO(Structure):
    _fields_ = [
        ("sDeviceAddress", char * NET_DVR_DEV_ADDRESS_MAX_LEN),
        ("byUseTransport", BYTE),
        ("wPort", WORD),
        ("sUserName", char * NET_DVR_LOGIN_USERNAME_MAX_LEN),
        ("sPassword", char * NET_DVR_LOGIN_PASSWD_MAX_LEN),
        ("fLoginResultCallBack", cbLoginResult),
        ("pUser", c_void_p),
        ("bUseAsynLogin", BOOL),
        ("byProxyType", BYTE),
        ("byUseUTCTime", BYTE),
        ("byLoginMode", BYTE),
        ("byHttps", BYTE),
        ("iProxyID", LONG),
        ("byRes2", BYTE * 120)
    ]


class NET_DVR_ALARMER(Structure):
    _fields_ = [
        ("byUserIDValid", BYTE),
        ("bySerialValid", BYTE),
        ("byVersionValid", BYTE),
        ("byDeviceNameValid", BYTE),
        ("byMacAddrValid", BYTE),
        ("byLinkPortValid", BYTE),
        ("byDeviceIPValid", BYTE),
        ("bySocketIPValid", BYTE),
        ("lUserID", LONG),
        ("sSerialNumber", BYTE * SERIALNO_LEN),
        ("dwDeviceVersion", DWORD),
        ("sDeviceName", char * NAME_LEN),
        ("byMacAddr", BYTE * MACADDR_LEN),
        ("wLinkPort", WORD),
        ("sDeviceIP", char * 128),
        ("sSocketIP", char * 128),
        ("byIpProtocol", BYTE),
        ("byRes2", BYTE * 6)
    ]

    def serialNumber(self):
        """Return the serial number as a string representation, removing the ending 0s"""
        serial = "".join([str(number) for number in self.sSerialNumber[:]])
        return re.sub(r"0*$", "", serial)

    def deviceName(self):
        return self.sDeviceName[:].decode('utf-8')

    def deviceIP(self):
        return self.sDeviceIP[:].decode('utf-8')


class NET_DVR_DEVICEINFO_V30(Structure):
    _fields_ = [
        ("sSerialNumber", BYTE * SERIALNO_LEN),
        ("byAlarmInPortNum", BYTE),
        ("byAlarmOutPortNum", BYTE),
        ("byDiskNum", BYTE),
        ("byDVRType", BYTE),
        ("byChanNum", BYTE),
        ("byStartChan", BYTE),
        ("byAudioChanNum", BYTE),
        ("byIPChanNum", BYTE),
        ("byZeroChanNum", BYTE),
        ("byMainProto", BYTE),
        ("bySubProto", BYTE),
        ("bySupport", BYTE),
        ("bySupport1", BYTE),
        ("bySupport2", BYTE),
        ("wDevType", WORD),
        ("bySupport3", BYTE),
        ("byMultiStreamProto", BYTE),
        ("byStartDChan", BYTE),
        ("byStartDTalkChan", BYTE),
        ("byHighDChanNum", BYTE),
        ("bySupport4", BYTE),
        ("byLanguageType", BYTE),
        ("byVoiceInChanNum", BYTE),
        ("byStartVoiceInChanNo", BYTE),
        ("byRes3", BYTE * 2),
        ("byMirrorChanNum", BYTE),
        ("wStartMirrorChanNo", WORD)
    ]

    def serialNumber(self):
        """Return the serial number as a string representation, removing the ending 0s"""
        serial = "".join([str(number) for number in self.sSerialNumber[:]])
        return re.sub(r"0*$", "", serial)


class NET_DVR_DEVICEINFO_V40(Structure):
    _fields_ = [
        ("struDeviceV30", NET_DVR_DEVICEINFO_V30),
        ("bySupportLock", BYTE),
        ("byRetryLoginTime", BYTE),
        ("byPasswordLevel", BYTE),
        ("byProxyType", BYTE),
        ("dwSurplusLockTime", DWORD),
        ("byCharEncodeType", BYTE),
        ("bySupportDev5", BYTE),
        ("byLoginMode", BYTE),
        ("byRes2", BYTE * 253)
    ]

class NET_DVR_SETUPALARM_PARAM(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("byLevel", BYTE),
        ("byAlarmInfoType", BYTE),
        ("byRetAlarmTypeV40", BYTE),
        ("byRetDevInfoVersion", BYTE),
        ("byRetVQDAlarmType", BYTE),
        ("byFaceAlarmDetection", BYTE),
        ("bySupport", BYTE),
        ("byBrokenNetHttp", BYTE),
        ("wTaskNo", WORD),
        ("byDeployType", BYTE),
        ("byRes1", BYTE * 3),
        ("byAlarmTypeURL", BYTE),
        ("byCustomCtrl", BYTE)
    ]

class NET_DVR_SETUPALARM_PARAM_V50(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("byLevel", BYTE),
        ("byAlarmInfoType", BYTE),
        ("byRetAlarmTypeV40", BYTE),
        ("byRetDevInfoVersion", BYTE),
        ("byRetVQDAlarmType", BYTE),
        ("byFaceAlarmDetection", BYTE),
        ("bySupport", BYTE),
        ("byBrokenNetHttp", BYTE),
        ("wTaskNo", WORD),
        ("byDeployType", BYTE),
        ("byRes1", BYTE * 3),
        ("byAlarmTypeURL", BYTE),
        ("byCustomCtrl", BYTE),
        ("byRes4", BYTE * 128),
    ]


class NET_DVR_ALARMINFO_V30(Structure):
    _fields_ = [
        ("dwAlarmType", DWORD),
        ("dwAlarmInputNumber", DWORD),
        ("byAlarmOutputNumber", BYTE * MAX_ALARMOUT_V30),
        ("byAlarmRelateChannel", BYTE * MAX_CHANNUM_V30),
        ("byChannel", BYTE * MAX_CHANNUM_V30),
        ("byDiskNumber", BYTE * MAX_DISKNUM_V30)
    ]

class NET_DVR_TIME_EX(Structure):
    _fields_ = [
        ("wYear", WORD),
        ("byMonth", BYTE),
        ("byDay", BYTE),
        ("byHour", BYTE),
        ("byMinute", BYTE),
        ("bySecond", BYTE),
        ("byRes", BYTE)
    ]

class NET_DVR_ZONE_ALARM_INFO(Structure):
    _fields_ = [
        ("byZoneName", BYTE * NAME_LEN),
        ("dwZonendex", DWORD),
        ("byZoneType", BYTE),
        ("byRes", BYTE * 219), 
    ]

class NET_DVR_VIDEO_INTERCOM_ALARM_INFO_UNION(Structure):
    _fields_ = [
        ("byLen", BYTE * 256),
        ("struZoneAlarm", NET_DVR_ZONE_ALARM_INFO),
    ]

class NET_DVR_VIDEO_INTERCOM_ALARM(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("struTime", NET_DVR_TIME_EX),
        ("byDevNumber", BYTE * MAX_DEV_NUMBER_LEN),
        ("byAlarmType", BYTE),
        ("byRes1", BYTE * 3),
        ("uAlarmInfo", NET_DVR_VIDEO_INTERCOM_ALARM_INFO_UNION),
        ("wLockID", BYTE),
        ("byRes2", BYTE)
    ]

class NET_DVR_UNLOCK_RECORD_INFO(Structure):
    _fields_ = [
        ("byUnlockType", BYTE),
        ("byRes1", BYTE * 3),
        ("byControlSrc", BYTE * NAME_LEN),
        ("dwPicDataLen", DWORD),
        ("pImage", POINTER(BYTE)),
        ("dwCardUserID", DWORD),
        ("nFloorNumber", SHORT),
        ("wRoomNumber", WORD),
        ("wLockID", WORD),
        ("byRes2", BYTE * 2),
        ("byLockName", BYTE * LOCK_NAME_LEN),
        ("byRes", BYTE * 168),
    ]

    def controlSource(self):
        """Return the controls source number as a string representation, removing the ending `0`s"""
        serial = "".join([str(number) for number in self.byControlSrc[:]])
        return re.sub(r"0*$", "", serial)


class NET_DVR_NOTICEDATA_RECEIPT_INFO(Structure):
    _fields_ = [
        ("byNoticeNumber", BYTE * MAX_NOTICE_NUMBER_LEN),
        ("byRes", BYTE * 224)
    ]

class NET_DVR_SEND_CARD_INFO(Structure):
    _fields_ = [
        ("byCardNo", BYTE * ACS_CARD_NO_LEN),
        ("byRes", BYTE * 224)
    ]

class NET_DVR_AUTH_INFO(Structure):
    _fields_ = [
        ("byAuthResult", BYTE),
        ("byAuthType", BYTE),
        ("byRes1", BYTE * 2),
        ("byCardNo", BYTE * ACS_CARD_NO_LEN),
        ("dwPicDataLen", DWORD),
        ("pImage", POINTER(BYTE)),
        ("byRes", BYTE * 212),
    ]

class NET_DVR_VIDEO_INTERCOM_EVENT_INFO_UINON(Union):
    _fields_ = [
        ("byLen", BYTE),
        ("struUnlockRecord", NET_DVR_UNLOCK_RECORD_INFO),
        ("struNoticedataReceipt", NET_DVR_NOTICEDATA_RECEIPT_INFO),
        ("struAuthInfo", NET_DVR_AUTH_INFO),
        ("struSendCardInfo", NET_DVR_SEND_CARD_INFO),
    ]
class NET_DVR_CONTROL_GATEWAY(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("dwGatewayIndex", DWORD),
        ("byCommand", BYTE),
        ("byLockType", BYTE),
        ("wLockID", SHORT),
        ("byControlSrc", BYTE * NAME_LEN),
        ("byControlType", BYTE),
        ("byRes3", BYTE * 3),
        ("byPassword", BYTE * 16),
        ("byRes2", BYTE * 108),
    ]

class NET_DVR_XML_CONFIG_INPUT(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("lpRequestUrl", c_void_p),
        ("dwRequestUrlLen", DWORD),
        ("lpInBuffer", c_void_p),
        ("dwInBufferSize", DWORD),
        ("dwRecvTimeOut", DWORD),
        ("byForceEncrpt", BYTE),
        ("byRes", BYTE * 31),
    ]

class NET_DVR_XML_CONFIG_OUTPUT(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("lpOutBuffer", c_void_p),
        ("dwOutBufferSize", DWORD),
        ("dwReturnedXMLSize", DWORD),
        ("lpStatusBuffer", c_void_p),
        ("dwStatusSize", DWORD),
        ("byRes", BYTE * 31),
    ]
class NET_DVR_CALL_STATUS(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("byCallStatus", BYTE),
        ("byRes", BYTE * 127),
    ]

class NET_DVR_VIDEO_CALL_PARAM(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("dwCmdType", DWORD),
        ("wPeriod", WORD),
        ("wBuildingNumber", WORD),
        ("wUnitNumber", WORD),
        ("wFloorNumber", SHORT),
        ("wRoomNumber", WORD),
        ("wDevIndex", WORD),
        ("byUnitType", BYTE),
        ("byRes", BYTE * 115),
    ]

class NET_DVR_MIME_UNIT(Structure):
    _fields_ = [
        ("szContentType", char * 32),
        ("szName", char * MAX_FILE_PATH_LEN),
        ("szFilename", char * MAX_FILE_PATH_LEN),
        ("dwContentLen", DWORD),
        ("pContent", c_char_p),
        ("byRes", BYTE * 16),
    ]

#class NET_DVR_JPEGPARA(Structure):
#    _fields_ = [
#        ("wPicSize", WORD),
#        ("wPicQuality", WORD)
#    ]
class NET_DVR_VIDEO_INTERCOM_EVENT(Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("struTime", NET_DVR_TIME_EX),
        ("byDevNumber", BYTE * MAX_DEV_NUMBER_LEN),
        ("byEventType", BYTE),
        ("byRes1", BYTE * 3),
        ("uEventInfo", NET_DVR_VIDEO_INTERCOM_EVENT_INFO_UINON),
        ("byRes2", BYTE * 256),
    ]
class NET_DVR_ALARM_ISAPI_PICDATA(Structure):
    _fields_ = [
        ("dwPicLen", DWORD),
        ("byRes", BYTE * 4),
        ("szFilename", char * MAX_FILE_PATH_LEN),
        ("pPicData", BYTE),
    ]
class NET_DVR_ALARM_ISAPI_INFO(Structure):
    _fields_ = [
        ("pAlarmData", char),
        ("dwAlarmDataLen", DWORD),
        ("byDataType", BYTE),
        ("byPicturesNumber", BYTE),
        ("byRes", BYTE * 2),
        ("pPicPackData", NET_DVR_ALARM_ISAPI_PICDATA),
        ("byRes2", BYTE * 32),
    ]

class MessageCallbackAlarmInfoUnion(Union):
    _fields_ = [
        ("NET_DVR_ALARMINFO_V30", NET_DVR_ALARMINFO_V30),
        ("NET_DVR_VIDEO_INTERCOM_ALARM", NET_DVR_VIDEO_INTERCOM_ALARM),
        ("NET_DVR_VIDEO_INTERCOM_EVENT", NET_DVR_VIDEO_INTERCOM_EVENT),
        ("NET_DVR_ALARM_ISAPI_INFO", NET_DVR_ALARM_ISAPI_INFO)
    ]


fMessageCallBack = CFUNCTYPE(BOOL, LONG, POINTER(
    NET_DVR_ALARMER), POINTER(MessageCallbackAlarmInfoUnion), DWORD, c_void_p)

