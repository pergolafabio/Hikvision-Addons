"""Offline transport, privacy and crash tests; no real device or broker."""
import ctypes as C
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import indoor_notice as module
from indoor_notice import Notice, NoticeData, NoticeError, NoticeService, abi_layout, jpeg_info, parse_request, read_picture, sdk_send

# Synthetic 1x1 baseline RGB JPEG, created with Pillow. No real camera/person.
import base64
JPEG = base64.b64decode('/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAA0JCgsKCA0LCgsODg0PEyAVExISEyccHhcgLikxMC4pLSwzOko+MzZGNywtQFdBRkxOUlNSMj5aYVpQYEpRUk//2wBDAQ4ODhMREyYVFSZPNS01T09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0//wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFAEBAAAAAAAAAAAAAAAAAAAABf/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AJ8AwIf/2Q==')


class NoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pictures = self.root / "pictures"
        self.pictures.mkdir()
        self.now = 1793674800.0
        self.service = NoticeService(self.root / "journal", self.pictures, lambda: self.now)
        self.target = hashlib.sha256(b"synthetic-device").hexdigest()
        self.idle = Mock(return_value=True)
        self.transport = Mock(return_value={"status": "accepted", "device_accepted": True, "sdk_error": None})

    def payload(self, **changes):
        data = {"id": "test-1", "title": "Проверка", "text": "Котёл работает\nВсе в норме", "expires_at": self.now + 120}
        data.update(changes)
        return json.dumps(data, ensure_ascii=False).encode()

    def send(self, **changes):
        return self.service.send(self.payload(**changes), self.target, self.idle, self.transport)

    def test_layout_and_cyrillic_byte_boundaries(self):
        self.assertEqual(abi_layout(), module.EXPECTED_ABI)
        self.send(title="я" * 31 + "x", text="я" * 511 + "x")
        for changes in ({"title": "я" * 32}, {"text": "я" * 512}, {"text": "bad\x00text"}, {"id": "../test"}):
            with self.subTest(changes=changes), self.assertRaises(NoticeError):
                parse_request(self.payload(**changes))

    def test_strict_json_types_keys_and_boundaries(self):
        for raw in (b"{}", b"[]", b"null", b'"str"', b'{}' * 4097, b"\xff",
                    self.payload(text=True), self.payload(expires_at=True), self.payload(expires_at=float('nan')),
                    self.payload(level=[]), self.payload(extra=1), self.payload(picture="../secret.jpg"),
                    self.payload(picture="https://example.com/a.jpg"), self.payload(picture="a.png"),
                    b'{"id":"one","id":"two"}'):
            with self.subTest(raw=raw[:80]), self.assertRaises(NoticeError):
                parse_request(raw)

    def test_alarm_and_notice_exact_abi_buffers(self):
        for level, expected in (("alarm", 3), ("notice", 4)):
            item = Notice("test", "Тема", "Текст", datetime.now(timezone.utc), level, JPEG)
            def remote(user, command, pointer, size):
                self.assertEqual((user, command, size), (1, 16008, 1552))
                value = C.cast(pointer, C.POINTER(NoticeData)).contents
                self.assertEqual(value.byLevel, expected)
                self.assertEqual(value.byPicNum, 1)
                self.assertEqual(bytes(value.byNoticeTheme).split(b"\0")[0].decode(), "Тема")
                self.assertEqual(C.string_at(value.struNoticePic[0].pPicData, value.struNoticePic[0].dwPicDataLen), JPEG)
                self.assertFalse(value.struNoticePic[1].pPicData)
                self.assertFalse(any(value.byRes2))
                return 1
            sdk = Mock()
            sdk.NET_DVR_RemoteControl.side_effect = remote
            self.assertEqual(sdk_send(sdk, 1, item)["status"], "accepted")
            sdk.NET_DVR_GetLastError.assert_not_called()

    def test_sdk_errors_and_invalid_session(self):
        item = Notice("test", "Title", "Text", datetime.now(timezone.utc))
        sdk = Mock()
        sdk.NET_DVR_RemoteControl.return_value = 0
        for error, expected in ((10, "unknown"), (29, "rejected")):
            sdk.NET_DVR_GetLastError.return_value = error
            self.assertEqual(sdk_send(sdk, 1, item)["status"], expected)
        for session in (-1, True, 2147483648):
            with self.assertRaises(NoticeError):
                sdk_send(sdk, session, item)

    def test_restart_duplicate_does_not_retry(self):
        self.assertEqual(self.send()["status"], "accepted")
        self.service = NoticeService(self.root / "journal", self.pictures, lambda: self.now)
        self.assertEqual(self.send()["duplicate"], True)
        self.transport.assert_called_once()
        self.idle.assert_called_once()

    def test_same_id_changed_content_or_sound_is_rejected(self):
        self.send()
        for changes in ({"text": "Another"}, {"level": "alarm"}):
            with self.assertRaisesRegex(NoticeError, "id_content_conflict"):
                self.send(**changes)
        self.transport.assert_called_once()

    def test_busy_unknown_or_unavailable_never_claims(self):
        for state in (False, None, "idle"):
            self.idle.return_value = state
            with self.assertRaisesRegex(NoticeError, "device_not_idle"):
                self.send()
        self.transport.assert_not_called()
        self.idle.return_value = True
        self.assertEqual(self.send()["status"], "accepted")

    def test_expiry_before_send_and_while_reading_idle(self):
        for expiry in (self.now, self.now - 1, self.now + 301):
            with self.assertRaises(NoticeError):
                self.send(expires_at=expiry)
        def slow_read():
            self.now += 121
            return True
        self.idle.side_effect = slow_read
        with self.assertRaisesRegex(NoticeError, "command_expired"):
            self.send()
        self.transport.assert_not_called()

    def test_durable_claim_is_visible_before_transport(self):
        def transport(notice):
            with sqlite3.connect(self.root / "journal" / "notices.sqlite3") as db:
                self.assertEqual(db.execute("SELECT status FROM notices").fetchone()[0], "sending")
            return {"status": "accepted"}
        self.transport.side_effect = transport
        self.send()

    def test_timeout_unknown_blocks_new_id_and_is_never_replayed(self):
        self.transport.side_effect = TimeoutError("private transport detail")
        result = self.send()
        self.assertEqual(result["status"], "unknown")
        self.assertNotIn("private", json.dumps(result))
        self.assertFalse(self.send()["send_attempted"])
        self.now += 61
        with self.assertRaisesRegex(NoticeError, "previous_attempt_needs_review"):
            self.send(id="new")
        self.transport.assert_called_once()
        self.service.review(self.target, "test-1")
        self.transport.side_effect = None
        self.send(id="new")
        self.assertEqual(self.transport.call_count, 2)
        self.assertEqual(self.send()["status"], "unknown")

    def test_crash_sending_claim_survives_restart(self):
        self.transport.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.send()
        self.service = NoticeService(self.root / "journal", self.pictures, lambda: self.now)
        self.assertEqual(self.send()["status"], "unknown")
        self.assertFalse(self.send()["send_attempted"])
        self.transport.assert_called_once()

    def test_rate_and_capacity_are_persistent(self):
        self.send()
        with self.assertRaisesRegex(NoticeError, "rate_limited"):
            self.send(id="second")
        self.now += 60
        self.send(id="second")
        self.now += 60
        with patch.object(module, "MAX_RECORDS", 2), self.assertRaisesRegex(NoticeError, "journal_capacity"):
            self.send(id="third")
        self.assertEqual(self.transport.call_count, 2)

    def test_other_device_has_independent_rate_and_unknown_gate(self):
        self.transport.return_value = {"status": "unknown"}
        self.send()
        other = hashlib.sha256(b"other-device").hexdigest()
        self.service.send(self.payload(), other, self.idle, self.transport)
        self.assertEqual(self.transport.call_count, 2)

    def test_metadata_does_not_contain_text_image_or_serial(self):
        self.send()
        with sqlite3.connect(self.root / "journal" / "notices.sqlite3") as db:
            data = repr(db.execute("SELECT * FROM notices").fetchall())
        self.assertNotIn("Котёл", data)
        self.assertNotIn("synthetic-device", data)
        self.assertEqual((self.root / "journal").stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.root / "journal" / "notices.sqlite3").stat().st_mode & 0o777, 0o600)

    def test_journal_symlink_or_public_permissions_rejected(self):
        directory = self.root / "journal"
        directory.mkdir(mode=0o755)
        directory.chmod(0o755)
        with self.assertRaisesRegex(NoticeError, "journal_directory_not_private"):
            self.send()
        directory.chmod(0o700)
        (directory / "notices.sqlite3").symlink_to(self.root / "other")
        with self.assertRaises(OSError):
            self.send()
        self.transport.assert_not_called()

    def test_jpeg_signature_metadata_progressive_size_and_dimensions(self):
        self.assertEqual(jpeg_info(JPEG)["width"], 1)
        for data in (b"not jpeg", JPEG + b"extra", JPEG[:-2], JPEG * 100,
                     JPEG[:2] + b"\xff\xe1\x00\x04AB" + JPEG[2:], JPEG.replace(b"\xff\xc0", b"\xff\xc2", 1)):
            with self.assertRaises(NoticeError):
                jpeg_info(data)
        changed = bytearray(JPEG)
        offset = changed.index(b"\xff\xc0")
        changed[offset + 7:offset + 9] = (641).to_bytes(2, "big")
        with self.assertRaisesRegex(NoticeError, "dimensions"):
            jpeg_info(bytes(changed))

    def test_picture_basename_symlink_fifo_and_bounded_read(self):
        (self.pictures / "one.jpg").write_bytes(JPEG)
        self.assertEqual(read_picture(self.pictures, "one.jpg"), JPEG)
        (self.pictures / "link.jpg").symlink_to(self.pictures / "one.jpg")
        os.mkfifo(self.pictures / "fifo.jpg")
        for name in ("../one.jpg", "link.jpg", "fifo.jpg"):
            with self.assertRaises((NoticeError, OSError)):
                read_picture(self.pictures, name)
        self.send(picture="one.jpg")
        self.assertEqual(self.transport.call_args.args[0].picture, JPEG)

    def test_changed_picture_with_same_id_is_not_resent(self):
        path = self.pictures / "one.jpg"
        path.write_bytes(JPEG)
        self.send(picture="one.jpg")
        # Change a valid quantization-table byte; structure remains valid.
        other = bytearray(JPEG)
        other[30] ^= 1
        path.write_bytes(other)
        with self.assertRaisesRegex(NoticeError, "id_content_conflict"):
            self.send(picture="one.jpg")
        self.transport.assert_called_once()

    def test_independent_connections_cannot_claim_same_id_twice(self):
        second = NoticeService(self.root / "journal", self.pictures, lambda: self.now)
        def during_send(notice):
            result = second.send(self.payload(), self.target, self.idle, Mock())
            self.assertEqual(result["status"], "unknown")
            self.assertFalse(result["send_attempted"])
            return {"status": "accepted"}
        self.transport.side_effect = during_send
        self.send()
        self.transport.assert_called_once()


if __name__ == "__main__":
    unittest.main()
