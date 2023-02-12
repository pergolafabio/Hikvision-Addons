from sdk.hcnetsdk import NET_DVR_DEVICEINFO_V30, NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM, fMessageCallBack, \
    COMM_ALARM_V30, COMM_ALARM_VIDEO_INTERCOM, NET_DVR_VIDEO_INTERCOM_ALARM, NET_DVR_ALARMINFO_V30, \
    ALARMINFO_V30_ALARMTYPE_MOTION_DETECTION, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING, \
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL, VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM, \
    VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED, COMM_UPLOAD_VIDEO_INTERCOM_EVENT, NET_DVR_VIDEO_INTERCOM_EVENT, \
    VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG, VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT, \
    NET_DVR_UNLOCK_RECORD_INFO, NET_DVR_CONTROL_GATEWAY, NET_DVR_XML_CONFIG_INPUT, NET_DVR_XML_CONFIG_OUTPUT
from ctypes import POINTER, cast, c_char_p, c_byte, sizeof, byref, memmove, c_void_p, c_char
import requests
import json
import time
import sys
from config import ADDON_CONFIG_PATH, loadConfig, SUPERVISOR_TOKEN
from sdk.utils import loadSDK
from loguru import logger

config = loadConfig(ADDON_CONFIG_PATH)
if __name__ == '__main__':
    # Remove the default handler installed by loguru (it redirects to stderr)
    logger.remove()
    logger.add(sys.stdout, colorize=True, level=config.system.log_level)
    logger.debug('Importing HIKVISION SDK')
    HCNetSDK = loadSDK()
    logger.debug("Hikvision SDK loaded")

sensor_name_door = "sensor." + config.sensor_door
sensor_name_callstatus = "sensor." + config.sensor_callstatus
sensor_name_motion = "sensor." + config.sensor_motion
sensor_name_tamper = "sensor." + config.sensor_tamper
sensor_name_dismiss = "sensor." + config.sensor_dismiss


def callback(command: int, alarmer_pointer, alarminfo_pointer, buffer_length, user_pointer):
    if (command == COMM_ALARM_V30):
        alarminfo_alarm_v30: NET_DVR_ALARMINFO_V30 = cast(
            alarminfo_pointer, POINTER(NET_DVR_ALARMINFO_V30)).contents
        if (alarminfo_alarm_v30.dwAlarmType == ALARMINFO_V30_ALARMTYPE_MOTION_DETECTION):
            logger.info("Motion detected, updating sensor {}", sensor_name_motion)
            update_sensor(sensor_name_motion, 'on')
            time.sleep(1)
            update_sensor(sensor_name_motion, 'off')
        else:
            logger.warning("COMM_ALARM_V30, unhandled dwAlarmType: {}", alarminfo_alarm_v30.dwAlarmType)

    elif (command == COMM_ALARM_VIDEO_INTERCOM):
        alarminfo_alarm_video_intercom: NET_DVR_VIDEO_INTERCOM_ALARM = cast(
            alarminfo_pointer, POINTER(NET_DVR_VIDEO_INTERCOM_ALARM)).contents
        if (alarminfo_alarm_video_intercom.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING):
            logger.info("Doorbell ringing, updating sensor {}", sensor_name_callstatus)
            update_sensor(sensor_name_callstatus, 'on')
            time.sleep(1)
            update_sensor(sensor_name_callstatus, 'off')
        elif (alarminfo_alarm_video_intercom.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL):
            logger.info("Call dismissed, updating sensor {}", sensor_name_dismiss)
            update_sensor(sensor_name_dismiss, 'on')
            time.sleep(1)
            update_sensor(sensor_name_dismiss, 'off')
        elif (alarminfo_alarm_video_intercom.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM):
            logger.info("Tampering alarm, updating sensor {}", sensor_name_tamper)
            update_sensor(sensor_name_tamper, 'on')
            time.sleep(1)
            update_sensor(sensor_name_tamper, 'off')
        elif (alarminfo_alarm_video_intercom.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED):
            logger.info("Door not closed alarm")
        else:
            logger.warning("COMM_ALARM_VIDEO_INTERCOM, unhandled byAlarmType: {}",
                           alarminfo_alarm_video_intercom.byAlarmType)

    elif (command == COMM_UPLOAD_VIDEO_INTERCOM_EVENT):
        alarminfo_upload_video_intercom_event: NET_DVR_VIDEO_INTERCOM_EVENT = cast(
            alarminfo_pointer, POINTER(NET_DVR_VIDEO_INTERCOM_EVENT)).contents
        if (alarminfo_upload_video_intercom_event.byEventType == VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG):
            logger.info("Door {} unlocked by {}, updating sensor {}",
                        alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.wLockID,
                        list(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.byControlSrc),
                        sensor_name_door)
            attributes = {
                'Unlock': list(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.byControlSrc),
                'DoorID': alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.wLockID
            }
            update_sensor(sensor_name_door, 'on', attributes)
            time.sleep(1)
            update_sensor(sensor_name_door, 'off', attributes)

        elif (
                alarminfo_upload_video_intercom_event.byEventType == VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT):
            logger.info("Illegal card swiping")
        else:
            logger.warning("COMM_ALARM_VIDEO_INTERCOM, unhandled byEventType: {}",
                           alarminfo_upload_video_intercom_event.byEventType)
    else:
        logger.warning("Unhandled command: {}", command)


