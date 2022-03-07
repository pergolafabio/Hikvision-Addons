from hcnetsdk import HCNetSDK, NET_DVR_DEVICEINFO_V30, NET_DVR_DEVICEINFO_V30, NET_DVR_CONTROL_GATEWAY
from ctypes import c_byte, sizeof, byref
import sys


HCNetSDK.NET_DVR_Init()
HCNetSDK.NET_DVR_SetValidIP(0, True)

device_info = NET_DVR_DEVICEINFO_V30()

# user_id = HCNetSDK.NET_DVR_Login_V30( "192.168.0.1".encode('utf-8'), 8000, "admin".encode('utf-8'), "pass12345".encode('utf-8'), device_info)
user_id = HCNetSDK.NET_DVR_Login_V30( sys.argv[1].encode('utf-8'), 8000, sys.argv[2].encode('utf-8'), sys.argv[3].encode('utf-8'), device_info)

if (user_id < 0):
    print(
        f"NET_DVR_Login_V30 failed, error code = {HCNetSDK.NET_DVR_GetLastError()}")
    HCNetSDK.NET_DVR_Cleanup()
    exit(1)


gw = NET_DVR_CONTROL_GATEWAY()
gw.dwSize = sizeof(NET_DVR_CONTROL_GATEWAY)
gw.dwGatewayIndex = 1
gw.byCommand = 1 # opening command
gw.byLockType = 0 # this is normal lock not smart lock
gw.wLockID = 0 # door station
gw.byControlSrc = (c_byte * 32)(*[97,98,99,100]) # anything will do but can't be empty
gw.byControlType = 1

print(gw.dwSize)
result = HCNetSDK.NET_DVR_RemoteControl(user_id, 16009, byref(gw), gw.dwSize)

print("unlockreusult", result)
if result == 0:
    print(HCNetSDK.NET_DVR_GetLastError())

HCNetSDK.NET_DVR_Logout_V30(user_id)
HCNetSDK.NET_DVR_Cleanup()
