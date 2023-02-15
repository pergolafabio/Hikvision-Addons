from ctypes import CDLL, c_byte, c_char, c_char_p, c_void_p, sizeof, cast
import json
from loguru import logger
from config import AppConfig
from sdk.hcnetsdk import NET_DVR_CONTROL_GATEWAY, NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM_V50, NET_DVR_XML_CONFIG_INPUT, NET_DVR_XML_CONFIG_OUTPUT


class Doorbell():
    """A doorbell device.

    This object manages a connection with the Hikvision door station.
    Call `authenticate` to login in the device, then `setup_alarm` to configure the doorbell to stream back events.

    Call `logout` when you want to stop receiving events.
    """
    user_id: int
    '''Provided by the SDK after login'''

    def __init__(self, id: int, config: AppConfig.Doorbell, sdk: CDLL):
        """
        Parameters:
            id: ID used internally to reference to this doorbell
        """
        logger.debug("Setting up doorbell: {}", config.name)
        self._sdk = sdk
        self._config = config
        self._id = id

    def authenticate(self):
        '''Authenticate with the remote doorbell'''
        logger.debug("Logging into doorbell")
        self._device_info = NET_DVR_DEVICEINFO_V30()
        self.user_id = self._sdk.NET_DVR_Login_V30(
            bytes(self._config.ip, 'utf8'),
            8000,
            bytes(self._config.username, 'utf8'),
            bytes(self._config.password, 'utf8'),
            self._device_info
        )
        if self.user_id < 0:
            # TODO raise exception
            raise RuntimeError(f"SDK error code {self._sdk.NET_DVR_GetLastError()}")

        logger.debug("Login returned user ID: {}", self.user_id)
        logger.debug("Doorbell serial number: {}, device type: {}",
                     self._device_info.serialNumber(), self._device_info.wDevType)
        logger.info("Connected to doorbell: {}", self._config.name)

    def setup_alarm(self):
        '''Receive events from the doorbell. authenticate() must be called first.'''
        alarm_param = NET_DVR_SETUPALARM_PARAM_V50()
        alarm_param.dwSize = sizeof(NET_DVR_SETUPALARM_PARAM_V50)
        alarm_param.byLevel = 1
        alarm_param.byAlarmInfoType = 1
        alarm_param.byFaceAlarmmDetection = 1

        logger.debug("Arming the device via SDK")
        alarm_handle = self._sdk.NET_DVR_SetupAlarmChan_V50(
            self.user_id, alarm_param, None, 0)
        if alarm_handle < 0:
            raise RuntimeError(f"Error code {self._sdk.NET_DVR_GetLastError()}")

    def logout(self):
        logout_result = self._sdk.NET_DVR_Logout_V30(self.user_id)
        if not logout_result:
            logger.debug("SDK logout result {}", logout_result)

    def unlock_door(self, lock_id: int):
        gw = NET_DVR_CONTROL_GATEWAY()
        gw.dwSize = sizeof(NET_DVR_CONTROL_GATEWAY)
        gw.dwGatewayIndex = 1
        gw.byCommand = 1  # opening command
        gw.byLockType = 0  # this is normal lock not smart lock
        gw.wLockID = lock_id  # door station
        gw.byControlSrc = (c_byte * 32)(*[97, 98, 99, 100])  # anything will do but can't be empty
        gw.byControlType = 1

        result = self._sdk.NET_DVR_RemoteControl(self.user_id, 16009, gw, gw.dwSize)
        if not result:
            raise RuntimeError(f"SDK returned error {self._sdk.NET_DVR_GetLastError()}")

        logger.info(" Door {} unlocked by SDK", lock_id + 1)

    def call_signal(self, command: str):
        inUrl = "PUT /ISAPI/VideoIntercom/callSignal?format=json"
        requestBody = {
            "CallSignal": {
                "cmdType": command
            }
        }
        logger.debug("Request body: {}", json.dumps(requestBody))

        # optional , but not needed??
        # inPutBuffer = "{\"CallSignal\":{\"cmdType\":\"reject\",\"periodNumber\": 1,\"buildingNumber\": 1,\"unitNumber\": 1,\"floorNumber\": 0,\"roomNumber\": 1,\"unitType\": \"villa\",\"coderType\":\"ezviz\", \"model\": 1}}"
        # inPutBuffer = "{\"CallSignal\":{\"cmdType\":\"reject\",\"src\":{\"periodNumber\":1,\"buildingNumber\":1,\"unitNumber\":1,\"floorNumber\":0,\"roomNumber\":1}}}"
        
        # Input information
        inputStruct = NET_DVR_XML_CONFIG_INPUT()

        szUrl = (c_char * 256)()

        csCommand = bytes(inUrl, "ascii")
        inputStruct.lpRequestUrl = cast(c_char_p(csCommand), c_void_p)
        inputStruct.dwRequestUrlLen = len(szUrl)

        m_csInputParam = bytes(json.dumps(requestBody), "ascii")
        
        inputStruct.lpInBuffer = cast(c_char_p(m_csInputParam), c_void_p)
        inputStruct.dwInBufferSize = len(m_csInputParam)

        inputStruct.dwSize = sizeof(inputStruct)
        
        # Output information
        outputStruct = NET_DVR_XML_CONFIG_OUTPUT()
        outputBufferLength = 1024 * 1024
        buffer_p = (c_char * outputBufferLength)()
        outputStruct.lpStatusBuffer = cast(buffer_p, c_void_p)
        outputStruct.dwStatusSize = outputBufferLength

        szGetOutput = (1024 * 1024)
        pszGetOutput = (c_char * szGetOutput)()

        outputStruct.lpOutBuffer = cast(pszGetOutput, c_void_p)
        outputStruct.dwOutBufferSize = szGetOutput
        outputStruct.dwSize = sizeof(outputStruct)

        # Invoke the device API
        result = self._sdk.NET_DVR_STDXMLConfig(self.user_id, inputStruct, outputStruct)

        logger.debug("Response buffer: {}", buffer_p.value.decode("utf-8"))
        logger.debug("Response output: size: {}, value: {}", outputStruct.dwReturnedXMLSize, pszGetOutput.value.decode("utf-8"))
        if not result:
            # print(HCNetSDK.NET_DVR_GetLastError())
            logger.error("Result error: {}", self._sdk.NET_DVR_GetLastError())

    def __del__(self):
        self.logout()


class Registry(dict[int, Doorbell]):

    def getBySerialNumber(self):
        # TODO
        pass