headers = {
    'Authorization': f'Bearer {SUPERVISOR_TOKEN}'
}


def update_sensor(sensor_name: str, state: str, attr: dict = None):
    """ Update the sensor by invoking the Home Assistant HTTP API
    """
    data = {'state': state, 'attributes': attr}
    try:
        response = requests.post(url_states + sensor_name, headers=headers, json=data)
        # Check that the server returned a successful HTTP response code
        response.raise_for_status()
        logger.debug("Response {} {}", response.text, response.json())
    except:
        logger.exception("Cannot update sensor")


## Unused function
def set_attribute(sensor_name, attribute, value):
    response = requests.get(url_states + sensor_name, headers=headers)
    msg = json.loads(response.text)
    msg['attributes'][attribute] = value
    payload = json.dumps({'state': msg['state'], 'attributes': msg['attributes']})
    requests.post(url_states + sensor_name, headers=headers, data=payload)


# url_states = config["url_states"]
url_states = "http://supervisor/core/api/states/"

HCNetSDK.NET_DVR_Init()
HCNetSDK.NET_DVR_SetLogToFile(3, bytes("/tmp/", 'utf8'), False)
HCNetSDK.NET_DVR_SetValidIP(0, True)

device_info = NET_DVR_DEVICEINFO_V30()
user_id = HCNetSDK.NET_DVR_Login_V30(config.ip.encode('utf-8'), 8000, config.username.encode('utf-8'),
                                     config.password.encode('utf-8'), device_info)

# fix for segmentation faults, remove device info:

# device_info = NET_DVR_DEVICEINFO_V30()
# user_id = HCNetSDK.NET_DVR_Login_V30(config["ip"].encode('utf-8'), 8000, config["username"].encode('utf-8'), config["password"].encode('utf-8'))

# Check that we have successfully logged in the doorbell
if (user_id < 0):
    logger.error("NET_DVR_Login_V30 failed, error code = {}", HCNetSDK.NET_DVR_GetLastError())
    HCNetSDK.NET_DVR_Cleanup()
    exit(1)

alarm_param = NET_DVR_SETUPALARM_PARAM()
alarm_param.dwSize = 20
alarm_param.byLevel = 1
alarm_param.byAlarmInfoType = 1
alarm_param.byFaceAlarmDetection = 1

alarm_handle = HCNetSDK.NET_DVR_SetupAlarmChan_V41(user_id, alarm_param)

if (alarm_handle < 0):
    logger.error("NET_DVR_SetupAlarmChan_V41 failed, error code {}", HCNetSDK.NET_DVR_GetLastError())
    HCNetSDK.NET_DVR_Logout_V30(user_id)
    HCNetSDK.NET_DVR_Cleanup()
    exit(2)

message_callback = fMessageCallBack(callback)
HCNetSDK.NET_DVR_SetDVRMessageCallBack_V50(0, message_callback, user_id)


def unlock_door(lockID):
    gw = NET_DVR_CONTROL_GATEWAY()
    gw.dwSize = sizeof(NET_DVR_CONTROL_GATEWAY)
    gw.dwGatewayIndex = 1
    gw.byCommand = 1  # opening command
    gw.byLockType = 0  # this is normal lock not smart lock
    gw.wLockID = lockID  # door station
    gw.byControlSrc = (c_byte * 32)(*[97, 98, 99, 100])  # anything will do but can't be empty
    gw.byControlType = 1

    # TODO: check result
    result = HCNetSDK.NET_DVR_RemoteControl(user_id, 16009, byref(gw), gw.dwSize)
    logger.info(" Door {} unlocked by SDK", lockID + 1)


