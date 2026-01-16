from ctypes import CDLL, CFUNCTYPE, POINTER, byref, c_byte, c_char, c_char_p, c_ulong, c_int, c_uint, c_void_p, c_long, create_string_buffer, pointer, sizeof, cast
from enum import IntEnum
import re
import json
import os
from datetime import datetime
from typing import Callable, Optional
from loguru import logger
from config import AppConfig
from sdk.hcnetsdk import BOOL, BYTE, DWORD, NET_DVR_CALL_STATUS, NET_DVR_JPEGPARA, NET_DVR_CLIENTINFO, NET_DVR_VIDEO_CALL_PARAM, NET_DVR_CONTROL_GATEWAY, NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM_V50,  DeviceAbilityType
from sdk.utils import SDKError, call_ISAPI
import xml.etree.ElementTree as ET


class DeviceType(IntEnum):
    OUTDOOR = 603
    INDOOR = 602
    VillaVTO = 605
    # K1T502 = 884 (unsupported)
    K1T671MF = 896
    K1T341AM = 10503
    DSKIT6Q = 10509
    K1T341M = 10510
    K1T341BM = 10515
    K1T343 = 10533
    K1T673 = 10534
    K1T342 = 10538
    K1T6QT = 10541
    K1T341 = 10542
    K1T321 = 10549
    K1T670 = 10552
    HD = 31
    AccessControlTerminal = 861

