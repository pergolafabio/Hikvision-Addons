from hcnetsdk import HCNetSDK, NET_DVR_DEVICEINFO_V30, NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM, fMessageCallBack, COMM_ALARM_V30, COMM_ALARM_VIDEO_INTERCOM, NET_DVR_VIDEO_INTERCOM_ALARM, NET_DVR_ALARMINFO_V30, ALARMINFO_V30_ALARMTYPE_MOTION_DETECTION, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING, VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL, VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM, VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED, COMM_UPLOAD_VIDEO_INTERCOM_EVENT, NET_DVR_VIDEO_INTERCOM_EVENT, VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG, VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT, NET_DVR_UNLOCK_RECORD_INFO, NET_DVR_CONTROL_GATEWAY
from ctypes import POINTER, cast, c_char_p, c_byte, sizeof, byref
import requests
import json
import time
import sys
import os

def callback(command: int, alarmer_pointer, alarminfo_pointer, buffer_length, user_pointer):
    if (command == COMM_ALARM_V30):
        alarminfo_alarm_v30: NET_DVR_ALARMINFO_V30 = cast(
            alarminfo_pointer, POINTER(NET_DVR_ALARMINFO_V30)).contents
        if (alarminfo_alarm_v30.dwAlarmType == ALARMINFO_V30_ALARMTYPE_MOTION_DETECTION):
            os.system("echo Motion detected, trying to update: " + sensor_name_motion)
            data = json.dumps({'state': 'on'})
            response = requests.post(url_states + sensor_name_motion, headers=headers, data=data)
            time.sleep(2)
            data = json.dumps({'state': 'off'})
            response = requests.post(url_states + sensor_name_motion, headers=headers, data=data)            
        else:
            os.system("echo COMM_ALARM_V30, unhandled dwAlarmType: " + str(alarminfo_alarm_v30.dwAlarmType))
    elif(command == COMM_ALARM_VIDEO_INTERCOM):
        alarminfo_alarm_video_intercom: NET_DVR_VIDEO_INTERCOM_ALARM = cast(
            alarminfo_pointer, POINTER(NET_DVR_VIDEO_INTERCOM_ALARM)).contents        
        if (alarminfo_alarm_video_intercom.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOORBELL_RINGING):
            try:
                os.system("echo Doorbell ringing, trying to update: " + sensor_name_callstatus)
                data = json.dumps({'state': 'on'})
                response = requests.post(url_states + sensor_name_callstatus, headers=headers, data=data)
                time.sleep(2)
                data = json.dumps({'state': 'off'})
                response = requests.post(url_states + sensor_name_callstatus, headers=headers, data=data)
            except:
                os.system("echo Sensor updating failed")
             
        elif (alarminfo_alarm_video_intercom.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DISMISS_INCOMING_CALL):
            os.system("echo Call dismissed")            
        elif (alarminfo_alarm_video_intercom.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_TAMPERING_ALARM):
            os.system("echo Tampering alarm")
        elif (alarminfo_alarm_video_intercom.byAlarmType == VIDEO_INTERCOM_ALARM_ALARMTYPE_DOOR_NOT_CLOSED):
            os.system("echo Door not closed")
        else:
            os.system("echo COMM_ALARM_VIDEO_INTERCOM, unhandled byAlarmType: "+ str(alarminfo_alarm_video_intercom.byAlarmType))
    elif(command == COMM_UPLOAD_VIDEO_INTERCOM_EVENT):
        alarminfo_upload_video_intercom_event: NET_DVR_VIDEO_INTERCOM_EVENT = cast(
            alarminfo_pointer, POINTER(NET_DVR_VIDEO_INTERCOM_EVENT)).contents
        if (alarminfo_upload_video_intercom_event.byEventType == VIDEO_INTERCOM_EVENT_EVENTTYPE_UNLOCK_LOG):  
    
            try:
                os.system("echo Door unlocked, trying to update: " + sensor_name_door)
                os.system("echo Unlocked door ID : " + str(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.wLockID))
                os.system("echo Unlocked door name : " + str(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.byLockName))
                os.system("echo Unlocked door namelist : " + str(list(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.byLockName)))
                os.system("echo Unlocked door type : " + str(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.byUnlockType))
                #data = json.dumps({'state': 'on'})
                data = json.dumps({'state': 'on', 'attributes': {'Unlock': str(list(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.byControlSrc)), 'DoorID' : str(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.wLockID) }})
                response = requests.post(url_states + sensor_name_door, headers=headers, data=data)
                time.sleep(2)
                data = json.dumps({'state': 'off', 'attributes': {'Unlock': str(list(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.byControlSrc)), 'DoorID' : str(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.wLockID) }})
                response = requests.post(url_states + sensor_name_door, headers=headers, data=data)                
            except:
                os.system("echo Sensor updating failed")        
            os.system("echo Unlocked by: " + str(list(alarminfo_upload_video_intercom_event.uEventInfo.struUnlockRecord.byControlSrc)))
        elif (alarminfo_upload_video_intercom_event.byEventType == VIDEO_INTERCOM_EVENT_EVENTTYPE_ILLEGAL_CARD_SWIPING_EVENT):
            os.system("echo Illegal card swiping")
        else:
            os.system("echo COMM_ALARM_VIDEO_INTERCOM, unhandled byEventType: " + str(alarminfo_upload_video_intercom_event.byEventType))
    else:
        os.system("echo Unhandled command: " + str(command))

