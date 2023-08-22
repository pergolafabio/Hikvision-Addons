from ctypes import CDLL, CFUNCTYPE, POINTER, byref, c_byte, c_char, c_char_p, c_int, c_uint, c_void_p, pointer, sizeof, cast
from enum import IntEnum
import re
from typing import Callable, Optional
from loguru import logger
from config import AppConfig
from sdk.hcnetsdk import BOOL, BYTE, DWORD, NET_DVR_CALL_STATUS, NET_DVR_CONTROL_GATEWAY, NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM_V50,  DeviceAbilityType

from sdk.utils import SDKError, call_ISAPI
import xml.etree.ElementTree as ET


class DeviceType(IntEnum):
    OUTDOOR = 603
    INDOOR = 602
    VillaVTO = 605
    FaceAccessTerminal = 10510
    HD = 31
    AccessControlTerminal = 861


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
            self._config.port,
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
        alarm_param.byDeployType = 1

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
        """ Unlock the specified door using the SKD NET_DVR_RemoteControl.
        If that fails, fallback to ISAPI `/ISAPI/AccessControl/RemoteControl/door/`.

        See #83
        """
        gw = NET_DVR_CONTROL_GATEWAY()
        gw.dwSize = sizeof(NET_DVR_CONTROL_GATEWAY)
        gw.dwGatewayIndex = 1
        gw.byCommand = 1  # opening command
        gw.byLockType = 0  # this is normal lock not smart lock
        gw.wLockID = lock_id  # door ID
        gw.byControlSrc = (c_byte * 32)(*[97, 98, 99, 100])  # anything will do but can't be empty
        gw.byControlType = 1

        result = self._sdk.NET_DVR_RemoteControl(self.user_id, 16009, byref(gw), gw.dwSize)
        if not result:
            # SDK failed, try via ISAPI
            url = "/ISAPI/AccessControl/RemoteControl/door/" + str(lock_id+1)
            requestBody = "<RemoteControlDoor><cmd>open</cmd></RemoteControlDoor>"

            logger.debug("NET_DVR_RemoteControl failed with code {}, trying ISAPI", self._sdk.NET_DVR_GetLastError())
            self._call_isapi("PUT", url, requestBody)
   
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

        # Delegate actual call to helper function
        output = call_ISAPI(self._sdk, self.user_id, http_method, url, requestBody)
        outputBuffer = output.lpOutBuffer

        output_char_p = cast(outputBuffer, c_char_p)

        # If there is no response in output (it may have errored out) return empty string
        response_body = output_char_p.value.decode("utf-8") if output_char_p.value else ""

        return response_body

    def get_num_outputs(self) -> int:
        """
        Get the number of output relays configured for this doorbell.

        Use the following methods, and return the first one that succeeds:
        
        - Manual configuration by the user
        - SDK NET_DVR_GetDeviceAbility
        - /ISAPI/System/IO/outputs
        - /ISAPI/AccessControl/RemoteControl/door/capabilities

        """

        # Define various functions, each using a different method to gather this information
        def user_config() -> int:
            if self._config.output_relays is not None:
                logger.debug("Using the configured number of switches: {}", self._config.output_relays)
                return self._config.output_relays
            raise RuntimeError("No user configuration specified")

        def sdk_device_ability() -> int:
            """Use SDK method GetDeviceAbility"""
            output_buffer = (c_char * 4096)()
            result = self._sdk.NET_DVR_GetDeviceAbility(
                self.user_id,
                DeviceAbilityType.IP_VIEW_DEV_ABILITY,
                None,
                0,
                output_buffer,
                len(output_buffer)
            )
            if not result:
                raise SDKError(self._sdk, "Error while getting device ability")
            response_xml = output_buffer.value.decode('utf-8')

            # Parse the XML response
            response = ET.fromstring(response_xml)
            # Use XPath to find a node named `IOOutNo` having attribute `@max`
            ioout_element = response.find(".//IOOutNo[@max]")
            if ioout_element is None:
                raise RuntimeError('Cannot find `IOOutNo` node in XML response')
            return int(ioout_element.attrib['max'])

        def isapi_io_outputs() -> int:
            io_outputs_xml = self._call_isapi("GET", "/ISAPI/System/IO/outputs")

            root = ET.fromstring(io_outputs_xml)
            if 'IOOutputPortList' not in root.tag:
                # XML does not contain the required tag
                raise RuntimeError(f'Unexpected XML response: {io_outputs_xml}')
            return len(root)

        def isapi_remote_control() -> int:
            # Device does not support previous ISAPI endpoint, try another
            door_capabilities_xml = self._call_isapi("GET", "/ISAPI/AccessControl/RemoteControl/door/capabilities")
            root = ET.fromstring(door_capabilities_xml)

            door_number_element = root.find('{*}doorNo')

            # Error out if we don't find attribute `max` inside the `doorNo` element
            if door_number_element is None or 'max' not in door_number_element.attrib:
                # Print a string representation of the response XML
                raise RuntimeError(f'Unexpected XML response: {door_capabilities_xml}')

            return int(door_number_element.attrib['max'])

        # Define the list of available endpoints to try
        available_endpoints: list[Callable] = [user_config, sdk_device_ability, isapi_io_outputs, isapi_remote_control]
        for endpoint in available_endpoints:
            # Invoke the endpoint, if it errors out try another one
            try:
                return endpoint()
            except RuntimeError:
                # This endpoint failed, try the next one
                pass

        # We have run out of available endpoints to call
        raise RuntimeError("Unable to get the number of doors, please configure the relays manually with this option in the config: output_relays")

    def get_device_info(self):
        """Retrieve device information (model, sw version, etc) using the ISAPI endpoint.
        Return the parsed XML document"""
        xml_string = self._call_isapi("GET", "/ISAPI/System/deviceInfo")
        return ET.fromstring(xml_string)

    def get_call_status(self) -> int:
        """Get the current status of the call."""
        call_status = NET_DVR_CALL_STATUS()
        call_status.dwSize = sizeof(call_status)
        call_status.byRes = (c_byte * 127)()

        ip_status_list = (BYTE * 1)()
        result = self._sdk.NET_DVR_GetDeviceStatus(self.user_id, 16034, 1, None, 0, ip_status_list, byref(call_status), call_status.dwSize)

        if not result:
            raise SDKError(self._sdk, "Error while calling GetDeviceStatus")

        return call_status.byCallStatus

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
