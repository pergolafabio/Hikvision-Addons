
from ctypes import CDLL, c_char_p, cast
import os
from pathlib import Path

import pytest
from doorbell import Doorbell
from sdk.utils import SDKLogLevel, SDKConfig, call_ISAPI, loadSDK, setupFunctionTypes, setupSDK, shutdownSDK


def test_loadSDK():
    sdk = loadSDK()
    assert sdk is not None


def test_setupFunctionTypes():
    sdk = loadSDK()
    setupFunctionTypes(sdk)


def test_shutdownSDK():
    sdk = loadSDK()
    shutdownSDK(sdk)


def test_setupSDK():
    sdk = loadSDK()
    setupSDK(sdk)


def test_setupSDK_with_config(tmp_path: Path):
    sdk = loadSDK()
    config: SDKConfig = {
        'log_level': SDKLogLevel.INFO,
        'log_dir': str(tmp_path)
    }
    setupSDK(sdk, config)


def test_setupSDK_with_debug(tmp_path: Path):
    sdk = loadSDK()
    config: SDKConfig = {
        'log_level': SDKLogLevel.DEBUG,
        'log_dir': str(tmp_path)
    }
    setupSDK(sdk, config)


def test_setupSDK_with_folder(tmp_path: Path):
    sdk = loadSDK()
    config: SDKConfig = {
        'log_level': SDKLogLevel.DEBUG,
        'log_dir': str(tmp_path)
    }
    setupSDK(sdk, config)


def test_setupSDK_with_dev_null():
    sdk = loadSDK()
    config: SDKConfig = {
        'log_level': SDKLogLevel.DEBUG,
        'log_dir': '/dev/null'
    }
    setupSDK(sdk, config)


@pytest.mark.skipif(os.environ.get("CI") is not None, reason="Cannot run inside CI pipeline")
def test_call_ISAPI(sdk: CDLL, doorbell: Doorbell):
    doorbell.authenticate()
    output = call_ISAPI(sdk, doorbell.user_id, "GET", "/ISAPI/System/DeviceInfo")

    outputBuffer = output.lpOutBuffer
    output_char_p = cast(outputBuffer, c_char_p)
    response_body = output_char_p.value.decode("utf-8")  # type: ignore

    assert output is not None
    assert len(response_body) > 1
