import os
import sys
sys.path.append("src")

from doorbell import Doorbell, Config
from sdk.utils import loadSDK, setupSDK, shutdownSDK, SDKConfig, LogLevel


def listen():        

    sdk = loadSDK()
    sdk_config: SDKConfig = {
        'log_level': LogLevel.DEBUG,
        'log_dir': str('/tmp/SDKLog')
    }
    setupSDK(sdk, sdk_config)

    config: Config = {
        "ip": os.getenv("IP", ""),
        "username": os.getenv("USERNAME", ""),
        "password": os.getenv("PASSWORD", ""),
    }

    a = Doorbell(sdk, config)
    a.authenticate()
    a.setup_alarm()

    while True:
        input()

    a.disconnect()
    shutdownSDK(sdk)

if __name__ == "__main__":
    listen()