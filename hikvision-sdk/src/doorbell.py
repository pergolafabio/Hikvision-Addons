from ctypes import CDLL, sizeof
from typing import TypedDict

from loguru import logger
from sdk.hcnetsdk import NET_DVR_DEVICEINFO_V30, NET_DVR_SETUPALARM_PARAM_V50


class Config(TypedDict):
    ip: str
    username: str
    password: str


class Doorbell:
    user_id: int

    def __init__(self, sdk: CDLL, config: Config):
        logger.debug("Setting up doorbell")
        self.sdk = sdk
        self.config = config

    def authenticate(self):
        logger.debug("Logging into doorbell")
        # Instantiate required struct populated by login function
        device_info = NET_DVR_DEVICEINFO_V30()
        self.user_id = self.sdk.NET_DVR_Login_V30(
            bytes(self.config["ip"], 'utf8'),
            8000,
            bytes(self.config["username"], 'utf8'),
            bytes(self.config["password"], 'utf8'),
            device_info
        )
        if self.user_id < 0:
            # TODO raise exception
            raise RuntimeError(f"Error code {self.sdk.NET_DVR_GetLastError()}")

        logger.debug("User ID: {}", self.user_id)
        logger.debug("Serial number: {}, device type: {}",
                     device_info.serialNumber(), device_info.wDevType)

    def start_listening(self):
        alarm_param = NET_DVR_SETUPALARM_PARAM_V50()
        alarm_param.dwSize = sizeof(NET_DVR_SETUPALARM_PARAM_V50)
        alarm_param.byLevel = 1
        alarm_param.byAlarmInfoType = 1
        alarm_param.byFaceAlarmmDetection = 1

        logger.debug("Start listening for events")
        alarm_handle = self.sdk.NET_DVR_SetupAlarmChan_V50(
            self.user_id, alarm_param, None, 0)
        if alarm_handle < 0:
            raise RuntimeError(f"Error code {self.sdk.NET_DVR_GetLastError()}")

    def logout(self):
        logout_result = self.sdk.NET_DVR_Logout_V30(self.user_id)
        if not logout_result:
            logger.debug("SDK logout result {}", logout_result)

    def __del__(self):
        self.logout()
