
from ctypes import CDLL, POINTER, c_char_p, c_int, c_void_p, cdll
from enum import Enum
import os
import platform
from typing import Optional, TypedDict
from loguru import logger
from sdk.hcnetsdk import DWORD, LONG, NET_DVR_SETUPALARM_PARAM_V50, WORD, NET_DVR_DEVICEINFO_V30, fMessageCallBack


class LogLevel(Enum):
    '''
    Define the level of verbosity of the SDK.
    '''
    NONE = 0
    ERROR = 1
    INFO = 2
    DEBUG = 3


class SDKConfig(TypedDict):
    '''
    Configuration for the SDK

    Attributes:
        log_level: Level of verbosity. By default it is NONE.
        log_dir: Directory where the SDK will write the log files

    '''
    log_level: LogLevel
    log_dir: str


def loadSDK() -> CDLL:
    '''
    Load the Hikvision SDK library with ctypes wrapper and return it.

    setupSDK() must be called before the library can be used.

    Returns:
       CDLL: The loaded library
    '''
    logger.info(f"Using OS: {platform.uname()[0]} with architecture: {platform.uname()[4]}")

    if platform.uname()[0] == "Windows":
        hcnetsdk_path = ".\lib-windows64\HCNetSDK.dll"
    elif platform.uname()[0] == "Linux":
        if platform.uname()[4] == "x86_64":
            hcnetsdk_path = os.path.join("lib-amd64", "libhcnetsdk.so")
        elif platform.uname()[4] == "aarch64":
            hcnetsdk_path = os.path.join("lib-aarch64", "libhcnetsdk.so")
        else:
            raise RuntimeError("No supported Linux library found!")
    else:
        raise RuntimeError("Unsupported operating system")
    logger.debug(f"Loading library from {hcnetsdk_path}")
    lib = cdll.LoadLibrary(hcnetsdk_path)
    setupFunctionTypes(lib)
    return lib


def setupFunctionTypes(lib: CDLL):
    """Define the argument types so that ctypes can help in avoiding error when calling the C functions."""

    # Arguments
    lib.NET_DVR_Login_V30.argtypes = [c_char_p, WORD, c_char_p, c_char_p, POINTER(NET_DVR_DEVICEINFO_V30)]
    lib.NET_DVR_Logout_V30.argtypes = [c_int]
    lib.NET_DVR_SetDVRMessageCallBack_V50.argtypes = [c_int, fMessageCallBack, c_void_p]
    lib.NET_DVR_SetupAlarmChan_V50.argtypes = [LONG, NET_DVR_SETUPALARM_PARAM_V50, c_char_p, DWORD]

    # Return types
    # lib.NET_DVR_Login_V30.restype = LONG


def setupSDK(sdk: CDLL, config: Optional[SDKConfig] = None):
    """
    Initialize the SDK. Must be called before any method of it is invoked. Remember to call shutdownSDK() to release its resources!.
    Optionally accepts a configuration dict.
    """

    logger.debug("Initializing SDK")
    sdk_init_result = sdk.NET_DVR_Init()
    if not sdk_init_result:
        raise RuntimeError("Unable to initialize SDK, init returned {}", sdk_init_result)

    if config:
        result = sdk.NET_DVR_SetLogToFile(config["log_level"].value, bytes(config["log_dir"], 'utf8'), False)
        if not result:
            raise RuntimeError("Cannot configure SDK logs, returned {}", result)

    valid_ip_result = sdk.NET_DVR_SetValidIP(0, True)
    if not valid_ip_result:
        logger.warning("SDK setValidIP returned {}", valid_ip_result)
    
    logger.debug("SDK initialized")


def shutdownSDK(sdk: CDLL):
    """Release the resources held by the SDK"""
    logger.debug("Shutting down SDK")
    sdk.NET_DVR_Cleanup()
