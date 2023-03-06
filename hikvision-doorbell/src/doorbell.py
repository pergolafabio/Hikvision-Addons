from ctypes import CDLL, byref, c_byte, c_char, c_char_p, c_void_p, sizeof, cast
from enum import IntEnum
import re
from typing import Optional
from loguru import logger
from config import AppConfig
from sdk.hcnetsdk import NET_DVR_CONTROL_GATEWAY, NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM_V50, NET_DVR_XML_CONFIG_INPUT, NET_DVR_XML_CONFIG_OUTPUT
from sdk.utils import SDKError


class DeviceType(IntEnum):
    OUTDOOR = 603
    INDOOR = 602
    VillaVTO = 605
    FaceAccessTerminal = 10510


class Doorbell():
    """A doorbell device.

    This object manages a connection with the Hikvision door station.
    Call `authenticate` to login in the device, then `setup_alarm` to configure the doorbell to stream back events.

    Call `logout` when you want to stop receiving events.
    """
    user_id: int
    '''Provided by the SDK after login'''
    _id: int
    '''Used internally to distinguish between multiple doorbells'''
    _type: DeviceType
    _device_info: NET_DVR_DEVICEINFO_V30
    '''Populated after authenticate method is invoked'''

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
            raise SDKError(self._sdk, f"Error while logging into {self._config.name}")

        try:
            self._type = DeviceType(self._device_info.wDevType)
        except KeyError:
            logger.warning("Unknown device type: {}", self._device_info.wDevType)

        logger.debug("Login returned user ID: {}", self.user_id)
        logger.debug("Doorbell serial number: {}, device type: {}",
                     self._device_info.serialNumber(), self._type.name)
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
            raise SDKError(self._sdk, f"Error while listening to events in {self._config.name}")

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

        result = self._sdk.NET_DVR_RemoteControl(self.user_id, 16009, byref(gw), gw.dwSize)
        if not result:
            raise SDKError(self._sdk, "Error while invoking NET_DVR_RemoteControl API")

        logger.info(" Door {} unlocked by SDK", lock_id + 1)

    def reboot_device(self):
        # We know that the SDK gives error when rebooting since it cannot contact the device, raising error code 10
        try:
            self._call_isapi("PUT", "/ISAPI/System/reboot")
        except SDKError as err:
            # If error code is 10 (NET_DVR_NETWORK_RECV_TIMEOUT) suppress it,
            error_code = err.args[1]
            if error_code != 10:
                # It is another kind of error, thrown it
                raise err

    def _call_isapi(self, http_method: str, url: str, requestBody: str = "") -> str:
        """Call the ISAPI endpoints using the SDK.
        
        Args:
            http_method: HTTP method to use (e.g. GET, POST, PUT)
            url: The URL to invoke. Must start with `/ISAPI`
            requestBody: optional request body
        Returns:
            str: The response message as a string
        """
        # Build the HTTP request string
        # e.g.: `GET /ISAPI/System/IO/outputs`
        inUrl = f"{http_method} {url}"

        logger.debug("Request body: {}", requestBody)

        # Input information
        inputStruct = NET_DVR_XML_CONFIG_INPUT()

        urlSize = (c_char * 256)()

        requestUrlBuffer = bytes(inUrl, "ascii")
        inputStruct.lpRequestUrl = cast(c_char_p(requestUrlBuffer), c_void_p)
        inputStruct.dwRequestUrlLen = len(urlSize)

        inputBuffer = bytes(requestBody, "ascii")

        inputStruct.lpInBuffer = cast(c_char_p(inputBuffer), c_void_p)
        inputStruct.dwInBufferSize = len(inputBuffer)

        inputStruct.dwSize = sizeof(inputStruct)

        # Output information
        outputStruct = NET_DVR_XML_CONFIG_OUTPUT()
        outputBufferSize = 1024 * 1024
        responseStatusBuffer = (c_char * outputBufferSize)()
        outputStruct.lpStatusBuffer = cast(responseStatusBuffer, c_void_p)
        outputStruct.dwStatusSize = outputBufferSize

        outputSize = (1024 * 1024)
        outputBuffer = (c_char * outputSize)()

        outputStruct.lpOutBuffer = cast(outputBuffer, c_void_p)
        outputStruct.dwOutBufferSize = outputSize
        outputStruct.dwSize = sizeof(outputStruct)

        # Invoke the ISAPI API
        result = self._sdk.NET_DVR_STDXMLConfig(self.user_id, inputStruct, outputStruct)

        if not result:
            # The response status is populated only in case of error
            logger.debug("Response status: {}", responseStatusBuffer.value.decode("utf-8"))
            logger.error("SDK error: {}", self._sdk.NET_DVR_GetLastError())
            raise SDKError(self._sdk, "Error while calling ISAPI endpoint")
        
        logger.debug("Response output: {}", outputBuffer.value.decode("utf-8"))

        return outputBuffer.value.decode("utf-8")

    def __del__(self):
        self.logout()


class Registry(dict[int, Doorbell]):

    def getBySerialNumber(self, serial: str) -> Optional[Doorbell]:
        for _, doorbell in self.items():
            if serial in doorbell._device_info.serialNumber():
                return doorbell

    def getFirstIndoor(self) -> Optional[Doorbell]:
        """Return the first indoor unit, if found in the registry"""
        for _, doorbell in self.items():
            if doorbell._type is DeviceType.INDOOR:
                return doorbell

    def getByName(self, name: str) -> Optional[Doorbell]:
        """Return the unit based on the input name, if found in the registry.
        The name is matched against the lowercase version with underscore instead of spaces"""
        for _, doorbell in self.items():
            # Lowercase the name, then substitute any whitespace with _
            sanitized_name = re.sub(r'\s', '_', doorbell._config.name.lower())
            if sanitized_name == name:
                return doorbell
