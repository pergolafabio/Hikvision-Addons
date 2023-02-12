from ctypes import CDLL, sizeof
from typing import TypedDict

from loguru import logger
from sdk.hcnetsdk import NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM_V50


class Config(TypedDict):
    ip: str
    username: str
    password: str


class Doorbell:
    """A doorbell device.

    This object manages a connection with the Hikvision door station.
    Call `authenticate` to login in the device, then `setup_alarm` to configure the doorbell to stream back events.

    Call `logout` when you want to stop receiving events.
    """
    user_id: int

    def __init__(self, sdk: CDLL, config: Config):
        logger.debug("Setting up doorbell")
        self._sdk = sdk
        self._config = config

    def authenticate(self):
        '''Authenticate with the remote doorbell'''
        logger.debug("Logging into doorbell")
        self._device_info = NET_DVR_DEVICEINFO_V30()
        self.user_id = self._sdk.NET_DVR_Login_V30(
            bytes(self._config["ip"], 'utf8'),
            8000,
            bytes(self._config["username"], 'utf8'),
            bytes(self._config["password"], 'utf8'),
            self._device_info
        )
        if self.user_id < 0:
            # TODO raise exception
            raise RuntimeError(f"SDK error code {self._sdk.NET_DVR_GetLastError()}")

        logger.debug("Login returned user ID: {}", self.user_id)
        logger.debug("Doorbell serial number: {}, device type: {}",
                     self._device_info.serialNumber(), self._device_info.wDevType)

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

    def __del__(self):
        self.logout()