def set_attribute(sensor_name, attribute, value):
    response = requests.get(url_states + sensor_name, headers=headers)
    msg = json.loads(response.text)
    msg['attributes'][attribute] = value
    payload = json.dumps({'state':  msg['state'], 'attributes': msg['attributes']})
    requests.post(url_states + sensor_name, headers=headers, data=payload)   

os.system("echo Hikvision SDK Add-on started! Listening for events...")  

# VARIABLES 
with open("/data/options.json") as fd:
    config = json.load(fd)

headers = {
    'Authorization': 'Bearer ' + config["bearer"],
    'content-type': 'application/json',
}
url_states = config["url_states"]
sensor_name_door = "sensor." + config["sensor_door"]
sensor_name_callstatus = "sensor."  + config["sensor_callstatus"]
sensor_name_motion = "sensor."  + config["sensor_motion"]
   
HCNetSDK.NET_DVR_Init()
HCNetSDK.NET_DVR_SetValidIP(0, True)

device_info = NET_DVR_DEVICEINFO_V30()
user_id = HCNetSDK.NET_DVR_Login_V30(config["ip"].encode('utf-8'), 8000, config["username"].encode('utf-8'), config["password"].encode('utf-8'), device_info)


if (user_id < 0):
    os.system("echo NET_DVR_Login_V30 failed, error code = " + str(HCNetSDK.NET_DVR_GetLastError()))
    HCNetSDK.NET_DVR_Cleanup()
    exit(1)

alarm_param = NET_DVR_SETUPALARM_PARAM()
alarm_param.dwSize = 20
alarm_param.byLevel = 1
alarm_param.byAlarmInfoType = 1
alarm_param.byFaceAlarmDetection = 1

alarm_handle = HCNetSDK.NET_DVR_SetupAlarmChan_V41(user_id, alarm_param)

if (alarm_handle < 0):
    os.system("echo NET_DVR_SetupAlarmChan_V41 failed, error code = " + str(HCNetSDK.NET_DVR_GetLastError()))
    HCNetSDK.NET_DVR_Logout_V30(user_id)
    HCNetSDK.NET_DVR_Cleanup()
    exit(2)
    

message_callback = fMessageCallBack(callback)
HCNetSDK.NET_DVR_SetDVRMessageCallBack_V50(0, message_callback, user_id)

def unlock_door(lockID):
    gw = NET_DVR_CONTROL_GATEWAY()
    gw.dwSize = sizeof(NET_DVR_CONTROL_GATEWAY)
    gw.dwGatewayIndex = 1
    gw.byCommand = 1 # opening command
    gw.byLockType = 0 # this is normal lock not smart lock
    gw.wLockID = lockID # door station
    gw.byControlSrc = (c_byte * 32)(*[97,98,99,100]) # anything will do but can't be empty
    gw.byControlType = 1

    result = HCNetSDK.NET_DVR_RemoteControl(user_id, 16009, byref(gw), gw.dwSize)
    os.system("echo Door: " + str(lockID + 1) + " unlocked by SDK!") 

#def NET_DVR_CaptureJPEGPicture():
#    sJpegPicFileName = b'test.jpg'
#    lpJpegPara = NET_DVR_JPEGPARA()
#    lpJpegPara.wPicSize = 2
#    lpJpegPara.wPicQuality = 1
#    res = HCNetSDK.NET_DVR_CaptureJPEGPicture(user_id, 1, byref(lpJpegPara), sJpegPicFileName)
#    if res == False:
#        os.system("Success")
#    else:
#        os.system("Grab stream fail")
        
for line in sys.stdin:
    if "unlock1" in line:
        os.system("echo Trying to unlock door 1... Stdin message: " + str(line))
        unlock_door(0)
    elif "unlock2" in line:
        os.system("echo Trying to unlock door 2... Stdin message: " + str(line))
        unlock_door(1)
 #   elif "image" in line:
 #       os.system("echo Trying to grab an image... Stdin message: " + str(line))
 #       NET_DVR_CaptureJPEGPicture()        
    else:
       os.system("echo Use input: unlock1 OR unlock2...  Stdin message: " + str(line))        

HCNetSDK.NET_DVR_CloseAlarmChan_V30(alarm_handle)
HCNetSDK.NET_DVR_Logout_V30(user_id)
HCNetSDK.NET_DVR_Cleanup()