def callsignal(value):
    HCNetSDK.NET_DVR_Init()
    HCNetSDK.NET_DVR_SetValidIP(0, True)
    # For 8003 owners, send callsignal to indoor station!!!!

    user_id_indoor = HCNetSDK.NET_DVR_Login_V30(config.ip_indoor.encode('utf-8'), 8000,
                                                config.username.encode('utf-8'), config.password.encode('utf-8'))
    if (user_id_indoor < 0):
        logger.error("NET_DVR_Login_V30 failed, error code = {}", HCNetSDK.NET_DVR_GetLastError())

        HCNetSDK.NET_DVR_Cleanup()
        exit(1)

    # inUrl = "GET /ISAPI/VideoIntercom/callSignal/capabilities?format=json"
    # inPutBuffer = ""
    # RESULTS :  ["answer", "reject", "bellTimeout", "hangUp", "deviceOnCall"]

    inUrl = "PUT /ISAPI/VideoIntercom/callSignal?format=json"
    # TODO: is manual serialization to JSON required here?
    inPutBuffer = "{\"CallSignal\":{\"cmdType\":\"" + value + "\"}}"
    logger.debug("Inputbuffer: {}" + json.dumps(inPutBuffer))
    # "{\"CallSignal\":{\"cmdType\":\"reject\"}}"

    # optional , but not needed??
    # inPutBuffer = "{\"CallSignal\":{\"cmdType\":\"reject\",\"periodNumber\": 1,\"buildingNumber\": 1,\"unitNumber\": 1,\"floorNumber\": 0,\"roomNumber\": 1,\"unitType\": \"villa\",\"coderType\":\"ezviz\", \"model\": 1}}"
    # inPutBuffer = "{\"CallSignal\":{\"cmdType\":\"reject\",\"src\":{\"periodNumber\":1,\"buildingNumber\":1,\"unitNumber\":1,\"floorNumber\":0,\"roomNumber\":1}}}"

    # optional , but not needed??
    # inUrl = "DELETE /ISAPI/VideoIntercom/ring"
    # inPutBuffer = ""

    szUrl = (c_char * 256)()
    struInput = NET_DVR_XML_CONFIG_INPUT()
    struOuput = NET_DVR_XML_CONFIG_OUTPUT()

    struInput.dwSize = sizeof(struInput)
    struOuput.dwSize = sizeof(struOuput)
    dwBufferLen = 1024 * 1024
    pBuffer = (c_char * dwBufferLen)()

    szGetOutput = (1024 * 1024)
    pszGetOutput = (c_char * szGetOutput)()

    csCommand = bytes(inUrl, "ascii")
    memmove(szUrl, csCommand, len(csCommand))
    struInput.lpRequestUrl = cast(szUrl, c_void_p)
    struInput.dwRequestUrlLen = len(szUrl)

    m_csInputParam = bytes(inPutBuffer, "ascii")
    dwInBufferLen = 1024 * 1024
    pInBuffer = (c_byte * dwInBufferLen)()
    memmove(pInBuffer, m_csInputParam, len(m_csInputParam))

    struInput.lpInBuffer = cast(pInBuffer, c_void_p)
    # struInput.lpInBuffer = None

    struInput.dwInBufferSize = len(m_csInputParam)
    # struInput.dwInBufferSize = 0

    struOuput.lpStatusBuffer = cast(pBuffer, c_void_p)
    struOuput.dwStatusSize = dwBufferLen

    struOuput.lpOutBuffer = cast(pszGetOutput, c_void_p)
    struOuput.dwOutBufferSize = szGetOutput

    result = HCNetSDK.NET_DVR_STDXMLConfig(user_id_indoor, byref(struInput), byref(struOuput))

    # print(result)
    # print(pBuffer.value)
    # print(pszGetOutput.value.decode("utf-8") )
    logger.debug("Response buffer: {}", json.dumps(pBuffer.value.decode("utf-8")))
    logger.debug("Response output: {}", json.dumps(pszGetOutput.value.decode("utf-8")))
    if result == 0:
        # print(HCNetSDK.NET_DVR_GetLastError())
        logger.error("Result error: {}", HCNetSDK.NET_DVR_GetLastError())

    HCNetSDK.NET_DVR_Logout_V30(user_id_indoor)
    HCNetSDK.NET_DVR_Cleanup()


