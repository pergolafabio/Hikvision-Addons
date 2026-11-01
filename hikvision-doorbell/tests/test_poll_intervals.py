"""Run the actual nested poll functions without SDK, broker or hardware.

The source functions are compiled unchanged inside their original per-device
closure shape. This exercises late binding rather than inspecting source text.
Can also be run directly with python -m unittest, without pytest/conftest imports.
"""
import ast
import asyncio
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

SOURCE = Path(os.environ.get('HIKVISION_SOURCE_ROOT', Path(__file__).resolve().parents[1] / 'src'))


class StopAfterOnePoll(BaseException):
    pass


class SilentLog:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class FakeSensor:
    def __init__(self):
        self.states = []

    def set_state(self, value):
        self.states.append(value)


class FakeDoorbell:
    def __init__(self, name, interval):
        self._config = SimpleNamespace(name=name, call_state_poll=interval,
                                       scene_state_poll=interval, alarm_state_poll=interval)
        self.calls = []

    def _call_isapi(self, method, url, *args):
        self.calls.append((method, url))
        if 'callStatus' in url:
            return json.dumps({'CallStatus': {'status': 'ring'}})
        if '/scene/' in url:
            return '<SceneNowMode><nowMode>goToBed</nowMode></SceneNowMode>'
        return '<AlarmControlByPhoneCfg><commandType>closeAlarm</commandType></AlarmControlByPhoneCfg>'


def poll_factory(filename, name, interval_variable, sensor_argument):
    source = ast.parse((SOURCE / filename).read_text())
    poller = copy.deepcopy(next(n for n in ast.walk(source)
                              if isinstance(n, ast.AsyncFunctionDef) and n.name == name))
    wrapper = ast.parse('def build(devices):\n result=[]\n for doorbell in devices:\n  call_sensor=FakeSensor()\n  result.append(None)\n return result\n')
    loop = wrapper.body[0].body[1]
    setup = ast.parse(f'{interval_variable}=doorbell._config.call_state_poll\n'
                      f'if {interval_variable} == 0:\n {interval_variable}=15\n').body
    if name == 'poll_call_sensor':
        append = ast.parse('result.append((doorbell, call_sensor, poll_call_sensor()))').body[0]
    else:
        append = ast.parse(f'result.append((doorbell, call_sensor, {name}(doorbell, call_sensor)))').body[0]
    loop.body[1:] = setup + [poller, append]
    observed = []

    async def stop_sleep(delay):
        observed.append((asyncio.current_task().get_name(), delay))
        raise StopAfterOnePoll()

    # The snapshot patch may route updates through the handler; the interval
    # test still checks the actual coroutine and device, without a real handler.
    sensor_map = {}
    handler = SimpleNamespace(_set_call_state=lambda d, state: sensor_map[d].set_state(state))
    namespace = {'FakeSensor': FakeSensor, 'Doorbell': FakeDoorbell, 'Sensor': FakeSensor,
                 'SDKError': RuntimeError, 'json': json, 'ET': ET, 'logger': SilentLog(),
                 'asyncio': SimpleNamespace(sleep=stop_sleep), 'self': handler}
    exec(compile(ast.fix_missing_locations(wrapper), str(SOURCE / filename), 'exec'), namespace)

    async def exercise(devices):
        entries = namespace['build'](devices)
        for doorbell, sensor, _ in entries:
            sensor_map[doorbell] = sensor

        async def one(coroutine):
            try:
                await coroutine
            except StopAfterOnePoll:
                pass

        await asyncio.gather(*(asyncio.create_task(one(coro), name=d._config.name)
                               for d, _, coro in entries))
        return observed, entries

    return exercise


class PollIntervals(unittest.IsolatedAsyncioTestCase):
    async def check(self, filename, name, variable, sensor, expected_state, reverse=False, zero=False):
        devices = [FakeDoorbell('panel-A', 0 if zero else 2), FakeDoorbell('panel-B', 11)]
        if reverse:
            devices.reverse()
        observed, entries = await poll_factory(filename, name, variable, sensor)(devices)
        self.assertEqual(dict(observed), {'panel-A': 15 if zero else 2, 'panel-B': 11})
        for doorbell, state_sensor, _ in entries:
            self.assertEqual(state_sensor.states, [expected_state])
            self.assertEqual(len(doorbell.calls), 1)
            self.assertEqual(doorbell.calls[0][0], 'GET')

    async def test_call_intervals(self):
        await self.check('mqtt.py', 'poll_call_sensor', 'call_state_poll_sec', 'c', 'ring')

    async def test_call_reverse_order(self):
        await self.check('mqtt.py', 'poll_call_sensor', 'call_state_poll_sec', 'c', 'ring', reverse=True)

    async def test_call_zero_keeps_existing_fallback(self):
        await self.check('mqtt.py', 'poll_call_sensor', 'call_state_poll_sec', 'c', 'ring', zero=True)

    async def test_scene_intervals(self):
        await self.check('mqtt_input.py', 'poll_scene_sensor', 'scene_state_poll_sec', 's', 'goToBed')

    async def test_scene_reverse_order(self):
        await self.check('mqtt_input.py', 'poll_scene_sensor', 'scene_state_poll_sec', 's', 'goToBed', reverse=True)

    async def test_scene_zero_keeps_existing_fallback(self):
        await self.check('mqtt_input.py', 'poll_scene_sensor', 'scene_state_poll_sec', 's', 'goToBed', zero=True)

    async def test_alarm_intervals(self):
        await self.check('mqtt_input.py', 'poll_alarm_sensor', 'alarm_state_poll_sec', 'a', 'closeAlarm')

    async def test_alarm_reverse_order(self):
        await self.check('mqtt_input.py', 'poll_alarm_sensor', 'alarm_state_poll_sec', 'a', 'closeAlarm', reverse=True)

    async def test_alarm_zero_keeps_existing_fallback(self):
        await self.check('mqtt_input.py', 'poll_alarm_sensor', 'alarm_state_poll_sec', 'a', 'closeAlarm', zero=True)


if __name__ == '__main__':
    unittest.main()
