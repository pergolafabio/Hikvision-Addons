# SPDX-License-Identifier: MIT
# Copyright (c) 2026 giflydimarik-gif
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Bounded local indoor notices. No credentials, login, polling or automatic retry.

MIT-licensed original implementation; see LICENSE in the public companion module.
JPEG validation checks structure, not complete entropy decoding. Use trusted,
normalised images. SDK structures use 32-bit LONG/DWORD and native pointer alignment.
"""
from __future__ import annotations

import ctypes as C
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time
from typing import Callable

NOTICE_COMMAND = 16008
MAX_JPEG_BYTES = 24576
MAX_PAYLOAD_BYTES = 8192
MAX_RECORDS = 4096
MIN_INTERVAL = 60
EXPECTED_ABI = {"LONG": 4, "DWORD": 4, "TIME": 8, "PIC": 48,
                "NOTICE": 1552, "pics_offset": 1136, "res2_offset": 1424}
UNCERTAIN_SDK_ERRORS = {7, 8, 9, 10, 11, 14}

class NoticeError(ValueError):
    pass


def jpeg_info(data: bytes) -> dict:
    """Bounded structural check for one baseline RGB JPEG, without metadata.

    The fixed test asset is additionally decoded by Pillow before publication;
    this lightweight guest check does not claim to be a full entropy decoder.
    """
    if type(data) is not bytes or not 4 <= len(data) <= MAX_JPEG_BYTES:
        raise NoticeError("jpeg_bytes_or_size_invalid")
    if data[:2] != b"\xff\xd8" or data[-2:] != b"\xff\xd9":
        raise NoticeError("jpeg_signature_invalid")
    offset, frame = 2, None
    for unused in range(128):
        if offset + 4 > len(data) or data[offset] != 255:
            raise NoticeError("jpeg_segment_invalid")
        marker = data[offset + 1]
        length = int.from_bytes(data[offset + 2:offset + 4], "big")
        if marker not in {0xE0, 0xDB, 0xC0, 0xC4, 0xDD, 0xDA}:
            raise NoticeError("jpeg_mode_or_metadata_unsupported")
        if length < 2 or offset + length + 2 > len(data):
            raise NoticeError("jpeg_segment_length_invalid")
        payload = data[offset + 4:offset + length + 2]
        offset += length + 2
        if marker == 0xE0 and (len(payload) != 14 or payload[:5] != b"JFIF\x00" or payload[-2:] != b"\x00\x00"):
            raise NoticeError("jpeg_metadata_unsupported")
        if marker == 0xC0:
            if frame is not None or len(payload) != 15 or payload[0] != 8 or payload[5] != 3:
                raise NoticeError("jpeg_frame_unsupported")
            height, width = int.from_bytes(payload[1:3], "big"), int.from_bytes(payload[3:5], "big")
            if not (1 <= width <= 640 and 1 <= height <= 360):
                raise NoticeError("jpeg_dimensions_invalid")
            frame = {"width": width, "height": height}
        elif marker == 0xDA:
            if frame is None or len(payload) != 10 or payload[0] != 3 or payload[-3:] != b"\x00\x3f\x00":
                raise NoticeError("jpeg_scan_unsupported")
            while offset < len(data) - 1:
                index = data.find(b"\xff", offset)
                if index < 0 or index + 1 >= len(data):
                    break
                next_marker = data[index + 1]
                if next_marker == 0 or 0xD0 <= next_marker <= 0xD7:
                    offset = index + 2
                elif next_marker == 0xD9 and index + 2 == len(data):
                    return {**frame, "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                else:
                    raise NoticeError("jpeg_entropy_marker_invalid")
            raise NoticeError("jpeg_scan_incomplete")
    raise NoticeError("jpeg_header_incomplete")


class TimeEx(C.Structure):
    _fields_ = [("wYear", C.c_uint16), ("byMonth", C.c_uint8),
                ("byDay", C.c_uint8), ("byHour", C.c_uint8),
                ("byMinute", C.c_uint8), ("bySecond", C.c_uint8),
                ("byRes", C.c_uint8)]


class NoticePic(C.Structure):
    _fields_ = [("pPicData", C.c_void_p), ("dwPicDataLen", C.c_uint32),
                ("byRes", C.c_uint8 * 32)]


class NoticeData(C.Structure):
    _fields_ = [("dwSize", C.c_uint32), ("struTime", TimeEx),
                ("byNoticeNumber", C.c_uint8 * 32),
                ("byNoticeTheme", C.c_uint8 * 64),
                ("byNoticeDetail", C.c_uint8 * 1024),
                ("byLevel", C.c_uint8), ("byPicNum", C.c_uint8),
                ("byRes1", C.c_uint8 * 2), ("struNoticePic", NoticePic * 6),
                ("byRes2", C.c_uint8 * 128)]


def abi_layout() -> dict:
    return {"LONG": C.sizeof(C.c_int32), "DWORD": C.sizeof(C.c_uint32),
            "TIME": C.sizeof(TimeEx), "PIC": C.sizeof(NoticePic),
            "NOTICE": C.sizeof(NoticeData),
            "pics_offset": NoticeData.struNoticePic.offset,
            "res2_offset": NoticeData.byRes2.offset}


def encoded(text: str, maximum: int, label: str) -> bytes:
    if not isinstance(text, str) or not text.strip():
        raise NoticeError(label + "_empty")
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise NoticeError(label + "_control_character")
    try:
        raw = text.encode("utf-8", "strict")
    except UnicodeError:
        raise NoticeError(label + "_invalid_unicode") from None
    if len(raw) > maximum:
        raise NoticeError(label + "_too_many_utf8_bytes")
    return raw


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise NoticeError("duplicate_json_key")
        result[key] = value
    return result


def parse_request(payload: bytes) -> dict:
    if type(payload) is not bytes or not 1 <= len(payload) <= MAX_PAYLOAD_BYTES:
        raise NoticeError("payload_size_invalid")
    try:
        request = json.loads(payload.decode("utf-8"), object_pairs_hook=_unique_keys)
    except (UnicodeError, ValueError, RecursionError):
        raise NoticeError("json_invalid") from None
    required = {"id", "title", "text", "expires_at"}
    if type(request) is not dict or not required <= request.keys() or request.keys() - required - {"level", "picture"}:
        raise NoticeError("payload_fields_invalid")
    if type(request["id"]) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,30}", request["id"]):
        raise NoticeError("id_invalid")
    encoded(request["title"], 63, "title")
    encoded(request["text"], 1023, "text")
    level = request.get("level", "notice")
    if type(level) is not str or level not in {"notice", "alarm"}:
        raise NoticeError("level_invalid")
    expiry = request["expires_at"]
    if type(expiry) not in (int, float) or not math.isfinite(expiry):
        raise NoticeError("expiry_invalid")
    picture = request.get("picture")
    if picture is not None and (type(picture) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.jpg", picture)):
        raise NoticeError("picture_name_invalid")
    return {**request, "level": level}


def read_picture(directory: Path, name: str) -> bytes:
    # Open the directory and file independently without following symlinks.
    # Basename-only input cannot select another path or a network URL.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.jpg", name):
        raise NoticeError("picture_name_invalid")
    directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or not 4 <= info.st_size <= MAX_JPEG_BYTES:
                raise NoticeError("picture_file_invalid")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                raw = stream.read(MAX_JPEG_BYTES + 1)
        finally:
            os.close(fd)
    finally:
        os.close(directory_fd)
    jpeg_info(raw)
    return raw


@dataclass(frozen=True)
class Notice:
    notice_id: str
    title: str
    text: str
    created_at: datetime
    level: str = "notice"
    picture: bytes | None = None

    def build(self) -> NoticeData:
        if sys.platform != "linux" or sys.byteorder != "little" or abi_layout() != EXPECTED_ABI:
            raise NoticeError("unsupported_abi")
        if type(self.notice_id) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,30}", self.notice_id):
            raise NoticeError("id_invalid")
        title, body = encoded(self.title, 63, "title"), encoded(self.text, 1023, "text")
        if self.level not in ("notice", "alarm"):
            raise NoticeError("level_invalid")
        if not isinstance(self.created_at, datetime) or self.created_at.utcoffset() is None or not 2000 <= self.created_at.year <= 2099:
            raise NoticeError("timestamp_invalid")
        value = NoticeData()
        value.dwSize = C.sizeof(value)
        when = self.created_at
        value.struTime = TimeEx(when.year, when.month, when.day, when.hour, when.minute, when.second, 0)
        for field, raw in (("byNoticeNumber", self.notice_id.encode("ascii")), ("byNoticeTheme", title), ("byNoticeDetail", body)):
            C.memmove(C.addressof(value) + getattr(NoticeData, field).offset, raw, len(raw))
        value.byLevel = 3 if self.level == "alarm" else 4
        if self.picture is not None:
            jpeg_info(self.picture)
            value._picture_buffer = C.create_string_buffer(self.picture, len(self.picture))
            value.byPicNum = 1
            value.struNoticePic[0].pPicData = C.addressof(value._picture_buffer)
            value.struNoticePic[0].dwPicDataLen = len(self.picture)
        return value


def sdk_send(sdk, user_id: int, notice: Notice) -> dict:
    if type(user_id) is not int or not 0 <= user_id <= 2147483647:
        raise NoticeError("sdk_session_invalid")
    block = notice.build()
    # A private function wrapper leaves the existing SDK wrapper/signatures intact.
    if isinstance(sdk, C.CDLL):
        send = C.CFUNCTYPE(C.c_int32, C.c_int32, C.c_uint32, C.c_void_p, C.c_uint32)(("NET_DVR_RemoteControl", sdk))
        last_error = C.CFUNCTYPE(C.c_uint32)(("NET_DVR_GetLastError", sdk))
    else:  # Injectable transport double; never loads a device/library in tests.
        send, last_error = sdk.NET_DVR_RemoteControl, sdk.NET_DVR_GetLastError
    accepted = bool(send(user_id, NOTICE_COMMAND, C.byref(block), C.sizeof(block)))
    error = None if accepted else int(last_error())
    return {"status": "accepted" if accepted else "unknown" if error in UNCERTAIN_SDK_ERRORS else "rejected",
            "device_accepted": accepted, "sdk_error": error}


class NoticeService:
    """One synchronous attempt, with a durable claim before the first SDK write.

    Unknown/in-flight attempts block subsequent IDs for that target until an
    operator reviews them. A review never resends the old ID. No text/image bytes
    or device credentials enter the journal or returned status.
    """

    def __init__(self, journal: Path, picture_directory: Path, clock: Callable = time.time):
        self.journal, self.picture_directory, self.clock = Path(journal), Path(picture_directory), clock

    def _connect(self):
        self.journal.mkdir(parents=True, mode=0o700, exist_ok=True)
        info = self.journal.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_mode & 0o077:
            raise NoticeError("journal_directory_not_private")
        path = self.journal / "notices.sqlite3"
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
                raise NoticeError("journal_file_not_private")
        finally:
            os.close(fd)
        db = sqlite3.connect(path, timeout=0.5, isolation_level=None)
        try:
            db.execute("PRAGMA trusted_schema=OFF")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS notices (target TEXT, id TEXT, digest TEXT, created REAL, "
                       "status TEXT, sdk_error INTEGER, reviewed_at REAL, PRIMARY KEY(target,id))")
        except Exception:
            db.close()
            raise
        return db

    @staticmethod
    def _target(target):
        if type(target) is not str or not re.fullmatch(r"[a-f0-9]{64}", target):
            raise NoticeError("target_fingerprint_invalid")

    def send(self, payload: bytes, target: str, is_idle: Callable, transport: Callable) -> dict:
        request = parse_request(payload)
        self._target(target)
        now = self.clock()
        if not now < request["expires_at"] <= now + 300:
            raise NoticeError("command_expired_or_too_far_ahead")
        picture = read_picture(self.picture_directory, request["picture"]) if request.get("picture") else None
        notice = Notice(request["id"], request["title"], request["text"],
                        datetime.fromtimestamp(now).astimezone(), request["level"], picture)
        notice.build()  # Validate every field, picture and ABI before claiming.
        content = {k: request[k] for k in ("id", "title", "text", "level")}
        content["picture_sha256"] = hashlib.sha256(picture).hexdigest() if picture else None
        digest = hashlib.sha256(json.dumps(content, ensure_ascii=True, sort_keys=True).encode()).hexdigest()
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT digest,status,sdk_error FROM notices WHERE target=? AND id=?", (target, notice.notice_id)).fetchone()
            if old:
                if old[0] != digest:
                    raise NoticeError("id_content_conflict")
                status = "unknown" if old[1] == "sending" else old[1]
                return {"id": notice.notice_id, "status": status, "duplicate": True, "send_attempted": False,
                        "device_accepted": status == "accepted", "sdk_error": old[2]}
            if db.execute("SELECT 1 FROM notices WHERE target=? AND status IN ('sending','unknown') AND reviewed_at IS NULL", (target,)).fetchone():
                raise NoticeError("previous_attempt_needs_review")
            if db.execute("SELECT COUNT(*) FROM notices").fetchone()[0] >= MAX_RECORDS:
                raise NoticeError("journal_capacity_reached")
            last = db.execute("SELECT MAX(created) FROM notices WHERE target=?", (target,)).fetchone()[0]
            if last is not None and now - last < MIN_INTERVAL:
                raise NoticeError("rate_limited")
            # Exact current read; unavailable, unknown and busy all fail closed.
            if is_idle() is not True:
                raise NoticeError("device_not_idle")
            if self.clock() >= request["expires_at"]:
                raise NoticeError("command_expired_or_too_far_ahead")
            db.execute("INSERT INTO notices VALUES (?,?,?,?,?,NULL,NULL)", (target, notice.notice_id, digest, now, "sending"))
            db.execute("COMMIT")  # FULL synchronous commit precedes transport.
            try:
                result = transport(notice)
                if type(result) is not dict or result.get("status") not in {"accepted", "rejected", "unknown"}:
                    raise NoticeError("transport_result_invalid")
                error = result.get("sdk_error")
                if error is not None and (type(error) is not int or not 0 <= error <= 4294967295):
                    raise NoticeError("transport_error_invalid")
            except Exception:
                result = {"status": "unknown", "sdk_error": None}
            try:
                db.execute("UPDATE notices SET status=?,sdk_error=? WHERE target=? AND id=?",
                           (result["status"], result.get("sdk_error"), target, notice.notice_id))
            except sqlite3.Error:
                # The durable sending claim remains: never label this not_sent.
                result = {"status": "unknown", "sdk_error": None}
            return {"id": notice.notice_id, "status": result["status"], "sdk_error": result.get("sdk_error"),
                    "send_attempted": True, "duplicate": False, "device_accepted": result["status"] == "accepted"}
        finally:
            db.close()

    def review(self, target: str, notice_id: str):
        """Admin-only acknowledgement after investigation; retains old ID/status."""
        self._target(target)
        db = self._connect()
        try:
            changed = db.execute("UPDATE notices SET reviewed_at=? WHERE target=? AND id=? "
                                 "AND status IN ('sending','unknown') AND reviewed_at IS NULL",
                                 (self.clock(), target, notice_id)).rowcount
            if changed != 1:
                raise NoticeError("unreviewed_unknown_not_found")
        finally:
            db.close()
