import asyncio
from ctypes import CDLL, CFUNCTYPE, POINTER, c_void_p, cast
from loguru import logger

from sdk.hcnetsdk import ALARMINFO_V30_ALARMTYPE_MOTION_DETECTION, BOOL, COMM_ALARM_V30, COMM_ALARM_VIDEO_INTERCOM, COMM_UPLOAD_VIDEO_INTERCOM_EVENT, DWORD, LONG, NET_DVR_ALARMER, NET_DVR_ALARMINFO_V30, NET_DVR_VIDEO_INTERCOM_ALARM, NET_DVR_VIDEO_INTERCOM_EVENT, MessageCallbackAlarmInfoUnion


class EventHandler:
    name: str = 'EventHandler'

    async def motion_detection(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_ALARMINFO_V30, buffer_length, user_pointer: c_void_p):
        raise NotImplementedError
    
    async def video_intercom_event(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_VIDEO_INTERCOM_EVENT, buffer_length, user_pointer: c_void_p):
        raise NotImplementedError
    
    async def video_intercom_alarm(self, command: int, device: NET_DVR_ALARMER, alarm_info: NET_DVR_VIDEO_INTERCOM_ALARM, buffer_length, user_pointer: c_void_p):
        raise NotImplementedError

    async def unhandled_event(self, command: int, device: NET_DVR_ALARMER, alarm_info_pointer, buffer_length, user_pointer: c_void_p):
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.name


class EventManager:
    _handlers: set[EventHandler] = set()
    _background_tasks = set()

    def __init__(self, sdk: CDLL):
        logger.debug("Setting up event manager")
        self.sdk = sdk
        # Save a reference to the main asyncio loop to schedule from another thread
        self.async_loop = asyncio.get_running_loop()

    def cast_alarm_info(self, command: int, callback_alarm_info_p):
        '''Cast the alarm_info pointer received from the callback to the correct Python class, depending on the value of `command`'''
        if (command == COMM_ALARM_V30):
            return cast(callback_alarm_info_p, POINTER(NET_DVR_ALARMINFO_V30)).contents
        elif (command == COMM_ALARM_VIDEO_INTERCOM):
            return cast(callback_alarm_info_p, POINTER(NET_DVR_VIDEO_INTERCOM_ALARM)).contents
        elif (command == COMM_UPLOAD_VIDEO_INTERCOM_EVENT):
            return cast(callback_alarm_info_p, POINTER(NET_DVR_VIDEO_INTERCOM_EVENT)).contents
        else:
            logger.warning("Received unhandled command: {}", command)
            return callback_alarm_info_p

    async def _invoke_handlers(self, command, device, alarm_info, buffer_length, user_pointer):
        logger.debug("Invoking {} handlers", len(self._handlers))
        for handler in self._handlers:

            # Select the handler function to call based on the type of alarm we have received
            match alarm_info:
                case NET_DVR_ALARMINFO_V30() if alarm_info.dwAlarmType == ALARMINFO_V30_ALARMTYPE_MOTION_DETECTION:
                    handler_func = handler.motion_detection
                case NET_DVR_VIDEO_INTERCOM_ALARM():
                    handler_func = handler.video_intercom_alarm
                case NET_DVR_VIDEO_INTERCOM_EVENT():
                    handler_func = handler.video_intercom_event
                case _:
                    handler_func = handler.unhandled_event

            # Ignore type checking since it gets confused by the match-case statement above
            task = asyncio.create_task(handler_func(command, device, alarm_info, buffer_length, user_pointer), name=handler.name) # type: ignore
            
            # Add task to the set. This creates a strong reference, as instructed by asyncio
            self._background_tasks.add(task)

            # To prevent keeping references to finished tasks forever, make each task remove its own reference from the set after completion:
            task.add_done_callback(self._background_tasks.discard)

    def _handle_callback(self, command: int, alarm_device_pointer, alarm_info_pointer, buffer_length, user_pointer):
        logger.debug("Callback invoked from SDK")
        device: NET_DVR_ALARMER = alarm_device_pointer.contents

        # Cast the alarm_info pointer to the correct Python class
        alarm_info = self.cast_alarm_info(command, alarm_info_pointer)

        # Invoke the registered handlers on the main asyncio loop
        future = asyncio.run_coroutine_threadsafe(
            self._invoke_handlers(
                command, device, alarm_info, buffer_length, user_pointer),
            self.async_loop)
        future.result()

    def register_handler(self, handler: EventHandler):
        logger.debug("Adding event handler {}", handler)
        self._handlers.add(handler)

    def remove_handler(self, handler: EventHandler):
        logger.debug("Removing event handler {}", handler)
        self._handlers.discard(handler)

    def get_callback_func(self):
        '''Wrapper to allow the use of a method function as a C callback function'''
        @CFUNCTYPE(BOOL, LONG, POINTER(NET_DVR_ALARMER), POINTER(MessageCallbackAlarmInfoUnion), DWORD, c_void_p)
        def callback(command: int, alarm_device_pointer, alarm_info_pointer, buffer_length, user_pointer):
            self._handle_callback(
                command,
                alarm_device_pointer,
                alarm_info_pointer,
                buffer_length,
                user_pointer)
        return callback

    def start(self):
        logger.debug("Registering event callback using SDK")
        self.callback_func = self.get_callback_func()
        result = self.sdk.NET_DVR_SetDVRMessageCallBack_V50(
            0,
            self.callback_func,
            None)
        if not result:
            raise RuntimeError(f"Error code {self.sdk.NET_DVR_GetLastError()}")
