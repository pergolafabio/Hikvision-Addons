from ctypes import CDLL, CFUNCTYPE, POINTER, byref, memset, memmove, c_byte, c_char, c_char_p, c_ulong, c_int, c_uint, c_void_p, c_long, create_string_buffer, pointer, sizeof, cast
from enum import IntEnum
import re
import unicodedata
import json
import os
import requests
from requests.auth import HTTPDigestAuth
from datetime import datetime, time
import time
from typing import Callable, Optional
from loguru import logger
from config import AppConfig
from sdk.hcnetsdk import BOOL, BYTE, DWORD, NET_DVR_VIDEO_INTERCOM_RELATEDEV_CFG, NET_DVR_CALL_STATUS, NET_DVR_JPEGPARA, NET_DVR_VIDEO_CALL_COND, NET_DVR_CLIENTINFO, NET_DVR_VIDEO_CALL_PARAM, NET_DVR_CONTROL_GATEWAY, NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM_V50, NET_DVR_VIDEO_INTERCOM_DEVICEID_CFG,  DeviceAbilityType
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

import re
import unicodedata

def sanitize_doorbell_name(doorbell_name: str) -> str:
    if not doorbell_name:
        return ""
    # Lowercase and normalize unicode
    name = doorbell_name.lower()
    name = unicodedata.normalize('NFD', name)
    # Strip everything except basic alphanumeric characters
    return "".join([c for c in name if c.isalnum()])

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

        '''
        # Add these for SIP chime functionality
        self.sip_call_id = f"doorbell_{id}_{datetime.now().strftime('%H%M%S')}"
        self.sip_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sip_sock.bind(("", 0)) # Bind to OS-assigned port
        '''
        
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
        logger.info("Connected to doorbell: {} type: {}", self._config.name, self._type.name)

    def setup_alarm(self):
        '''Receive events from the doorbell. authenticate() must be called first.'''

        alarm_param = NET_DVR_SETUPALARM_PARAM_V50()
        alarm_param.dwSize = sizeof(NET_DVR_SETUPALARM_PARAM_V50)
        alarm_param.byLevel = 1
        alarm_param.byAlarmInfoType = 1
        alarm_param.byFaceAlarmDetection = 1
        alarm_param.byDeployType = 1
        # This flips bit 1 to 0, telling the doorbell NOT to send the backlog.
        alarm_param.bySupport = alarm_param.bySupport & ~0x02

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

    def get_outdoor_ip(self) -> Optional[str]:
            """
            Retrieves the IP address of the linked Main Door Station.
            Command: 16006 (NET_DVR_GET_VIDEO_INTERCOM_RELATEDEV_CFG)
            """

            # 1. Initialize the structure
            config_struct = NET_DVR_VIDEO_INTERCOM_RELATEDEV_CFG()
            config_struct.dwSize = sizeof(NET_DVR_VIDEO_INTERCOM_RELATEDEV_CFG)
            lp_returned = c_ulong(0)
            
            # Command 16006: Related Device Config
            # Channel 0xFFFFFFFF: Required for this command
            result = self._sdk.NET_DVR_GetDVRConfig(
                self.user_id,
                16006, 
                0xFFFFFFFF,
                byref(config_struct),
                sizeof(config_struct),
                byref(lp_returned)
            )

            if not result:
                error_code = self._sdk.NET_DVR_GetLastError()
                logger.error("Failed to get intercom config. Error: {}", error_code)
                return None

            if config_struct.dwNum == 0:
                logger.warning("No related devices found for {}", self._config.name)
                return None

            # For an Indoor Station, we usually want the 'struOutdoorUnit' (Main Door Station)
            try:
                # Access the first linked device in the union
                raw_ip = config_struct.struuRelatedDev[0].struIndoorUnit.struOutdoorUnit.sIpV4
                ip_address = raw_ip.decode('ascii').strip('\x00')
                
                if not ip_address:
                    # Fallback: check the OutdoorUnit view of the union
                    raw_ip = config_struct.struuRelatedDev[0].struOutdoorUnit.struMainOutdoorUnit.sIpV4
                    ip_address = raw_ip.decode('ascii').strip('\x00')

                if ip_address:
                    logger.info("Found linked Door Station IP: {}", ip_address)
                    return ip_address
                
                return None
            except Exception as e:
                logger.error("Error parsing IP from related device union: {}", e)
                return None
    '''
    def get_intercom_sip_id(self) -> Optional[str]:
            """
            Retrieves the Video Intercom Device ID configuration and 
            generates the SIP number for Indoor Stations.
            """
            config_struct = NET_DVR_VIDEO_INTERCOM_DEVICEID_CFG()
            config_struct.dwSize = sizeof(config_struct)
            lp_returned = c_ulong(0)

            result = self._sdk.NET_DVR_GetDVRConfig(
                self.user_id,
                16001,
                0,
                byref(config_struct),
                sizeof(config_struct),
                byref(lp_returned)
            )

            if not result:
                logger.error("Failed to get Video Intercom Device ID. Error: {}", self._sdk.NET_DVR_GetLastError())
                return None

            # Ensure we are only processing Indoor Stations (Type 3)
            if config_struct.byUnitType != 3:
                logger.warning("Device is not an Indoor Station (Type: {})", config_struct.byUnitType)
                return None

            unit = config_struct.uVideoIntercomUnit.struIndoorUnit
            dev_idx = unit.wDevIndex

            # Generate SIP number based on device_index rules
            if dev_idx == 0:
                sip_number = "10010110001"
            else:
                # Generates format like 10000000001, 10000000002, etc.
                sip_number = f"1000000000{dev_idx}"

            data = {
                "type": "Indoor",
                "floor": unit.wFloorNumber,
                "room": unit.wRoomNumber,
                "device_index": dev_idx,
                "sip_number": sip_number
            }

            logger.debug("Indoor Station Data: {}", data)
            return sip_number
    '''

    def take_snapshot(self):

        # --- ISAPI HTTP BLOCK START ---

        filename = None
        # 1. Determine the correct IP to target
        target_ip = self._config.ip
        if self._type == DeviceType.INDOOR:
            logger.debug("Indoor station: resolving outdoor IP for direct ISAPI...")
            target_ip = self.get_outdoor_ip()
            logger.debug("Resolved outdoor IP for direct ISAPI: {}", target_ip)
        
        if target_ip:
            # 2. Try both Main (1) and Sub (101) channels
            for channel in [1, 101]:
                try:
                    url = f"http://{target_ip}/ISAPI/Streaming/channels/{channel}/picture?snapShotImageType=JPEG&videoResolutionWidth=1280&videoResolutionHeight=720&imageQuality=best"
                    ## ISAPI/Streaming/channels/1/picture?snapShotImageType=JPEG&videoResolutionWidth=1280&videoResolutionHeight=7206&imageQuality=best
                    # snapShotImageType picture format, only support JPEG now
                    # videoResolutionWidth videoResolutionHeight picture resolution, if not use this parameter, by default it’s 704*576. Supported resolution 1280*720 704*576 704*480 352*288 352*240 176*144 176*120
                    # imageQuality support best better normal general
                    logger.debug("Attempting direct ISAPI: {}", url)
                    
                    response = requests.get(
                        url, 
                        auth=HTTPDigestAuth(self._config.username, self._config.password),
                        timeout=5
                    )

                    if response.status_code == 200 and len(response.content) > 100:
                        if response.content.startswith(b'\xff\xd8'):
                            filename = self._save_snapshot_result(response.content)
                            logger.info("Snapshot captured via HTTP ISAPI on channel {}", channel)
                            break
                    else:
                        # This catches 404, 401, etc., which are NOT exceptions
                        logger.error("ISAPI channel {} returned status: {} (Length: {})", 
                                     channel, response.status_code, len(response.content))

                except Exception as e:
                    logger.debug("HTTP ISAPI failed for channel {}: {}", channel, e)

        # If HTTP succeeded, we can skip the rest of the logic
        if filename:
            self._notify_snapshot_update(filename)
            return filename
        # --- ISAPI HTTP BLOCK END ---

        target_user_id = self.user_id
        temp_user_id = -1

        try:
            # Step 1: Handle Indoor logic by logging into the linked Outdoor station
            if self._type == DeviceType.INDOOR:
                logger.info("Indoor station detected, fetching linked Outdoor IP for snapshot...")
                outdoor_ip = self.get_outdoor_ip()
                
                if not outdoor_ip:
                    logger.error("Could not find linked outdoor IP for {}", self._config.name)
                    return None
                
                # Create a temporary session for the outdoor station
                device_info = NET_DVR_DEVICEINFO_V30()
                temp_user_id = self._sdk.NET_DVR_Login_V30(
                    bytes(outdoor_ip, 'utf8'),
                    self._config.port,
                    bytes(self._config.username, 'utf8'),
                    bytes(self._config.password, 'utf8'),
                    device_info
                )

                if temp_user_id < 0:
                    logger.error("Failed to login to linked Outdoor station at {} Error {}", outdoor_ip, self._sdk.NET_DVR_GetLastError())
                    return None
                
                target_user_id = temp_user_id
                logger.debug("Temporary session established (ID: {}) for IP: {}", target_user_id, outdoor_ip)
            else:
                logger.debug("Direct snapshot for device type: {}", self._type.name)

            # Step 2: Capture Logic
            priority_channels = [1, 101]
            param_combinations = [
                (0xFF, 2, 2*1024*1024), # Try Max resolution first with a 2MB buffer
                (16, 2, 1024*1024)    # Fallback to 720p if Max fails
            ]

            
            filename = None
            for channel in priority_channels:
                if filename: 
                    break

                # NET_DVR_JPEGPARA Capture if ISAPI fails
                for pic_size, quality, buffer_size in param_combinations:
                    try:
                        logger.debug("Trying parameters {} on channel {}", (pic_size, quality, buffer_size), channel)
                        jpeg_para = NET_DVR_JPEGPARA()
                        jpeg_para.wPicSize = pic_size
                        jpeg_para.wPicQuality = quality
                        buffer = create_string_buffer(buffer_size)
                        size = c_ulong(0)
                        
                        result = self._sdk.NET_DVR_CaptureJPEGPicture_NEW(
                            target_user_id, 
                            channel,
                            byref(jpeg_para),
                            buffer,
                            buffer_size,
                            byref(size)
                        )
                        
                        if result and size.value > 100:
                            image_data = buffer.raw[:size.value]
                            if image_data.startswith(b'\xff\xd8'):
                                filename = self._save_snapshot_result(image_data)
                                break 
                    except Exception as e:
                        logger.debug("Capture attempt failed on channel {}: {}", channel, e)
                    if filename: break

            if filename:
                # Notify MQTT input to update image (if MQTT is set up)
                self._notify_snapshot_update(filename)

            return filename
            
        except Exception as e:
            logger.error("Exception in take_snapshot: {}", e)
            return None
        finally:
            # Step 3: Cleanup temporary session if it was created
            if temp_user_id >= 0:
                logger.debug("Logging out of temporary session {}", temp_user_id)
                self._sdk.NET_DVR_Logout_V30(temp_user_id)

    def _notify_snapshot_update(self, filename: str):
        """Notify that a new snapshot was taken"""
        # You'll need a way to access the MQTTInput instance
        # One option is to store a reference to it in the Doorbell class
        if hasattr(self, '_mqtt_input_ref'):
            self._mqtt_input_ref.update_snapshot_image(self, filename)

    def _save_snapshot_result(self, image_data,):
        """Helper to save snapshot result"""
        try:
            # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = re.sub(r'\s+', '_', self._config.name.lower())
            base_path = "/media" if os.path.isdir("/media") else os.path.expanduser("~")
            output_dir = os.path.join(base_path, folder_name)
            os.makedirs(output_dir, exist_ok=True)
            filename = os.path.join(output_dir, f"snapshot.jpg")
            with open(filename, "wb") as f:
                f.write(image_data)
            logger.info(f"Snapshot saved: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")

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

    def video_call_signal_process(self,dwDataType,pRecvDataBuffer,dwBufSize,pUserData):

        # STATUS
        if dwDataType == 0:
            if pRecvDataBuffer:
                try:
                    status = cast(pRecvDataBuffer,POINTER(DWORD)).contents.value
                    logger.info("STATUS VALUE: {}", status)
                except Exception as e:
                    logger.error("Error reading status: {}", e)
            else:
                logger.warning("STATUS: pRecvDataBuffer is NULL")

        # DATA
        elif dwDataType == 2:
            if pRecvDataBuffer:
                try:
                    # Try to cast to our structure
                    param = cast(pRecvDataBuffer, POINTER(NET_DVR_VIDEO_CALL_PARAM)).contents

                    messages = {
                        1: "Call cancelled",
                        3: "Call refused",
                        4: "Ring timeout",
                        6: "Other party busy",
                    }

                    if param.dwCmdType == 0:
                        logger.debug("*** THIS IS THE RING SIGNAL ***")
                    elif param.dwCmdType == 2:
                        logger.debug("Call answered signal received. Checking for custom call label audio...")
                        time.sleep(0.5)
                        self.start_voice_talk()
                        '''
                        # Read from the doorbell object
                        audio_path = getattr(self, '_custom_call_label', None)
                        
                        if audio_path and str(audio_path).strip():
                            clean_path = str(audio_path).strip()
                            logger.info("Using custom call label audio path: {}", clean_path)
                            self.start_voice_talk(audio_file_path=clean_path)
                        else:
                            logger.info("No custom call label text found. Just starting audio playback.")
                            self.start_voice_talk()
                        '''
                    elif param.dwCmdType == 5:
                        logger.debug("Call ended signal received.")
                        time.sleep(1)
                        self.stop_voice_talk()
                        time.sleep(1)
                        self.stop_call_to_device()
                    elif param.dwCmdType in messages:
                        logger.debug(messages[param.dwCmdType])
                        self.stop_call_to_device()
                    else:
                        logger.debug("Unknown CMD: {}", param.dwCmdType)
                        
                except Exception as e:
                    logger.error("Error parsing DATA structure: {}", e)
                    # Try to read raw bytes to see what we got
                    try:
                        if dwBufSize > 0 and dwBufSize <= 1024:
                            raw = bytearray(dwBufSize)
                            memmove(raw, pRecvDataBuffer, dwBufSize)
                            logger.debug("Raw bytes (first 4 bytes as DWORD): {}", int.from_bytes(raw[:4], 'little') if len(raw) >= 4 else "too short")
                    except Exception as e2:
                        logger.error("Could not read raw bytes: {}", e2)
            else:
                logger.warning("DATA: pRecvDataBuffer is NULL")
        else:
            logger.debug("Unknown dwDataType: {} (not 0 or 2)", dwDataType)

    def send_call_to_device(self,floor=1,room=1,building=1,unit=1,dev_index=0):

        try:
            if hasattr(self, 'config_handle'):
                logger.debug("cleaning up call sessions")
                self._sdk.NET_DVR_StopRemoteConfig(self.config_handle)
                self.config_handle = -1
                time.sleep(1)
        except:
            pass

        if not hasattr(self, "video_call_callback"):

            self.VIDEO_CALL_CALLBACK = CFUNCTYPE(None,DWORD,c_void_p,DWORD,c_void_p)
            self.video_call_callback = self.VIDEO_CALL_CALLBACK(self.video_call_signal_process)

        self.call_cond = NET_DVR_VIDEO_CALL_COND()
        memset(byref(self.call_cond),0,sizeof(self.call_cond))
        self.call_cond.dwSize = sizeof(self.call_cond)

        # Set byRequestType explicitly for extension
        # 0 = client initiates call, 1 = device initiates call
        # self.call_cond.byRequestType = 1

        # StartRemoteConfig
        self.config_handle = self._sdk.NET_DVR_StartRemoteConfig(self.user_id,16032,byref(self.call_cond),sizeof(self.call_cond),self.video_call_callback,None )

        if self.config_handle < 0:

            err = self._sdk.NET_DVR_GetLastError()
            raise SDKError(self._sdk, f"StartRemoteConfig failed: {err}")

        logger.debug("Call remote config started with handle: {}".format(self.config_handle))

        # ADD THIS DELAY - like waiting for user to click "Inquest"
        logger.debug("Waiting 1 seconds before sending call...")
        time.sleep(1) 

        # parameter
        self.call_param = NET_DVR_VIDEO_CALL_PARAM()
        memset(byref(self.call_param),0,sizeof(self.call_param))
        self.call_param.dwSize = sizeof(self.call_param)
        self.call_param.dwCmdType = 0
        self.call_param.wPeriod = 0
        self.call_param.wBuildingNumber = building
        self.call_param.wUnitNumber = unit
        self.call_param.wFloorNumber = floor
        self.call_param.wRoomNumber = room
        self.call_param.wDevIndex = dev_index
        self.call_param.byUnitType = 0

        logger.info("Sending call building={} unit={} floor={} room={}",building,unit,floor,room )

        result = self._sdk.NET_DVR_SendRemoteConfig(self.config_handle,0,byref(self.call_param),sizeof(self.call_param))

        if not result:

            err = self._sdk.NET_DVR_GetLastError()
            logger.error("SendRemoteConfig failed error={}", err)

            self._sdk.NET_DVR_StopRemoteConfig(self.config_handle)
            self.config_handle = -1

            raise SDKError(self._sdk,f"SendRemoteConfig failed: {err}")

        return True
    
    def stop_call_to_device(self):

        if self.config_handle < 0:
            return False

        self.call_param.dwCmdType = 1
        result = self._sdk.NET_DVR_SendRemoteConfig(self.config_handle, 0,byref(self.call_param),sizeof(self.call_param))
        logger.debug("NET_DVR_StopRemoteConfig command sent result={}", result)
        self._sdk.NET_DVR_StopRemoteConfig(self.config_handle)
        self.config_handle = -1
        return result

    def start_video_preview(self):
        if not hasattr(self, "real_play_handle") or self.real_play_handle < 0:
            # NET_DVR_CLIENTINFO structure configuration
            # In a headless Python add-on, hPlayWnd is typically None (0) because there is no local window handle
            stru_client_info = NET_DVR_CLIENTINFO()
            memset(byref(stru_client_info), 0, sizeof(stru_client_info))
            stru_client_info.hPlayWnd = 0  # No window handle needed for headless streaming/transcoding
            stru_client_info.lChannel = 1  # Intercom main channel
            stru_client_info.lLinkMode = 0 # 0: Main stream, 1: Sub stream
            stru_client_info.sMultiCastIP = None

            self.real_play_handle = self._sdk.NET_DVR_RealPlay_V30(
                self.user_id, byref(stru_client_info), None, None, True
            )
            
            if self.real_play_handle == -1:
                err = self._sdk.NET_DVR_GetLastError()
                logger.error("NET_DVR_RealPlay_V30 failed: {}", err)
            else:
                logger.info("NET_DVR_RealPlay_V30 succeeded, handle: {}", self.real_play_handle)

    def stop_video_preview(self):
        if hasattr(self, "real_play_handle") and self.real_play_handle >= 0:
            self._sdk.NET_DVR_StopRealPlay(self.real_play_handle)
            self.real_play_handle = -1
            logger.info("Video preview stopped.")

    def start_voice_talk(self,audio_file_path=None):
        if not hasattr(self, "voice_talk_handle") or self.voice_talk_handle < 0:
            self.voice_talk_handle = self._sdk.NET_DVR_StartVoiceCom_V30(
                self.user_id, 1, 0, None, None
            )
            if self.voice_talk_handle == -1:
                err = self._sdk.NET_DVR_GetLastError()
                logger.error("NET_DVR_StartVoiceCom_V30 failed: {}", err)
            else:
                logger.info("NET_DVR_StartVoiceCom_V30 succeeded, handle: {}", self.voice_talk_handle)
                # Start video right along with voice for a full video call , removed for now since it may not be needed and can cause issues with some devices
                # self.start_video_preview()

                # If an audio file is provided, start streaming it in a background thread
                if audio_file_path:
                    import threading
                    threading.Thread(
                        target=self._stream_audio_file, 
                        args=(audio_file_path,), 
                        daemon=True
                    ).start()

    def start_voice_forwarding(self, audio_file_path=None):
        if not hasattr(self, "voice_talk_handle") or self.voice_talk_handle < 0:
            self.voice_talk_handle = self._sdk.NET_DVR_StartVoiceCom_MR_V30(
                self.user_id, 1, None, None
            )

            if self.voice_talk_handle == -1:
                err = self._sdk.NET_DVR_GetLastError()
                logger.error("NET_DVR_StartVoiceCom_MR_V30 failed: {}", err)
                return False

            logger.info("NET_DVR_StartVoiceCom_MR_V30 succeeded, handle: {}", self.voice_talk_handle)

            if audio_file_path:
                import threading
                threading.Thread(
                    target=self._stream_audio_file,
                    args=(audio_file_path,),
                    daemon=True
                ).start()

        return True
    

    def _stream_audio_file(self, file_path_or_url):
        import time, os, io, tempfile, requests
        from pydub import AudioSegment

        target_path = file_path_or_url
        temp_file = None

        try:
            if file_path_or_url.startswith(("http://", "https://")):
                logger.info("Downloading audio from URL: {}", file_path_or_url)
                response = requests.get(file_path_or_url, timeout=15)
                response.raise_for_status()
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".audio")
                temp_file.write(response.content)
                temp_file.close()
                target_path = temp_file.name

            logger.info("Converting audio for Hikvision G711 μ-law: {}", target_path)

            audio = AudioSegment.from_file(target_path)
            audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)

            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav", codec="pcm_mulaw", parameters=["-ar", "8000", "-ac", "1"])
            raw_data = wav_buffer.getvalue()[44:]

            logger.info("Audio converted: {} Hz, {} channel, {} bytes", 8000, 1, len(raw_data))

            frame_size = 160
            frame_time = 0.020
            time.sleep(0.5)
            next_send = time.perf_counter()

            for offset in range(0, len(raw_data), frame_size):
                if not hasattr(self, "voice_talk_handle") or self.voice_talk_handle < 0:
                    logger.warning("Voice handle closed during streaming")
                    break

                frame = raw_data[offset:offset + frame_size]
                if len(frame) != frame_size:
                    break

                buf = create_string_buffer(frame, frame_size)
                result = self._sdk.NET_DVR_VoiceComSendData(self.voice_talk_handle, byref(buf), frame_size)

                if not result:
                    err = self._sdk.NET_DVR_GetLastError()
                    logger.error("NET_DVR_VoiceComSendData failed: {}", err)
                    break

                next_send += frame_time
                delay = next_send - time.perf_counter()
                if delay > 0:
                    time.sleep(delay)
                else:
                    next_send = time.perf_counter()

            logger.info("Audio streaming completed")
            time.sleep(0.2)
            if hasattr(self, "voice_talk_handle") and self.voice_talk_handle >= 0:
                self.stop_voice_talk()
        except Exception:
            logger.exception("Exception during audio streaming")

        finally:
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass

    def stop_voice_talk(self):
        if hasattr(self, "voice_talk_handle") and self.voice_talk_handle >= 0:
            self._sdk.NET_DVR_StopVoiceCom(self.voice_talk_handle)
            self.voice_talk_handle = -1
            logger.info("Voice intercom stopped.")
        
        # Stop video preview when the call ends
        #self.stop_video_preview()

    '''
    def _send_sip_packet(self, data: str):
        # Assumes target SIP server is listening on 5060 at the configured IP
        try:
            self.sip_sock.sendto(data.encode(), (self._config.ip, 5060))
        except Exception as e:
            logger.error("Failed to send SIP packet to {}: {}", self._config.ip, e)

    def chime_on(self, sip_number: str, label: str):
        """Sends the SIP INVITE to trigger the chime using the provided sip_number."""
        sdp = (
            "v=0\r\no=J12345678 0 0 IN IP4 0.0.0.0\r\ns=Talk session\r\n"
            "c=IN IP4 0.0.0.0\r\nt=0 0\r\n"
            "a=doorFloor:0\r\na=responseType:0\r\na=doorType:1\r\na=isSpecialType:0\r\n"
            "m=audio 9654 RTP/AVP 0 8 101\r\na=rtpmap:0 PCMU/8000\r\n"
            "a=rtpmap:8 PCMA/8000\r\na=rtpmap:101 telephone-event/8000\r\n"
            "a=sendrecv\r\n"
        )
        invite = (
            f"INVITE sip:{sip_number}@{self._config.ip}:5060 SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self._config.ip}:5060;rport;branch=z9hG4bK{self._id}\r\n"
            f"From: {label}<sip:10010100000@{self._config.ip}>;tag=123456\r\n"
            f"To: <sip:{sip_number}@{self._config.ip}:5060>\r\n"
            f"Call-ID: {self.sip_call_id}\r\n"
            "CSeq: 20 INVITE\r\n"
            "Content-Type: application/sdp\r\n"
            f"Content-Length: {len(sdp)}\r\n\r\n"
            f"{sdp}"
        )
        self._send_sip_packet(invite)

    def chime_off(self, sip_number: str):
        """Sends the SIP CANCEL to stop the chime using the provided sip_number."""
        cancel_packet = (
            f"CANCEL sip:{sip_number}@{self._config.ip}:5060 SIP/2.0\r\n"
            f"Via: SIP/2.0/UDP {self._config.ip}:5060;rport;branch=z9hG4bK{self._id}\r\n"
            f"From: <sip:10010100000@{self._config.ip}>;tag=123456\r\n"
            f"To: <sip:{sip_number}@{self._config.ip}:5060>\r\n"
            f"Call-ID: {self.sip_call_id}\r\n"
            "CSeq: 20 CANCEL\r\n"
            "Content-Length: 0\r\n\r\n"
        )
        self._send_sip_packet(cancel_packet)
    '''
        
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
        logger.debug("Unable to get the number of doors on the indoor station, please configure the relays manually with this option in the config: output_relays, we will continue with 1 output relay as a fallback")
        return 1
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
        logger.info("Unable to get the number of doors, please configure the relays manually with this option in the config: output_relays, we will continue with 1 output relay as a fallback")
        return 1
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
