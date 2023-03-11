
from ctypes import CDLL, POINTER, c_char, c_char_p, c_int, c_long, c_void_p, cast, cdll, sizeof
from ctypes.wintypes import LPVOID
from enum import IntEnum
import os
import platform
from typing import Optional, TypedDict
from loguru import logger
from sdk.hcnetsdk import DWORD, LONG, NET_DVR_SETUPALARM_PARAM_V50, NET_DVR_XML_CONFIG_INPUT, NET_DVR_XML_CONFIG_OUTPUT, WORD, NET_DVR_DEVICEINFO_V30, fMessageCallBack


class SDKLogLevel(IntEnum):
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
    log_level: SDKLogLevel
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
    lib.NET_DVR_GetErrorMsg.argtypes = [POINTER(c_long)]
    lib.NET_DVR_SetDVRMessageCallBack_V50.argtypes = [c_int, fMessageCallBack, c_void_p]
    lib.NET_DVR_SetupAlarmChan_V50.argtypes = [LONG, NET_DVR_SETUPALARM_PARAM_V50, c_char_p, DWORD]
    lib.NET_DVR_RemoteControl.argtypes = [LONG, DWORD, c_void_p, DWORD]
    lib.NET_DVR_STDXMLConfig.argtypes = [LONG, POINTER(NET_DVR_XML_CONFIG_INPUT), POINTER(NET_DVR_XML_CONFIG_OUTPUT)]
    lib.NET_DVR_GetDeviceAbility.argtypes = [LONG, DWORD, c_char_p, DWORD, c_char_p, DWORD]

    # Return types
    lib.NET_DVR_GetErrorMsg.restype = c_char_p


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


def call_ISAPI(sdk: CDLL, user_id: int, http_method: str, url: str, requestBody: str = "") -> NET_DVR_XML_CONFIG_OUTPUT:
    """Call the specified ISAPI endpoint using the SDK.

    Args:
        sdk: an instance of Hikvision SDK
        user_id: the logged in user ID returned by the SDK
        http_method: HTTP method to use (e.g. GET, POST, PUT)
        url: The URL to invoke. Must start with `/ISAPI`
        requestBody: optional request body
    Returns:
        NET_DVR_XML_CONFIG_OUTPUT: The response struct
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

    # Do the actual call
    result = sdk.NET_DVR_STDXMLConfig(user_id, inputStruct, outputStruct)

    if not result:
        # The response status is populated only in case of error
        logger.debug("Response status: {}", responseStatusBuffer.value.decode("utf-8"))
        raise SDKError(sdk, f"Error while calling ISAPI {url}")

    logger.debug("Response output: {}", outputBuffer.value.decode("utf-8"))

    return outputStruct


class SDKError(RuntimeError):
    """
    This exception should be appropriately trapped and explained to the user where it is raised.
    """
    def __init__(self, sdk: CDLL, user_message: str, *args: object) -> None:
        """Base exception class for error generating from the SDK API
        
        Use the `user_message` parameter to a user-friendly message that will be printed out along with the error.
        It automatically extracts the error code and message from the SDK.
        This class sets the `error_code` and `error_message` as a tuple inside its `args` property.
        """
        super().__init__(*args)
        error_code = sdk.NET_DVR_GetLastError()
        error_message: str = sdk.NET_DVR_GetErrorMsg(c_long(error_code)).decode('utf-8')
        
        # Prepend the three parameters to the rest of the tuple in args
        self.args = (user_message, error_code, error_message, *self.args)
        
