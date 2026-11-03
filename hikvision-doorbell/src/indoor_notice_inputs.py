"""HA notice controls; editing a draft never sends a device command.

Draft text stays in memory. MQTT state echoes are non-retained and bypass the
discovery library's value-logging helpers. HA itself may record entity history.
"""
import json
import threading
import time
import uuid

from ha_mqtt_discoverable import Settings
from ha_mqtt_discoverable.sensors import Button, ButtonInfo, Text, TextInfo, Select, SelectInfo, Sensor, SensorInfo
from indoor_notice import NoticeError, parse_request


class NoticeSendButton(Button):
    """Restore non-retained draft states when the shared client reconnects."""

    def set_availability(self, available):
        super().set_availability(available)
        if available and hasattr(self, "notice_inputs"):
            self.notice_inputs.refresh()


class NoticeInputs:
    """One current draft per exact indoor device; no persistent message content."""

    TEXT_FIELDS = {"title": ("Notice title", 63), "text": ("Notice text", 255), "picture": ("Notice JPEG", 68)}

    def __init__(self, mqtt_settings, device, name, doorbell, send, report, register, clock=time.time):
        self.client = mqtt_settings.client
        self.clock, self.send, self.report = clock, send, report
        self.lock = threading.RLock()
        self.fields = {"title": "", "text": "", "picture": "", "level": "notice"}
        self.invalid_fields = set()
        self.created_at = self.clock()
        self.notice_id = self._new_id()
        self.entities = {}
        self.last_result = {"status": "idle"}
        self.ready = False
        for key, (label, maximum) in self.TEXT_FIELDS.items():
            info = TextInfo(name=label, unique_id=f"{name}_notice_{key}", device=device,
                            icon="mdi:image" if key == "picture" else "mdi:format-text",
                            min=0, max=maximum, retain=False)
            settings = Settings(mqtt=mqtt_settings, entity=info, manual_availability=True, user_data=doorbell)

            def edit(client, userdata, message, field=key):
                self.edit(field, message)

            entity = Text(settings, edit)
            self.entities[key] = entity
            entity.set_availability(True)
            register(entity)

        info = SelectInfo(name="Notice type", unique_id=f"{name}_notice_level", device=device,
                          icon="mdi:message-alert", options=["notice", "alarm"], retain=False)
        settings = Settings(mqtt=mqtt_settings, entity=info, manual_availability=True, user_data=doorbell)
        entity = Select(settings, lambda client, userdata, message: self.edit("level", message))
        self.entities["level"] = entity
        entity.set_availability(True)
        register(entity)

        info = SensorInfo(name="Notice result", unique_id=f"{name}_notice_result", device=device, icon="mdi:message-check")
        settings = Settings(mqtt=mqtt_settings, entity=info, manual_availability=True, user_data=doorbell)
        self.result = Sensor(settings)
        self.result.set_availability(True)
        register(self.result)

        info = ButtonInfo(name="Send notice", unique_id=f"{name}_send_notice", device=device,
                          icon="mdi:message-arrow-right", payload_press=self._press_payload(), retain=False)
        settings = Settings(mqtt=mqtt_settings, entity=info, manual_availability=True, user_data=doorbell)
        self.button = NoticeSendButton(settings, lambda client, userdata, message: self.press(message))
        self.button.notice_inputs = self
        self.ready = True
        self.button.set_availability(True)
        register(self.button)

    @staticmethod
    def _new_id():
        return "ha-" + uuid.uuid4().hex[:28]

    def _press_payload(self):
        return "SEND " + self.notice_id

    def _payload(self, validation=False):
        data = {"id": self.notice_id, "title": self.fields["title"], "text": self.fields["text"],
                "level": self.fields["level"], "expires_at": self.created_at + 300}
        if validation:
            # Empty fields are valid while editing, but never while sending.
            data["title"] = data["title"] or "Notice"
            data["text"] = data["text"] or "Draft"
        if self.fields["picture"]:
            data["picture"] = self.fields["picture"]
        return json.dumps(data, ensure_ascii=True).encode("utf-8")

    def _new_revision(self):
        self.notice_id = self._new_id()
        self.created_at = self.clock()
        # HA's button publishes the current discovery payload. A stale queued
        # press carries an old revision and cannot send a newer draft.
        self.button._entity.payload_press = self._press_payload()
        self.button.write_config()

    def _failure(self, reason):
        result = {"status": "not_sent", "reason": reason, "send_attempted": False}
        self.report(result)
        return result

    def edit(self, field, message):
        with self.lock:
            if not self.ready or field not in self.fields:
                return self._failure("draft_not_ready")
            if message.retain or getattr(message, "dup", False):
                return self._failure("replayed_edit_rejected")
            try:
                maximum = self.TEXT_FIELDS.get(field, (None, 8))[1]
                if type(message.payload) is not bytes or len(message.payload) > maximum * 4:
                    raise NoticeError("field_size_invalid")
                value = message.payload.decode("utf-8", "strict")
                if len(value) > maximum:
                    raise NoticeError("field_size_invalid")
                previous = self.fields[field]
                self.fields[field] = value
                try:
                    parse_request(self._payload(validation=True))
                except (ValueError, UnicodeError, TypeError):
                    self.fields[field] = previous
                    raise NoticeError("draft_field_invalid") from None
            except (ValueError, UnicodeError, TypeError):
                self.invalid_fields.add(field)
                return self._failure("draft_field_invalid")
            self.invalid_fields.discard(field)
            self._new_revision()
            self._publish_field(field)
            return {"status": "draft_updated", "send_attempted": False}

    def press(self, message):
        with self.lock:
            if not self.ready:
                return self._failure("draft_not_ready")
            if message.retain or getattr(message, "dup", False):
                return self._failure("replayed_press_rejected")
            if message.payload != self._press_payload().encode("ascii"):
                return self._failure("stale_draft_press_rejected")
            if self.invalid_fields:
                return self._failure("draft_field_invalid")
            if not self.created_at <= self.clock() < self.created_at + 300:
                return self._failure("draft_expired")
            try:
                payload = self._payload()
                parse_request(payload)
            except (ValueError, UnicodeError, TypeError):
                return self._failure("draft_incomplete")
            result = self.send(payload)
            if result.get("status") == "accepted":
                # A successful press consumes the text; a new message requires
                # an explicit edit. The durable sender retains the old ID too.
                self.fields["text"] = ""
                self._new_revision()
                self._publish_field("text")
            return result

    def _publish_field(self, field):
        entity = self.entities[field]
        if not entity.wrote_configuration:
            entity.write_config()
        # Text.set_text and Discoverable._update_state log private values.
        self.client.publish(entity.state_topic, self.fields[field], retain=False)

    def publish_result(self, result):
        with self.lock:
            self.last_result = {key: value for key, value in result.items()
                                if key in {"status", "id", "reason", "send_attempted", "device_accepted", "sdk_error", "duplicate"}}
            self._publish_result()

    def _publish_result(self):
        if not self.result.wrote_configuration:
            self.result.write_config()
        self.client.publish(self.result.state_topic, self.last_result["status"], retain=False)
        self.client.publish(self.result.attributes_topic, json.dumps(self.last_result), retain=False)

    def refresh(self):
        with self.lock:
            for field in self.fields:
                self._publish_field(field)
            self._publish_result()
