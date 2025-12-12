from hcnetsdk import (
    NET_DVR_DEVICEINFO_V30,
    NET_DVR_CONTROL_GATEWAY,
    NET_DVR_AUDIOENC_INFO,
    NET_DVR_AUDIOENC_PROCESS_PARAM,
    NET_DVR_AUDIO_CHANNEL,
    NET_DVR_COMPRESSION_AUDIO,
    setupSDK,
)
from ctypes import (
    c_byte,
    sizeof,
    byref,
    c_ushort,
    c_long,
    c_char_p,
    POINTER,
    cast,
    create_string_buffer,
)
import itertools
import ctypes
import sys
import time


class HikVision:
    def __init__(self, ip, username, password):
        self._ip = ip
        self._username = username
        self._password = password
        self._user_id = None
        self._sdk = setupSDK()
        self._sdk.NET_DVR_GetErrorMsg.restype = c_char_p
        self._sdk.NET_DVR_Init()
        self._sdk.NET_DVR_SetValidIP(0, True)

    def login(self):
        print("test")
        device_info = NET_DVR_DEVICEINFO_V30()
        user_id = self._sdk.NET_DVR_Login_V30(
            self._ip.encode("utf-8"),
            8000,
            self._username.encode("utf-8"),
            self._password.encode("utf-8"),
            device_info,
        )
        print("test2")
        if user_id < 0:
            raise RuntimeError(
                f"NET_DVR_Login_V30 failed, error code = {self._sdk.NET_DVR_GetLastError()}"
            )
            print(f"Error logging in {self._sdk.NET_DVR_GetLastError()}")
        print(f"Logged in with {user_id}")
        self._user_id = user_id

    def unlock_door(self):
        print("Unlocking door")
        gw = NET_DVR_CONTROL_GATEWAY()
        gw.dwSize = sizeof(NET_DVR_CONTROL_GATEWAY)
        gw.dwGatewayIndex = 1
        gw.byCommand = 1  # opening command
        gw.byLockType = 0  # this is normal lock not smart lock
        gw.wLockID = 0  # door station
        gw.byControlSrc = (c_byte * 32)(
            *[97, 98, 99, 100]
        )  # anything will do but can't be empty
        gw.byControlType = 1

        result = self._sdk.NET_DVR_RemoteControl(
            self._user_id, 16009, byref(gw), gw.dwSize
        )

        if result < 0:
            self._handle_error("Failed to unlock: {}")

    def _handle_error(self, message="Api failed: {}"):
        errono = self._sdk.NET_DVR_GetLastError()
        errormsg = self._sdk.NET_DVR_GetErrorMsg(0)
        raise RuntimeError(message.format(f"{errono}: {errormsg}"))

    def get_current_encoding(self, channel=1):
        aud = NET_DVR_AUDIO_CHANNEL()
        aud.dwChannelNum = channel
        out = NET_DVR_COMPRESSION_AUDIO()
        res = self._sdk.NET_DVR_GetCurrentAudioCompress_V50(
            self._user_id, byref(aud), byref(out)
        )
        if not res:
            self._handle_error()
        print(out, out.byAudioEncType, out.byAudioSamplingRate, out.byAudioBitRate)
        return

    def play_sound(self, filename, channel=1):
        # use g711.u
        insize = 160
        vhandle = self._sdk.NET_DVR_StartVoiceCom_MR_V30(
            self._user_id, channel, None, None
        )
        if vhandle < 0:
            self._handle_error()
        time.sleep(1)
        chars = itertools.cycle("//--\\\\||")
        print("")
        try:
            with open(filename, "rb") as fd:
                data = fd.read(insize)
                print
                while data:
                    if len(data) < insize:
                        data += b"\0" * (insize - len(data))
                    output_c = (ctypes.c_ubyte * insize).from_buffer(bytearray(data))
                    char = next(chars)
                    print(f"Writing data {char}\r", flush=True, end="")
                    res = self._sdk.NET_DVR_VoiceComSendData(
                        vhandle, byref(output_c), insize
                    )
                    if not res:
                        self._handle_error("Failed to send data: {}")
                    time.sleep(0.02)
                    data = fd.read(insize)
        finally:
            time.sleep(1)
            self._sdk.NET_DVR_StopVoiceCom(vhandle)

    def logout(self):
        if self._user_id:
            self._sdk.NET_DVR_Logout_V30(self._user_id)
        self._sdk.NET_DVR_Cleanup()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--filename")
    options = parser.parse_args()
    hik = HikVision(options.ip, options.user, options.password)
    print(options)
    try:
        print("command=" + options.command)
        hik.login()
        print("command=" + options.command)
        if options.command == "unlock":
            print("Unlocking door")
            hik.unlock_door()
        elif options.command == "play_sound":
            if not options.filename:
                print("Filename required for play_sound")
                sys.exit(1)
            hik.play_sound(options.filename)
        print(options)
    finally:
        hik.logout()
        
# python3 hikcli.py --ip 192.168.0.70 --user admin --password xxx --command unlock
