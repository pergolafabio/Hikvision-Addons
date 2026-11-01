"""Exercise actual transition methods without SDK/broker/network imports."""
import ast
import asyncio
import copy
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(os.environ.get('HIKVISION_SOURCE_ROOT', Path(__file__).resolve().parents[1] / 'src'))


class SilentLog:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


class Door:
    def __init__(self, name='test', enabled=True):
        self._config = SimpleNamespace(name=name, snapshot=enabled)


def subject_type():
    source = ast.parse((SOURCE / 'mqtt.py').read_text())
    handler = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'MQTTHandler')
    methods = [copy.deepcopy(n) for n in handler.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name in ('_set_call_state', '_publish_call_snapshot')]
    if len(methods) != 2:
        raise AssertionError('Snapshot transition handling is absent')
    klass = ast.ClassDef(name='Subject', bases=[], keywords=[], body=methods, decorator_list=[])
    namespace = {'Doorbell': Door, 'asyncio': asyncio, 'logger': SilentLog(), 'os': os}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[klass], type_ignores=[])),
                 str(SOURCE / 'mqtt.py'), 'exec'), namespace)
    return namespace['Subject']


class RingSnapshots(unittest.IsolatedAsyncioTestCase):
    def make(self, *doors):
        obj = subject_type()()
        obj._call_states, obj._call_state_versions, obj._snapshot_tasks = {}, {}, {}
        self.states = {door: [] for door in doors}
        obj._sensors = {door: {'call': SimpleNamespace(set_state=self.states[door].append)} for door in doors}
        self.snapshots = []

        async def capture(door):
            self.snapshots.append(door)

        obj._publish_call_snapshot = capture
        return obj

    async def finish(self, obj):
        await asyncio.gather(*obj._snapshot_tasks.values())

    async def test_repeated_polled_ring_once(self):
        door = Door(); obj = self.make(door)
        for state in ('idle', 'ring', 'ring', 'ring'):
            obj._set_call_state(door, state)
        await self.finish(obj)
        self.assertEqual(self.snapshots, [door])
        self.assertEqual(self.states[door], ['idle', 'ring', 'ring', 'ring'])

    async def test_sdk_and_poll_share_ring(self):
        for sequence in [('ringing', 'ring', 'ringing'), ('ring', 'ringing', 'ring')]:
            door = Door(); obj = self.make(door)
            for state in sequence:
                obj._set_call_state(door, state)
                await asyncio.sleep(0)
            await self.finish(obj)
            self.assertEqual(self.snapshots, [door])

    async def test_next_call_has_new_snapshot(self):
        door = Door(); obj = self.make(door)
        obj._set_call_state(door, 'ring'); await self.finish(obj)
        obj._set_call_state(door, 'idle')
        obj._set_call_state(door, 'ring'); await self.finish(obj)
        self.assertEqual(self.snapshots, [door, door])

    async def test_snapshot_is_opt_in(self):
        for enabled in (False, None):
            door = Door(enabled=enabled); obj = self.make(door)
            obj._set_call_state(door, 'ring'); await self.finish(obj)
            self.assertEqual(self.snapshots, [])

    async def test_two_devices_are_independent(self):
        a, b = Door('A'), Door('B'); obj = self.make(a, b)
        obj._set_call_state(a, 'ring'); obj._set_call_state(b, 'ringing')
        await self.finish(obj)
        self.assertCountEqual(self.snapshots, [a, b])

    async def test_pending_snapshot_does_not_overlap(self):
        door = Door(); obj = self.make(door); blocked = asyncio.Event()
        async def capture(d):
            self.snapshots.append(d); await blocked.wait()
        obj._publish_call_snapshot = capture
        obj._set_call_state(door, 'ring'); await asyncio.sleep(0)
        obj._set_call_state(door, 'idle'); obj._set_call_state(door, 'ring')
        blocked.set(); await self.finish(obj)
        self.assertEqual(self.snapshots, [door])

    async def test_later_call_invalidates_old_timeout(self):
        door = Door(); obj = self.make(door)
        old = obj._set_call_state(door, 'ringing')
        obj._set_call_state(door, 'idle')
        current = obj._set_call_state(door, 'ringing')
        await self.finish(obj)
        self.assertGreater(current, old)
        self.assertEqual(obj._set_call_state(door, 'ringing'), current)
        self.assertGreater(obj._set_call_state(door, 'onCall'), current)

    async def test_publish_saved_snapshot(self):
        door = Door(); obj = self.make(door); published = []
        transport = SimpleNamespace(_last_snapshot_paths={},
                                    _publish_snapshot_image=lambda d, path: published.append((d, path)))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.jpg'; path.write_bytes(b'\xff\xd8synthetic\xff\xd9')
            door.take_snapshot = lambda: str(path)
            with patch.dict(sys.modules, {'mqtt_input': SimpleNamespace(get_mqtt_input=lambda: transport)}):
                await subject_type()._publish_call_snapshot(obj, door)
            self.assertEqual(published, [(door, str(path))])
            self.assertEqual(transport._last_snapshot_paths[door], str(path))

    async def test_missing_snapshot_not_published(self):
        door = Door(); obj = self.make(door); door.take_snapshot = lambda: None
        transport = SimpleNamespace(_last_snapshot_paths={},
                                    _publish_snapshot_image=lambda *args: self.fail('Invalid publication'))
        with patch.dict(sys.modules, {'mqtt_input': SimpleNamespace(get_mqtt_input=lambda: transport)}):
            await subject_type()._publish_call_snapshot(obj, door)
        self.assertEqual(transport._last_snapshot_paths, {})

    async def test_capture_error_contained(self):
        door = Door(); obj = self.make(door)
        def fail():
            raise RuntimeError('Device offline')
        door.take_snapshot = fail
        with patch.dict(sys.modules, {'mqtt_input': SimpleNamespace(get_mqtt_input=lambda: None)}):
            await subject_type()._publish_call_snapshot(obj, door)


if __name__ == '__main__':
    unittest.main()