def reboot_device():
    inUrl = "PUT /ISAPI/System/reboot"
    # TODO: is manual serialization to JSON required here?
    inPutBuffer = ""
    logger.debug("Inputbuffer: {}" + json.dumps(inPutBuffer))

    szUrl = (c_char * 256)()
    struInput = NET_DVR_XML_CONFIG_INPUT()
    struOuput = NET_DVR_XML_CONFIG_OUTPUT()

    struInput.dwSize = sizeof(struInput)
    struOuput.dwSize = sizeof(struOuput)
    dwBufferLen = 1024 * 1024
    pBuffer = (c_char * dwBufferLen)()

    szGetOutput = (1024 * 1024)
    pszGetOutput = (c_char * szGetOutput)()

    csCommand = bytes(inUrl, "ascii")
    memmove(szUrl, csCommand, len(csCommand))
    struInput.lpRequestUrl = cast(szUrl, c_void_p)
    struInput.dwRequestUrlLen = len(szUrl)

    m_csInputParam = bytes(inPutBuffer, "ascii")
    dwInBufferLen = 1024 * 1024
    pInBuffer = (c_byte * dwInBufferLen)()
    memmove(pInBuffer, m_csInputParam, len(m_csInputParam))

    struInput.lpInBuffer = cast(pInBuffer, c_void_p)
    # struInput.lpInBuffer = None

    struInput.dwInBufferSize = len(m_csInputParam)
    # struInput.dwInBufferSize = 0

    struOuput.lpStatusBuffer = cast(pBuffer, c_void_p)
    struOuput.dwStatusSize = dwBufferLen

    struOuput.lpOutBuffer = cast(pszGetOutput, c_void_p)
    struOuput.dwOutBufferSize = szGetOutput

    result = HCNetSDK.NET_DVR_STDXMLConfig(user_id, byref(struInput), byref(struOuput))

    logger.debug("Response buffer: {}", json.dumps(pBuffer.value.decode("utf-8")))
    logger.debug("Response output: {}", json.dumps(pszGetOutput.value.decode("utf-8")))
    if result == 0:
        logger.error("Result error: {}", HCNetSDK.NET_DVR_GetLastError())

# def NET_DVR_CaptureJPEGPicture():
#    sJpegPicFileName = b'test.jpg'
#    lpJpegPara = NET_DVR_JPEGPARA()
#    lpJpegPara.wPicSize = 2
#    lpJpegPara.wPicQuality = 1
#    res = HCNetSDK.NET_DVR_CaptureJPEGPicture(user_id, 1, byref(lpJpegPara), sJpegPicFileName)
#    if res == False:
#        os.system("Success")
#    else:
#        os.system("Grab stream fail")

loop = True
while loop:
    try:
        line = input()
        logger.debug("Received input: `{}`", line)
        if "unlock1" in line:
            logger.info("Unlocking door 1")
            unlock_door(0)
        elif "unlock2" in line:
            logger.info("Unlocking door 2")
            unlock_door(1)
        # Callsignal keywords : "request,cancle,answer,reject,bellTimeout,hangUp,deviceOnCall"
        elif "reject" in line:
            logger.info("Rejecting the call")
            callsignal("reject")
        elif "answer" in line:
            logger.info("Answering the call")
            callsignal("answer")
        elif "cancle" in line:
            # TODO: fix typo
            logger.info("Cancelling the call")
            callsignal("cancle")
        elif "hangUp" in line:
            logger.info("Hanging up the call")
            callsignal("hangUp")
        elif "request" in line:
            logger.info("Requesting call")
            callsignal("request")
        elif "bellTimeout" in line:
            logger.info("Bell timeout")
            callsignal("bellTimeout")
        elif "deviceOnCall" in line:
            logger.info("Device on call")
            callsignal("deviceOnCall")
        elif "reboot" in line:
            logger.info("Rebooting Doorstation")
            reboot_device()
        #   elif "image" in line:
        #       os.system("echo Trying to grab an image... Stdin message: " + str(line))
        #       NET_DVR_CaptureJPEGPicture()
        else:
            logger.error("Command not recognized: {}. Please see the documentation for the list of supported commands.",
                         line)
    except EOFError:
        loop = False
        logger.debug("Shutting down addon, cleaning up SDK")

# Shutdown HikVision SDK
HCNetSDK.NET_DVR_CloseAlarmChan_V30(alarm_handle)
HCNetSDK.NET_DVR_Logout_V30(user_id)
HCNetSDK.NET_DVR_Cleanup()
