from hcnetsdk import HCNetSDK, NET_DVR_DEVICEINFO_V30, NET_DVR_DEVICEINFO_V30, NET_DVR_XML_CONFIG_INPUT, NET_DVR_XML_CONFIG_OUTPUT
from ctypes import c_byte, sizeof, byref, c_char, memmove, cast, c_void_p, POINTER
import sys

HCNetSDK.NET_DVR_Init()
HCNetSDK.NET_DVR_SetValidIP(0, True)


# For 8003 owners, send callsignal to indoor station!!!!
user_id = HCNetSDK.NET_DVR_Login_V30( "192.168.0.71".encode('utf-8'), 8000, "admin".encode('utf-8'), "XXX".encode('utf-8'))
  
if (user_id < 0):
    print(
        f"NET_DVR_Login_V30 failed, error code = {HCNetSDK.NET_DVR_GetLastError()}")
    HCNetSDK.NET_DVR_Cleanup()
    exit(1)

#inUrl = "GET /ISAPI/VideoIntercom/callSignal/capabilities?format=json"
#inPutBuffer = ""
# RESULTS :  ["answer", "reject", "bellTimeout", "hangUp", "deviceOnCall"]

inUrl = "PUT /ISAPI/VideoIntercom/callSignal?format=json"
inPutBuffer = "{\"CallSignal\":{\"cmdType\":\"reject\"}}"

#optional , but not needed??
#inPutBuffer = "{\"CallSignal\":{\"cmdType\":\"reject\",\"periodNumber\": 1,\"buildingNumber\": 1,\"unitNumber\": 1,\"floorNumber\": 0,\"roomNumber\": 1,\"unitType\": \"villa\",\"coderType\":\"ezviz\", \"model\": 1}}"
#inPutBuffer = "{\"CallSignal\":{\"cmdType\":\"reject\",\"src\":{\"periodNumber\":1,\"buildingNumber\":1,\"unitNumber\":1,\"floorNumber\":0,\"roomNumber\":1}}}"

#optional , but not needed??
#inUrl = "DELETE /ISAPI/VideoIntercom/ring"
#inPutBuffer = ""
                    
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

#print(result)
#print(pBuffer.value)
print(pszGetOutput.value.decode("utf-8") )

if result == 0:
    print(HCNetSDK.NET_DVR_GetLastError())

HCNetSDK.NET_DVR_Logout_V30(user_id)
HCNetSDK.NET_DVR_Cleanup()
