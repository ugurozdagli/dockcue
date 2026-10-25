"""Pure protocol and control logic. No network, files, recording or Win32 imports."""
from dataclasses import dataclass
import math
import threading
import time

VID, PID = 0x046D, 0x0B0B
STATUS_QUERY = bytes([2, 12, 3, 0, 12, 46]) + bytes(58)
BATTERY_QUERY = bytes([2, 12, 3, 0, 6, 12]) + bytes(58)


def parse_packet(data):
    b = bytes(data)
    if len(b) < 7 or b[:2] != b"\x02\x0c" or b[3] != 0:
        return None
    if b[4] == 0x0C and b[2] == 7 and len(b) >= 10:
        return "mic", bool(b[9] & 1)
    if b[4] == 0x0A and b[2] == 4 and 0 <= b[6] <= 12:
        return "mix", b[6]
    if b[4] == 6 and b[2] == 6 and len(b) >= 9 and b[6] <= 100:
        # The station remains present when the headset is docked/off. Battery
        # values may be cached; they are NOT proof of an active radio link.
        return "battery", (b[6], bool(b[8] & 1))
    return None


def choose_language(preference="auto", windows_lang_id=0x0409):
    if preference in ("tr", "en"):
        return preference
    return "tr" if windows_lang_id & 0x03FF == 0x001F else "en"


def clean_settings(data):
    if not isinstance(data, dict):
        data = {}
    try:
        volume = float(data.get("volume", .15))
    except (TypeError, ValueError):
        volume = .15
    if not math.isfinite(volume):
        volume = .15
    return {
        "sound": data.get("sound", True) is not False,
        "media": data.get("media", True) is not False,
        "volume": max(.02, min(.4, volume)),
        "button": data.get("button") if data.get("button") in ("voice", "game") else "voice",
        "language": data.get("language") if data.get("language") in ("auto", "tr", "en") else "auto",
    }


@dataclass
class DeviceState:
    base_present: bool = False
    mic_open: bool | None = None
    battery: int | None = None
    docked: bool | None = None
    battery_at: float = 0
    last_reply_at: float = 0

    def connect(self):
        self.base_present = True
        self.last_reply_at = time.monotonic()

    def disconnect(self):
        self.base_present = False
        self.mic_open = None
        self.battery = None
        self.docked = None
        self.battery_at = 0
        self.last_reply_at = 0

    def update_battery(self, percent, docked, now=None):
        self.battery, self.docked = percent, docked
        self.battery_at = time.monotonic() if now is None else now

    def battery_is_fresh(self, now=None):
        now = time.monotonic() if now is None else now
        return self.base_present and self.battery is not None and now - self.battery_at < 30


class MixController:
    """Map a chosen mix direction to media and ignore our own restoration echo."""
    def __init__(self, restore, toggle, notify):
        self.lock = threading.RLock()
        self.restore, self.toggle, self.notify = restore, toggle, notify
        self.reference = None
        self.pending = None
        self.pending_at = 0
        self.available = False
        self.enabled = True
        self.button = "voice"
        self.last_toggle = -1e9

    def ready(self, balance):
        if not isinstance(balance, int) or not 0 <= balance <= 12:
            raise ValueError("Invalid mix range")
        with self.lock:
            self.reference, self.pending = balance, None
            self.available = True

    def unavailable(self):
        with self.lock:
            self.available = False
            self.reference = self.pending = None

    def handle(self, balance):
        if not isinstance(balance, int) or not 0 <= balance <= 12:
            return
        with self.lock:
            if self.pending is not None:
                if balance == self.pending:
                    self.reference, self.pending = balance, None
                elif time.monotonic() - self.pending_at > 2.5:
                    self.unavailable()
                    self.notify("restore_timeout")
                return
            if self.reference is None:
                self.reference = balance
                return
            previous = self.reference
            if balance == previous:
                return
            chosen = balance < previous if self.button == "voice" else balance > previous
            if not (self.enabled and self.available and chosen):
                self.reference = balance
                return
            self.pending, self.pending_at = previous, time.monotonic()
            self.restore(previous)
            if time.monotonic() - self.last_toggle >= .25:
                self.last_toggle = time.monotonic()
                self.toggle()
                self.notify("media_action", self.button)

    def needs_center(self, balance):
        return self.enabled and ((self.button == "voice" and balance == 0) or
                                 (self.button == "game" and balance == 12))
