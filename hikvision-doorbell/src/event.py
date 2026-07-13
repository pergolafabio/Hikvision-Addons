"""Manage events coming from the Hikvision devices"""
import asyncio
from ctypes import CDLL, CFUNCTYPE, POINTER, c_void_p, cast
from typing_extensions import override
from loguru import logger
from doorbell import Doorbell, Registry

from sdk.hcnetsdk import ALARMINFO_V30_ALARMTYPE_MOTION_DETECTION, BOOL, COMM_ALARM_V30, COMM_ALARM_VIDEO_INTERCOM, COMM_UPLOAD_VIDEO_INTERCOM_EVENT, DWORD, LONG, NET_DVR_ALARMER, NET_DVR_ALARMINFO_V30, NET_DVR_VIDEO_INTERCOM_ALARM, NET_DVR_VIDEO_INTERCOM_EVENT, NET_DVR_ALARM_ISAPI_INFO, NET_DVR_ACS_ALARM_INFO, COMM_ISAPI_ALARM, COMM_ALARM_ACS, MessageCallbackAlarmInfoUnion
from sdk.utils import SDKError


class EventHandler:
    """Base class defining the callbacks methods to be invoked when an event is received from a device"""

    name: str = 'BaseHandler'

    async def motion_detection(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARMINFO_V30,
            buffer_length,
            user_pointer: c_void_p):
        raise NotImplementedError

    async def video_intercom_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_VIDEO_INTERCOM_EVENT,
            buffer_length,
            user_pointer: c_void_p):
        raise NotImplementedError

    async def video_intercom_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_VIDEO_INTERCOM_ALARM,
            buffer_length,
            user_pointer: c_void_p):
        raise NotImplementedError

    async def isapi_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARM_ISAPI_INFO,
            buffer_length,
            user_pointer: c_void_p):
        raise NotImplementedError

    async def acs_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ACS_ALARM_INFO,
            buffer_length,
            user_pointer: c_void_p):
        raise NotImplementedError

    async def unhandled_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info_pointer,
            buffer_length,
            user_pointer: c_void_p):
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.name


class ConsoleHandler(EventHandler):
    """Useful for debugging: it outputs each event it receives with the configured logger"""
    name = 'ConsoleSTDOUT'

    def __init__(self) -> None:
        super().__init__()
        logger.info("Setting up event handler: Console stdout")

    @override
    async def motion_detection(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARMINFO_V30,
            buffer_length,
            user_pointer: c_void_p):
        logger.info("Motion detected from {}", doorbell._config.name)

    @override
    async def video_intercom_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_VIDEO_INTERCOM_EVENT,
            buffer_length,
            user_pointer: c_void_p):
        logger.info("Video intercom event from {}", doorbell._config.name)

    @override
    async def video_intercom_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_VIDEO_INTERCOM_ALARM,
            buffer_length,
            user_pointer: c_void_p):
        logger.info("Video intercom alarm from {}", doorbell._config.name)

    @override
    async def isapi_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ALARM_ISAPI_INFO,
            buffer_length,
            user_pointer: c_void_p):
        #logger.info("Isapi alarm from {}", doorbell._config.name)
        pass

    @override
    async def acs_alarm(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info: NET_DVR_ACS_ALARM_INFO,
            buffer_length,
            user_pointer: c_void_p):
        logger.info("ACS alarm from {}", doorbell._config.name)

    @override
    async def unhandled_event(
            self,
            doorbell: Doorbell,
            command: int,
            device: NET_DVR_ALARMER,
            alarm_info_pointer,
            buffer_length,
            user_pointer: c_void_p):
        logger.warning("Unknown event from {}", doorbell._config.name)


