import ctypes
from ctypes import (
    c_byte,
    c_char_p,
    c_long,
    c_ubyte,
    c_uint,
    c_void_p,
    sizeof,
    byref,
    POINTER,
    CFUNCTYPE,
)
import itertools
import os
import sys
import time

from hcnetsdk import (
    NET_DVR_DEVICEINFO_V30,
    NET_DVR_CONTROL_GATEWAY,
    setupSDK,
)


class HikVision:
    def __init__(self, ip, username, password):
        self._ip = ip
        self._username = username
        self._password = password
        self._user_id = None
        self._sdk = setupSDK()
        
        # Configure error messaging return type
        self._sdk.NET_DVR_GetErrorMsg.restype = c_char_p
        
        # Define C-types for VoiceCom SDK functions to prevent 64-bit pointer truncation crashes
        self._sdk.NET_DVR_StartVoiceCom_MR_V30.argtypes = [c_long, c_uint, c_void_p, c_void_p]
        self._sdk.NET_DVR_StartVoiceCom_MR_V30.restype = c_long
        
        self._sdk.NET_DVR_VoiceComSendData.argtypes = [c_long, c_void_p, c_uint]
        self._sdk.NET_DVR_VoiceComSendData.restype = ctypes.c_bool

        self._sdk.NET_DVR_Init()
        self._sdk.NET_DVR_SetValidIP(0, True)

    def login(self):
        device_info = NET_DVR_DEVICEINFO_V30()
        user_id = self._sdk.NET_DVR_Login_V30(
            self._ip.encode("utf-8"),
            8000,
            self._username.encode("utf-8"),
            self._password.encode("utf-8"),
            byref(device_info),
        )
        if user_id < 0:
            self._handle_error("NET_DVR_Login_V30 failed: {}")
            
        print(f"[DEBUG] Logged in successfully. User ID = {user_id}")
        self._user_id = user_id

    def unlock_door(self):
        print("Unlocking door...")
        gw = NET_DVR_CONTROL_GATEWAY()
        gw.dwSize = sizeof(NET_DVR_CONTROL_GATEWAY)
        gw.dwGatewayIndex = 1
        gw.byCommand = 1  # opening command
        gw.byLockType = 0
        gw.wLockID = 0
        gw.byControlSrc = (c_byte * 32)(*[97, 98, 99, 100])
        gw.byControlType = 1

        result = self._sdk.NET_DVR_RemoteControl(
            self._user_id, 16009, byref(gw), gw.dwSize
        )

        if not result:
            self._handle_error("Failed to unlock: {}")

    def _handle_error(self, message="API failed: {}"):
        errono = self._sdk.NET_DVR_GetLastError()
        errormsg = self._sdk.NET_DVR_GetErrorMsg(errono)
        if isinstance(errormsg, bytes):
            errormsg = errormsg.decode('utf-8', errors='ignore')
        print(f"[ERROR DEBUG] SDK Error Code: {errono}, Message: {errormsg}")
        raise RuntimeError(message.format(f"{errono}: {errormsg}"))

    def play_sound(self, filename, channel=1):
        insize = 160
        
        if not os.path.exists(filename):
            print(f"[ERROR] Audio file not found at: {filename}")
            return

        file_size = os.path.getsize(filename)
        print(f"[DEBUG] Target audio file size: {file_size} bytes")

        # Define and keep a reference to the voice callback to prevent garbage collection crashes
        VOICE_CB = CFUNCTYPE(None, c_long, POINTER(c_byte), c_uint, c_ubyte, c_void_p)
        def _dummy_voice_callback(handle, data_buffer, buf_size, audio_flag, user_data):
            print(f"[CALLBACK DEBUG] Voice callback triggered. Handle: {handle}, BufSize: {buf_size}, AudioFlag: {audio_flag}")
        
        self._voice_cb_ref = VOICE_CB(_dummy_voice_callback)

        print(f"[DEBUG] Starting voice talk session on channel {channel}...")
        vhandle = self._sdk.NET_DVR_StartVoiceCom_MR_V30(
            self._user_id, channel, self._voice_cb_ref, None
        )
        print(f"[DEBUG] NET_DVR_StartVoiceCom_MR_V30 returned vhandle: {vhandle}")
        
        if vhandle < 0:
            self._handle_error("Failed to start voice talk: {}")

        time.sleep(1)
        chars = itertools.cycle("//--\\\\||")
        print("Streaming audio...")

        # Pre-allocate static ctypes buffer once
        output_c = (c_ubyte * insize)()
        chunks_sent = 0
        total_bytes_sent = 0

        try:
            with open(filename, "rb") as fd:
                while True:
                    data = fd.read(insize)
                    if not data:
                        print("\n[DEBUG] Reached end of audio file.")
                        break
                    
                    if len(data) < insize:
                        data += b"\0" * (insize - len(data))

                    ctypes.memmove(output_c, data, insize)

                    char = next(chars)
                    print(f"Writing data {char} | Chunks sent: {chunks_sent}\r", flush=True, end="")

                    res = self._sdk.NET_DVR_VoiceComSendData(
                        vhandle, byref(output_c), insize
                    )
                    
                    if not res:
                        err_code = self._sdk.NET_DVR_GetLastError()
                        print(f"\n[WARNING] NET_DVR_VoiceComSendData failed on chunk {chunks_sent}. SDK Error: {err_code}")
                    else:
                        total_bytes_sent += insize

                    chunks_sent += 1
                    time.sleep(0.02)
                    
            print(f"\n[DEBUG] Finished streaming loop. Total chunks: {chunks_sent}, Total bytes sent: {total_bytes_sent}")
        except Exception as e:
            print(f"\n[ERROR] Exception during audio streaming: {e}")
            raise
        finally:
            print("[DEBUG] Stopping voice talk session...")
            time.sleep(1)
            stop_res = self._sdk.NET_DVR_StopVoiceCom(vhandle)
            print(f"[DEBUG] NET_DVR_StopVoiceCom result: {stop_res}")

    def logout(self):
        """Logout and cleanup C SDK resources safely."""
        if self._user_id is not None and self._user_id >= 0:
            print(f"[DEBUG] Logging out user ID: {self._user_id}")
            self._sdk.NET_DVR_Logout_V30(self._user_id)
            self._user_id = None
        self._sdk.NET_DVR_Cleanup()
        print("[DEBUG] SDK cleanup completed.")


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
    try:
        hik.login()
        if options.command == "unlock":
            hik.unlock_door()
        elif options.command == "play_sound":
            if not options.filename:
                print("Error: --filename required for play_sound")
                sys.exit(1)
            hik.play_sound(options.filename)
    finally:
        hik.logout()