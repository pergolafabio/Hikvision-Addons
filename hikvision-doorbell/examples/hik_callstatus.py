from ctypes import byref, sizeof

from sdk.hcnetsdk import (NET_DVR_CALL_STATUS, NET_DVR_DEVICEINFO_V30,
                          NET_DVR_VIDEO_CALL_PARAM)
from sdk.utils import loadSDK

# NET_DVR_GET_CALL_STATUS                  16034  
# NET_DVR_SET_CALL_SIGNAL                  16036  
HCNetSDK = loadSDK()
HCNetSDK.NET_DVR_Init()
HCNetSDK.NET_DVR_SetValidIP(0, True)

device_info = NET_DVR_DEVICEINFO_V30()

user_id = HCNetSDK.NET_DVR_Login_V30( "192.168.0.70".encode('utf-8'), 8000, "admin".encode('utf-8'), "XXXX".encode('utf-8'), device_info)

if (user_id < 0):
    print(
        f"NET_DVR_Login_V30 failed, error code = {HCNetSDK.NET_DVR_GetLastError()}")
    HCNetSDK.NET_DVR_Cleanup()
    exit(1)
    
###### Callsignal
    
struCallSignal = NET_DVR_VIDEO_CALL_PARAM()
struCallSignal.dwSize = sizeof(NET_DVR_VIDEO_CALL_PARAM)
struCallSignal.dwCmdType = 3
struCallSignal.wUnitNumber = 1

result = HCNetSDK.NET_DVR_SetDVRConfig(user_id, 16036, 1, struCallSignal)
print("callsignal", result)
if result == 0:
    print(HCNetSDK.NET_DVR_GetLastError())
    
##### Callstatus     
struCallStatus = NET_DVR_CALL_STATUS()
struCallStatus.dwSize = sizeof(NET_DVR_CALL_STATUS)

#result = HCNetSDK.NET_DVR_GetDeviceStatus(user_id, 16034, None, struCallStatus)
result = HCNetSDK.NET_DVR_GetDeviceStatus(user_id, 16034, 1, None, None, byref(struCallStatus), struCallStatus.dwSize)

print("callstatus", result)
if result == 0:
    print(HCNetSDK.NET_DVR_GetLastError())
        
    
    


HCNetSDK.NET_DVR_Logout_V30(user_id)
HCNetSDK.NET_DVR_Cleanup()
