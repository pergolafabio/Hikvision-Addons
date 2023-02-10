
from json import load
from pathlib import Path
from sdk.utils import LogLevel, SDKConfig, loadSDK, setupFunctionTypes, setupSDK, shutdownSDK


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
        'log_level': LogLevel.INFO,
        'log_dir': str(tmp_path)
    }
    setupSDK(sdk, config)

def test_setupSDK_with_debug(tmp_path: Path):
    sdk = loadSDK()
    config: SDKConfig = {
        'log_level': LogLevel.DEBUG,
        'log_dir': str(tmp_path)
    }
    setupSDK(sdk, config)

def test_setupSDK_with_folder(tmp_path: Path):
    sdk = loadSDK()
    config: SDKConfig = {
        'log_level': LogLevel.DEBUG,
        'log_dir': str(tmp_path)
    }
    setupSDK(sdk, config)

def test_setupSDK_with_dev_null():
    sdk = loadSDK()
    config: SDKConfig = {
        'log_level': LogLevel.DEBUG,
        'log_dir': '/dev/null'
    }
    setupSDK(sdk, config)