class EventManager:
    """Register callbacks to be invoked when there is some SDK events coming from the devices.
    The devices need to be put in `alarm mode` for the callbacks to be invoked.

    Use `register_handler` with a subclass of `EventHandler`.

    Call `start`, then put each device in `alarm mode`.
    """
    _handlers: set[EventHandler] = set()
    _background_tasks = set()

    def __init__(self, sdk: CDLL, doorbells: Registry):
        self._sdk = sdk
        self._doorbells = doorbells
        # Save a reference to the main asyncio loop to schedule from another thread
        self._async_loop = asyncio.get_running_loop()

    def _cast_alarm_info(self, command: int, callback_alarm_info_p):
        '''Cast the alarm_info pointer received from the callback to the correct Python class, depending on the value of `command`'''
        if (command == COMM_ALARM_V30):
            return cast(callback_alarm_info_p, POINTER(NET_DVR_ALARMINFO_V30)).contents
        elif (command == COMM_ALARM_VIDEO_INTERCOM):
            return cast(callback_alarm_info_p, POINTER(NET_DVR_VIDEO_INTERCOM_ALARM)).contents
        elif (command == COMM_UPLOAD_VIDEO_INTERCOM_EVENT):
            return cast(callback_alarm_info_p, POINTER(NET_DVR_VIDEO_INTERCOM_EVENT)).contents
        elif (command == COMM_ISAPI_ALARM):
            return cast(callback_alarm_info_p, POINTER(NET_DVR_ALARM_ISAPI_INFO)).contents
        elif (command == COMM_ALARM_ACS):
            return cast(callback_alarm_info_p, POINTER(NET_DVR_ACS_ALARM_INFO)).contents
        else:
            logger.warning("Received unhandled command: {}", command)
            return callback_alarm_info_p

    async def _invoke_handlers(self, command, device: NET_DVR_ALARMER, alarm_info, buffer_length, user_pointer):
        # Match the device information from the callback with a Doorbell instance in the registry
        doorbell = self._doorbells.getBySerialNumber(device.serialNumber())
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
                case NET_DVR_ALARM_ISAPI_INFO():
                    handler_func = handler.isapi_alarm
                case NET_DVR_ACS_ALARM_INFO():
                    handler_func = handler.acs_alarm
                case _:
                    handler_func = handler.unhandled_event

            # Ignore type checking since it gets confused by the match-case statement above
            task = asyncio.create_task(handler_func(doorbell, command, device, alarm_info, buffer_length, user_pointer), name=handler.name)  # type: ignore

            # Add task to the set. This creates a strong reference, as instructed by asyncio
            self._background_tasks.add(task)

            # To prevent keeping references to finished tasks forever, make each task remove its own reference from the set after completion:
            task.add_done_callback(self._background_tasks.discard)

    def _handle_callback(self, command: int, alarm_device_pointer, alarm_info_pointer, buffer_length, user_pointer):
        logger.debug("Callback invoked from SDK")
        device: NET_DVR_ALARMER = alarm_device_pointer.contents

        '''
        # Match the device information with the Doorbell instance
        doorbell = self._doorbells.getBySerialNumber(device.serialNumber())
        
        # ------------------------------------------------------------------
        # NATIVE SDK AUTO-ONLINE HEAL
        # If we are receiving alarm data packets, the device is explicitly online.
        # ------------------------------------------------------------------
        if doorbell:
            for handler in self._handlers:
                if handler.__class__.__name__ == 'MQTTHandler' or handler.name == 'MQTT':
                    try:
                        if hasattr(handler, '_sensors') and doorbell in handler._sensors:
                            doorbell_sensors = handler._sensors[doorbell]
                            online_sensor = doorbell_sensors.get('online') or doorbell_sensors.get('online_state')
                            # If the sensor is missing or currently marked offline, flip it back!
                            if online_sensor and getattr(online_sensor, '_state', None) != "online":
                                online_sensor.set_state("online")
                                logger.debug(f"SDK alarm channel traffic resumed: {doorbell._config.name} marked ONLINE.")
                    except Exception as sensor_err:
                        logger.error(f"Failed to auto-heal online state via SDK callback: {sensor_err}")
        # ------------------------------------------------------------------
        '''

        # Cast the alarm_info pointer to the correct Python class
        alarm_info = self._cast_alarm_info(command, alarm_info_pointer)

        # Invoke the registered handlers on the main asyncio loop
        future = asyncio.run_coroutine_threadsafe(
            self._invoke_handlers(
                command, device, alarm_info, buffer_length, user_pointer),
            self._async_loop)
        future.result()

    '''
    async def _process_exception(self, exception_type: int, user_id: int):
        """Toggles the HA sensor state purely based on native SDK connection exceptions"""
        target_index = None
        target_doorbell = None
        
        for index, doorbell in list(self._doorbells.items()):
            doorbell_id = getattr(doorbell, 'user_id', getattr(doorbell, '_user_id', None))
            if doorbell_id == user_id:
                target_index = index
                target_doorbell = doorbell
                break

        if target_index is not None and target_doorbell is not None:
            # Determine target state based on the exception code
            if exception_type == 0x8006:
                new_state = "offline"
                log_msg = f"Doorbell index {target_index} dropped connection (SDK exception 0x8006)"
            elif exception_type == 0x8016:
                new_state = "online"
                log_msg = f"Doorbell index {target_index} reconnected successfully (SDK exception 0x8016)"
            else:
                return

            logger.debug(log_msg)
            
            # Push the updated state directly to the HA entity handler
            for handler in self._handlers:
                if handler.__class__.__name__ == 'MQTTHandler' or handler.name == 'MQTT':
                    try:
                        if hasattr(handler, '_sensors') and target_doorbell in handler._sensors:
                            doorbell_sensors = handler._sensors[target_doorbell]
                            online_sensor = doorbell_sensors.get('online') or doorbell_sensors.get('online_state')
                            if online_sensor:
                                online_sensor.set_state(new_state)
                                logger.info(f"Successfully changed entity state for {target_doorbell._config.name} to {new_state}.")
                    except Exception as sensor_err:
                        logger.error(f"Failed to update entity state to {new_state}: {sensor_err}")

    def _get_exception_callback_func(self):
        """C-compatible wrapper that catches hardware drops and reconnects"""
        @CFUNCTYPE(None, DWORD, LONG, LONG, c_void_p)
        def exc_callback(dwType: int, lUserID: int, lHandle: int, pUser: c_void_p):

            # Print every raw code from the SDK to stdout/log file for easy analysis
            logger.debug(f"SDK Global Exception Event Triggered -> Code: {hex(dwType)} (Dec: {dwType}) for UserID: {lUserID}")
            
            # Allow both drop (0x8006) and recovery (0x8016) codes through
            if dwType in (0x8006, 0x8016):
                asyncio.run_coroutine_threadsafe(
                    self._process_exception(dwType, lUserID), 
                    self._async_loop
                )
        return exc_callback

    '''
    def register_handler(self, handler: EventHandler):
        logger.debug("Adding event handler {}", handler)
        self._handlers.add(handler)

    def remove_handler(self, handler: EventHandler):
        logger.debug("Removing event handler {}", handler)
        self._handlers.discard(handler)

    def _get_callback_func(self):
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
        """Register the callbacks with the SDK"""
        logger.debug("Registering callback function using SDK")
        self.callback_func = self._get_callback_func()
        result = self._sdk.NET_DVR_SetDVRMessageCallBack_V50(
            0,
            self.callback_func,
            None)
        if not result:
            raise SDKError(self._sdk, "Error while setting up event manager")
        
        '''
        # ==================== ADD THESE LINES HERE ====================
        logger.debug("Registering global exception callback function using SDK")
        self.exception_callback_func = self._get_exception_callback_func()
        exc_result = self._sdk.NET_DVR_SetExceptionCallBack_V30(0, None, self.exception_callback_func, None)
        if not exc_result:
            raise SDKError(self._sdk, "Error while setting up event manager exception callback")
        # ==============================================================
        '''
        
        # Warn if there are no handlers defined (apart from ConsoleHandler, that is only useful for troubleshooting)
        if not any([not isinstance(handler, ConsoleHandler) for handler in self._handlers]):
            logger.warning("No handler defined!")
