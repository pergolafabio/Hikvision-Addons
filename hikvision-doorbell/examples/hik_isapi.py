from ctypes import byref, c_byte, c_char, c_void_p, cast, memmove, sizeof

from sdk.hcnetsdk import NET_DVR_DEVICEINFO_V30, NET_DVR_XML_CONFIG_INPUT, NET_DVR_XML_CONFIG_OUTPUT
from sdk.utils import loadSDK

# NET_DVR_GET_CALL_STATUS                  16034  
# NET_DVR_SET_CALL_SIGNAL                  16036  
HCNetSDK = loadSDK()
HCNetSDK.NET_DVR_Init()
HCNetSDK.NET_DVR_SetValidIP(0, True)

device_info = NET_DVR_DEVICEINFO_V30()

user_id = HCNetSDK.NET_DVR_Login_V30( "192.168.0.70".encode('utf-8'), 8000, "admin".encode('utf-8'), "XXX".encode('utf-8'), device_info)

if (user_id < 0):
    print(
        f"NET_DVR_Login_V30 failed, error code = {HCNetSDK.NET_DVR_GetLastError()}")
    HCNetSDK.NET_DVR_Cleanup()
    exit(1)

inUrl = "GET /ISAPI/VideoIntercom/callStatus?format=json"
#inUrl = "GET /ISAPI/VideoIntercom/callStatus?format=json&channelType=tripartitePlatform"
inPutBuffer = ""

#inUrl = "PUT /ISAPI/AccessControl/RemoteControl/door/1"
#inPutBuffer = "<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>"

szUrl = (c_char * 256)()
struInput = NET_DVR_XML_CONFIG_INPUT()
struOuput = NET_DVR_XML_CONFIG_OUTPUT()

struInput.dwSize=sizeof(struInput)
struOuput.dwSize=sizeof(struOuput)
dwBufferLen = 1024 * 1024
pBuffer = (c_char * dwBufferLen)()

szGetOutput = (1024 * 1024)
pszGetOutput = (c_char * szGetOutput)()

csCommand = bytes(inUrl, "ascii")
memmove(szUrl, csCommand, len(csCommand))
struInput.lpRequestUrl = cast(szUrl,c_void_p)
struInput.dwRequestUrlLen = len(szUrl)

m_csInputParam= bytes(inPutBuffer, "ascii")
dwInBufferLen = 1024 * 1024
pInBuffer=(c_byte * dwInBufferLen)()
memmove(pInBuffer, m_csInputParam, len(m_csInputParam))

struInput.lpInBuffer = cast(pInBuffer,c_void_p)
#struInput.lpInBuffer = None

struInput.dwInBufferSize = len(m_csInputParam)
#struInput.dwInBufferSize = 0

struOuput.lpStatusBuffer = cast(pBuffer,c_void_p)
struOuput.dwStatusSize = dwBufferLen

struOuput.lpOutBuffer = cast(pszGetOutput,c_void_p)
struOuput.dwOutBufferSize = szGetOutput

result = HCNetSDK.NET_DVR_STDXMLConfig(user_id, byref(struInput), byref(struOuput))

print(result)
print(pBuffer.value)
print(pszGetOutput.value)

if result == 0:
    print(HCNetSDK.NET_DVR_GetLastError())

HCNetSDK.NET_DVR_Logout_V30(user_id)
HCNetSDK.NET_DVR_Cleanup()