def sanitize_doorbell_name(doorbell_name: str) -> str:
    """Given a doorbell name, lowercase it and substitute whitespaces and `-` with `_`"""
    return re.sub(r"\s|-", "_", doorbell_name.lower())

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
    _previouse_audio_out_volume: str
    '''Used to unmute the doorbell by changing the audio out volume from 0 to the previouse value '''

    def __init__(self, id: int, config: AppConfig.Doorbell, sdk: CDLL):
        """
        Parameters:
            id: ID used internally to reference to this doorbell
        """
        logger.debug("Setting up doorbell: {}", config.name)
        self._sdk = sdk
        self._config = config
        self._id = id
        self._previouse_audio_out_volume = "5"

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

    def unlock_com(self, com_id: int):

        url = "/ISAPI/SecurityCP/control/outputs/" + str(com_id) + "?format=json"
        requestBody = {
            "OutputsCtrl": {
                "switch": "open"
            }
        }
        try:
            self._call_isapi("PUT", url, json.dumps(requestBody))
        except SDKError as err:
            # If error code is 10 (NET_DVR_NETWORK_RECV_TIMEOUT) suppress it,
            raise err
        logger.info(" Com {} unlocked by ISAPI", com_id +1)

    def lock_com(self, com_id: int):

        url = "/ISAPI/SecurityCP/control/outputs/" + str(com_id) + "?format=json"
        requestBody = {
            "OutputsCtrl": {
                "switch": "close"
            }
        }
        try:
            self._call_isapi("PUT", url, json.dumps(requestBody))
        except SDKError as err:
            # If error code is 10 (NET_DVR_NETWORK_RECV_TIMEOUT) suppress it,
            raise err
        logger.info(" Com {} locked by ISAPI", com_id +1)

    def unlock_door(self, lock_id: int):
        if not self._type is DeviceType.INDOOR:
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
        else:
                # ISAPI command for indoor
            url = "/ISAPI/AccessControl/RemoteControl/door/" + str(lock_id+1)
            requestBody = "<RemoteControlDoor><channelNo>1</channelNo><cmd>open</cmd><controlType>monitor</controlType></RemoteControlDoor>"

            logger.debug("NET_DVR_RemoteControl failed with code {}, trying ISAPI", self._sdk.NET_DVR_GetLastError())
            self._call_isapi("PUT", url, requestBody)

        logger.info(" Door {} unlocked by SDK", lock_id + 1)

    def get_device_channels_info(self):
        """Get information about available channels"""
        if not hasattr(self, 'user_id') or self.user_id < 0:
            logger.error("Not logged in")
            return
        
        # Get device configuration to find channels
        device_info = NET_DVR_DEVICEINFO_V30()
        logger.info(f"Trying to retrieve channels")
        # First, get basic device info
        result = self._sdk.NET_DVR_GetDVRConfig(
            self.user_id,
            0,  # NET_DVR_GET_DEVICECFG
            0,
            byref(device_info),
            sizeof(device_info)
        )
        
        if result:
            logger.info(f"Device supports {device_info.byChanNum} analog channels")
            logger.info(f"Device supports {device_info.byIPChanNum} IP channels")
            logger.info(f"Device supports {device_info.byHighDChanNum} high-def channels")

    def take_snapshot(self):

        try:
            
            # APPROACH 1: Direct capture on most likely channels
            logger.info("Trying Approach 1: Direct capture on likely channels")
            priority_channels = [
                1,     # Sometimes main stream
                0,     # Device itself (usually no camera)
                2,     # Sometimes sub stream
                33,    # Most common for linked IP camera on indoor stations
                34,    # Secondary IP channel
                35,    # Tertiary IP channel
                99,    # Video intercom channel
                100,   # Extended channel
                200,   # Digital channel
                201,   # Digital channel
            ]
            
            # Different parameter combinations to try
            param_combinations = [
                #(0xFF, 1, 2*1024*1024),  # Original size, low quality, 2MB buffer
                (0xFF, 2, 1024*1024)   # Original size, medium quality, 1MB buffer
                #(2, 1, 512*1024),        # D1, low quality, 512KB buffer
                #(3, 2, 1024*1024),       # VGA, medium quality, 1MB buffer
            ]
            
            for channel in priority_channels:
                logger.info(f"Testing channel {channel}")
                
                for pic_size, quality, buffer_size in param_combinations:
                    logger.debug(f"  Params: size={pic_size}, quality={quality}, buffer={buffer_size}")
                    
                    # Try NET_DVR_CaptureJPEGPicture first
                    try:
                        jpeg_para = NET_DVR_JPEGPARA()
                        jpeg_para.wPicSize = pic_size
                        jpeg_para.wPicQuality = quality
                        
                        buffer = create_string_buffer(buffer_size)
                        size = c_ulong(0)
                        
                        result = self._sdk.NET_DVR_CaptureJPEGPicture(
                            self.user_id,
                            channel,
                            byref(jpeg_para),
                            buffer,
                            buffer_size,
                            byref(size)
                        )
                        
                        if result and size.value > 100:
                            image_data = buffer.raw[:size.value]
                            # Quick JPEG validation
                            if len(image_data) >= 2 and image_data[:2] == b'\xff\xd8':
                                filename = self._save_snapshot_result(image_data, channel, "direct")
                                logger.info(f"✓ SUCCESS Approach 1: Channel {channel}, {size.value} bytes")
                                return filename
                            
                    except Exception as e:
                        logger.debug(f"  NET_DVR_CaptureJPEGPicture failed: {e}")
                    
                    # Try NET_DVR_CaptureJPEGPicture_NEW if available
                    if hasattr(self._sdk, 'NET_DVR_CaptureJPEGPicture_NEW'):
                        try:
                            jpeg_para = NET_DVR_JPEGPARA()
                            jpeg_para.wPicSize = pic_size
                            jpeg_para.wPicQuality = quality
                            
                            buffer = create_string_buffer(buffer_size)
                            size = c_ulong(0)
                            
                            result = self._sdk.NET_DVR_CaptureJPEGPicture_NEW(
                                self.user_id,
                                channel,
                                byref(jpeg_para),
                                buffer,
                                buffer_size,
                                byref(size)
                            )
                            
                            if result and size.value > 100:
                                image_data = buffer.raw[:size.value]
                                if len(image_data) >= 2 and image_data[:2] == b'\xff\xd8':
                                    filename = self._save_snapshot_result(image_data, channel, "direct_new")
                                    logger.info(f"✓ SUCCESS Approach 1 (NEW): Channel {channel}, {size.value} bytes")
                                    return filename
                                
                        except Exception as e:
                            logger.debug(f"  NET_DVR_CaptureJPEGPicture_NEW failed: {e}")
            
            # APPROACH 2: Try to "wake up" camera with preview first
            logger.info("Approach 1 failed, trying Approach 2: Preview then capture")
            
            # Try starting a realplay to wake up the camera
            preview_handle = -1
            try:
                if hasattr(self._sdk, 'NET_DVR_RealPlay_V40'):
                    preview_info = NET_DVR_CLIENTINFO()
                    preview_info.hPlayWnd = 0  # No window
                    preview_info.lChannel = 33  # Try channel 33 for preview
                    preview_info.lLinkMode = 0  # TCP
                    preview_info.sMultiCastIP = None
                    
                    preview_handle = self._sdk.NET_DVR_RealPlay_V40(self.user_id, byref(preview_info), None, None, 0)
                    
                    if preview_handle >= 0:
                        logger.info(f"Preview started on handle {preview_handle}")
                        
                        # Wait for camera to initialize
                        import time
                        time.sleep(3)
                        
                        # Now try capture again
                        for channel in [33, 1, 2]:
                            for pic_size, quality, buffer_size in [(0xFF, 1, 2*1024*1024), (2, 1, 1024*1024)]:
                                try:
                                    jpeg_para = NET_DVR_JPEGPARA()
                                    jpeg_para.wPicSize = pic_size
                                    jpeg_para.wPicQuality = quality
                                    
                                    buffer = create_string_buffer(buffer_size)
                                    size = c_ulong(0)
                                    
                                    result = self._sdk.NET_DVR_CaptureJPEGPicture(
                                        self.user_id,
                                        channel,
                                        byref(jpeg_para),
                                        buffer,
                                        buffer_size,
                                        byref(size)
                                    )
                                    
                                    if result and size.value > 100:
                                        image_data = buffer.raw[:size.value]
                                        if len(image_data) >= 2 and image_data[:2] == b'\xff\xd8':
                                            filename = self._save_snapshot_result(image_data, channel, "preview_wake")
                                            logger.info(f"✓ SUCCESS Approach 2: Channel {channel} after preview")
                                            
                                            # Stop preview
                                            self._sdk.NET_DVR_StopRealPlay(preview_handle)
                                            return filename
                                            
                                except Exception as e:
                                    logger.debug(f"  Capture after preview failed: {e}")
                        
                        # Stop preview if we started it
                        self._sdk.NET_DVR_StopRealPlay(preview_handle)
                        
            except Exception as e:
                logger.debug(f"Preview approach failed: {e}")
                if preview_handle >= 0:
                    try:
                        self._sdk.NET_DVR_StopRealPlay(preview_handle)
                    except:
                        pass
            
            # APPROACH 3: Try capture from preview handle (different method)
            logger.info("Approach 2 failed, trying Approach 3: Capture from preview handle")
            
            try:
                if hasattr(self._sdk, 'NET_DVR_RealPlay_V40') and hasattr(self._sdk, 'NET_DVR_CapturePicture'):
                    preview_info = NET_DVR_CLIENTINFO()
                    preview_info.hPlayWnd = 0
                    preview_info.lChannel = 33
                    preview_info.lLinkMode = 0
                    preview_info.sMultiCastIP = None
                    
                    preview_handle = self._sdk.NET_DVR_RealPlay_V40(self.user_id, byref(preview_info), None, None, 0)
                    
                    if preview_handle >= 0:
                        logger.info(f"Preview handle: {preview_handle}")
                        time.sleep(2)  # Wait for stream
                        
                        # Try capture from the preview handle
                        buffer = create_string_buffer(2 * 1024 * 1024)
                        size = c_ulong(0)
                        
                        result = self._sdk.NET_DVR_CapturePicture(preview_handle, buffer, 2*1024*1024, byref(size))
                        
                        if result and size.value > 100:
                            image_data = buffer.raw[:size.value]
                            if len(image_data) >= 2 and image_data[:2] == b'\xff\xd8':
                                filename = self._save_snapshot_result(image_data, 33, "preview_capture")
                                logger.info(f"✓ SUCCESS Approach 3: Capture from preview handle, {size.value} bytes")
                                
                                self._sdk.NET_DVR_StopRealPlay(preview_handle)
                                return filename
                        
                        self._sdk.NET_DVR_StopRealPlay(preview_handle)
                        
            except Exception as e:
                logger.debug(f"Preview capture approach failed: {e}")
            
            logger.error("All snapshot approaches failed")
            
            return None
            
        except Exception as e:
            logger.error(f"Exception in take_snapshot_alternative: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def _save_snapshot_result(self, image_data, channel, method):
        """Helper to save snapshot result"""
        try:
            # Create filename with timestamp and details
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = re.sub(r'\s+', '_', self._config.name.lower())
            
            # Determine base path
            base_path = "/media" if os.path.isdir("/media") else os.path.expanduser("~")
            output_dir = os.path.join(base_path, folder_name)
            os.makedirs(output_dir, exist_ok=True)
            
            filename = os.path.join(output_dir, f"snapshot_{timestamp}_ch{channel}_{method}.jpg")
            
            with open(filename, "wb") as f:
                f.write(image_data)
            
            logger.info(f"Snapshot saved: {filename} ({len(image_data)} bytes)")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            # Fallback to temp directory
            try:
                temp_file = f"/tmp/snapshot_{timestamp}_ch{channel}.jpg"
                with open(temp_file, "wb") as f:
                    f.write(image_data)
                return temp_file
            except:
                return None


    def callsignal(self, cmd_type: int):
        """ Answer the specified door using the NET_DVR_VIDEO_CALL_PARAM.
            command type: 0- Request call, 1- cancel call, 2- answer the call, 3- refuse the call, 4- called timeout, 5- end the call, 6- the device is busy, 7- the device is busy. 
        """
        gw = NET_DVR_VIDEO_CALL_PARAM()
        gw.dwSize = sizeof(NET_DVR_VIDEO_CALL_PARAM)
        gw.dwCmdType = cmd_type
        #gw.wUnitNumber = 1
        gw.byRes = (c_byte * 115)()

        result = self._sdk.NET_DVR_SetDVRConfig(self.user_id, 16036, 1, byref(gw),255)
        if not result:
            raise SDKError(self._sdk, "Error while calling NET_DVR_VIDEO_CALL_PARAM")
        logger.info("Callsignal {} sended with SDK", cmd_type)
        
        
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

    def get_num_outputs_indoor(self) -> int:
        """
        Get the number of output relays configured for the indoor station
        """

        def user_config() -> int:
            if self._config.output_relays is not None:
                logger.debug("Using the configured number of switches: {}", self._config.output_relays)
                return self._config.output_relays
            logger.debug("No manual config found to define output relays for indoor")
            raise RuntimeError("No user configuration specified")

        def isapi_door_capabilities() -> int:
            io_doors_xml = self._call_isapi("GET", "/ISAPI/AccessControl/RemoteControl/door/capabilities")
            try:
                root = ET.fromstring(io_doors_xml)
                door_number_element = root.find('{*}channelNo')
                if door_number_element is None or door_number_element.text is None:
                    # Print a string representation of the response XML
                    logger.debug("No door relays found for the indoor device")
                    raise RuntimeError(f'Unexpected XML response: {io_doors_xml}')
                logger.debug("We have found {} door relays for the indoor device", door_number_element.text)
                return int(door_number_element.text)
            except ET.ParseError:
                logger.debug("Error parsing: {}", io_doors_xml)
                raise RuntimeError("Error parsing: {}", io_doors_xml)

        # Define the list of available endpoints to try
        available_endpoints: list[Callable] = [user_config, isapi_door_capabilities]
        for endpoint in available_endpoints:
            # Invoke the endpoint, if it errors out try another one
            try:
                return endpoint()
            except RuntimeError:
                # This endpoint failed, try the next one
                pass

        # We have run out of available endpoints to call, dont ro a runtime error, just continue with 0 outputs
        logger.debug("Unable to get the number of doors on the indoor station, please configure the relays manually with this option in the config: output_relays")
        return 0
        #raise RuntimeError("Unable to get the number of doors, please configure the relays manually with this option in the config: output_relays")

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
            logger.debug("Response url for sdk_device_ability: {}", response_xml)

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
            if 'IOOutputPortList' not in root.tag or len(root) == 0:
                # XML does not contain the required tag
                raise RuntimeError(f'Unexpected XML response: {io_outputs_xml}')
            return len(root)

        def isapi_remote_control() -> int:
            door_capabilities_xml = self._call_isapi("GET", "/ISAPI/AccessControl/RemoteControl/door/capabilities")
            root = ET.fromstring(door_capabilities_xml)
            door_number_element = root.find('{*}doorNo')
            # Error out if we don't find attribute `max` inside the `doorNo` element
            if door_number_element is None or 'max' not in door_number_element.attrib:
                # Print a string representation of the response XML
                raise RuntimeError(f'Unexpected XML response: {door_capabilities_xml}')
            return int(door_number_element.attrib['max'])

        def isapi_device_info() -> int:
            electro_lock_xml = self._call_isapi("GET", "/ISAPI/System/deviceInfo")
            logger.debug("Response url for /ISAPI/System/deviceInfo: {}", electro_lock_xml)
            root = ET.fromstring(electro_lock_xml)
            electro_lock_xml_element = root.find('{*}electroLockNum')
            # Error out if we don't find `electroLockNum`
            if electro_lock_xml_element is None or electro_lock_xml_element.text is None:
                # Print a string representation of the response XML
                raise RuntimeError('Cannot find `electroLockNum` node in XML response')
            logger.debug("We have found {} electro locks for the outdoor device", electro_lock_xml_element.text)
            return int(electro_lock_xml_element.text)

        # Define the list of available endpoints to try
        available_endpoints: list[Callable] = [user_config, sdk_device_ability, isapi_io_outputs, isapi_remote_control, isapi_device_info]
        for endpoint in available_endpoints:
            # Invoke the endpoint, if it errors out try another one
            try:
                return endpoint()
            except RuntimeError:
                # This endpoint failed, try the next one
                pass
        # We have run out of available endpoints to call, dont ro a runtime error, just continue with 0 outputs
        logger.info("Unable to get the number of doors, please configure the relays manually with this option in the config: output_relays")
        return 0
        #raise RuntimeError("Unable to get the number of doors, please configure the relays manually with this option in the config: output_relays")

    def get_num_coms_indoor(self) -> int:
        """
        Get the number of com relays configured for this doorbell.
        We can also use this method: POST /ISAPI/SecurityCP/status/outputStatus?format=json {"OutputCond":{"maxResults":2,"outputModuleNo":0,"searchID":"1","searchResultPosition":0}}

        """

        def isapi_device_info() -> int:
            io_coms_xml = self._call_isapi("GET", "/ISAPI/System/deviceInfo")
            root = ET.fromstring(io_coms_xml)
            com_number_element = root.find('{*}alarmOutNum')
            # Error out if we don't find attribute `max` inside the `doorNo` element
            if com_number_element is None or com_number_element.text is None:
                # Print a string representation of the response XML
                raise RuntimeError('Cannot find `alarmOutNum` node in XML response')
            logger.debug("We have found {} com ports for the indoor device", com_number_element.text)
            return int(com_number_element.text)

        # Define the list of available endpoints to try
        available_endpoints: list[Callable] = [isapi_device_info]
        for endpoint in available_endpoints:
            # Invoke the endpoint, if it errors out try another one
            try:
                return endpoint()
            except RuntimeError:
                # This endpoint failed, try the next one
                pass

        # We have run out of available endpoints to call
        logger.debug("Unable to get the number of coms for the indoor station")
        return 0
        #raise RuntimeError("Unable to get the number of coms")

    def get_device_info(self):
        """Retrieve device information (model, sw version, etc) using the ISAPI endpoint.
        Return the parsed XML document"""
        xml_string = self._call_isapi("GET", "/ISAPI/System/deviceInfo")
        return ET.fromstring(xml_string)

    def get_audio_out_settings(self):
        """Retrieve audio output seetings of channel 1 (volume of the output and talk volume) using the ISAPI endpoint.
        Return the parsed XML document"""
        xml_string = self._call_isapi("GET", "/ISAPI/System/Audio/AudioOut/channels/1")
        return ET.fromstring(xml_string)

    def mute_audio_output(self):
        try:
            current_settings = self.get_audio_out_settings()
            currentTalkVolume = current_settings.find('.//{*}talkVolume')
            if currentTalkVolume is None or currentTalkVolume.text is None:
                talkVolume = "7"
                logger.debug("Current talk volume not found, using 7 as default")
            else:
                talkVolume = currentTalkVolume.text
                logger.debug("Current talk volume found: {}", talkVolume)

            currentVolume = current_settings.find('.//{*}volume')
            if currentVolume is None or currentVolume.text is None or currentVolume.text == "0":
                self._previouse_audio_out_volume = 7
                logger.debug("Current volume not found, using 7 as default")
            else:
                # remember current audio out volume for the unmute of the doorbell
                self._previouse_audio_out_volume = int(currentVolume.text)
                logger.debug("Current volume found: {}", self._previouse_audio_out_volume)

        except SDKError:
            # Cannot get current audio out settings use default values
            talkVolume = "7"
            self._previouse_audio_out_volume = "7"

        url = "/ISAPI/System/Audio/AudioOut/channels/1"
        # mute audio out by changing the audio out volume to 0
        requestBody = """<AudioOut><id>1</id><AudioOutVolumelist><AudioOutVlome><type>audioOutput</type>
                         <volume>0</volume><talkVolume>{}</talkVolume>
                         </AudioOutVlome></AudioOutVolumelist></AudioOut>""".format(talkVolume)

        self._call_isapi("PUT", url, requestBody)

    def unmute_audio_output(self):
        try:
            current_settings = self.get_audio_out_settings()
            currentTalkVolume = current_settings.find('.//{*}talkVolume')
            if currentTalkVolume is None or currentTalkVolume.text is None:
                talkVolume = "7"
                logger.debug("Current talk volume not found, using 7 as default")
            else:
                talkVolume = currentTalkVolume.text
                logger.debug("Current talk volume found: {}", talkVolume)
        except SDKError:
            # Cannot get current audio out settings use default values
            talkVolume = "7"

        url = "/ISAPI/System/Audio/AudioOut/channels/1"

        # unmute audio out by changing the audio out volume back to the previouse volume
        requestBody = """<AudioOut><id>1</id><AudioOutVolumelist><AudioOutVlome><type>audioOutput</type>
                         <volume>{}</volume><talkVolume>{}</talkVolume>
                         </AudioOutVlome></AudioOutVolumelist></AudioOut>""".format(self._previouse_audio_out_volume, talkVolume)

        self._call_isapi("PUT", url, requestBody)

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
