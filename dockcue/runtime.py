"""Windows integration. Outbound IPC is restricted to local G HUB."""
import ctypes
import io
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import os
from pathlib import Path
import re
import socket
import struct
import sys
import time
import uuid
import wave

from .core import clean_settings

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
MIX_PATH = re.compile(r"^/audio/dev[A-Za-z0-9_-]{1,64}/centurion_mix$")


def application_folder():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_folder():
    # Portable storage also avoids packaged-host AppData redirection.
    return application_folder() / "data"


def setup_log(directory):
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("dockcue")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = RotatingFileHandler(directory / "dockcue.log", maxBytes=131072,
                                  backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def safe_error(logger, event, error):
    # Do not include exception messages: OS errors may contain personal paths.
    locations = []
    tb = error.__traceback__
    while tb:
        locations.append(f"{Path(tb.tb_frame.f_code.co_filename).name}:{tb.tb_lineno}")
        tb = tb.tb_next
    logger.error("%s type=%s frames=%s", event, type(error).__name__, ",".join(locations[-5:]))


def read_settings(directory):
    try:
        return clean_settings(json.loads((directory / "settings.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return clean_settings({})


def save_settings(directory, settings):
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / "settings.tmp"
    temporary.write_text(json.dumps(clean_settings(settings), indent=2), encoding="utf-8")
    temporary.replace(directory / "settings.json")


def windows_ui_language():
    if sys.platform != "win32":
        return 0x0409
    return ctypes.windll.kernel32.GetUserDefaultUILanguage()


def startup_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "DockCue")
        enabled = "DockCue.exe" in value and "--tray" in value
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as key:
                state, _ = winreg.QueryValueEx(key, "DockCue")
            enabled = enabled and bool(state) and state[0] in (2, 6)
        except FileNotFoundError:
            pass
        return enabled
    except OSError:
        return False


def set_startup(enabled):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        if enabled:
            executable = application_folder() / "DockCue.exe"
            if not getattr(sys, "frozen", False) or not executable.is_file():
                raise OSError("Startup is supported by the packaged app")
            winreg.SetValueEx(key, "DockCue", 0, winreg.REG_SZ, f'"{executable}" --tray')
        else:
            try:
                winreg.DeleteValue(key, "DockCue")
            except FileNotFoundError:
                pass
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, APPROVED_KEY) as key:
            winreg.SetValueEx(key, "DockCue", 0, winreg.REG_BINARY, bytes([2, 0, 0, 0]) + bytes(8))


def tone_wav(opened, volume):
    rate, samples = 22050, []
    volume = max(.02, min(.4, volume))
    for hz in ((660, 990) if opened else (660, 440)):
        count = int(rate * .105)
        for i in range(count):
            envelope = min(1.0, i / 180, (count - 1 - i) / 240)
            samples.append(int(32767 * volume * envelope * math.sin(2 * math.pi * hz * i / rate)))
        samples.extend([0] * int(rate * .025))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(struct.pack("<" + "h" * len(samples), *samples))
    return buf.getvalue()


def media_toggle():
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ulong, ctypes.c_size_t]
    user.keybd_event(0xB3, 0, 0, 0)
    user.keybd_event(0xB3, 0, 2, 0)


def app_icon(size=128):
    from PIL import Image, ImageDraw
    image = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((2, 2, 126, 126), radius=30, fill="#111923")
    draw.arc((27, 25, 101, 103), 180, 360, fill="#13d7ed", width=9)
    draw.rounded_rectangle((23, 59, 39, 98), radius=7, fill="#13d7ed")
    draw.rounded_rectangle((89, 59, 105, 98), radius=7, fill="#13d7ed")
    draw.line((96, 94, 83, 108, 68, 108), fill="#e8f0f8", width=6)
    draw.ellipse((61, 103, 72, 113), fill="#e8f0f8")
    return image.resize((size, size), Image.Resampling.LANCZOS)


def connect_ghub():
    import websocket
    # A preconnected loopback socket bypasses all HTTP/SOCKS proxy variables.
    sock = socket.create_connection(("127.0.0.1", 9010), timeout=1)
    try:
        return websocket.create_connection("ws://127.0.0.1:9010", socket=sock,
                                          subprotocols=["json"], timeout=.2, suppress_origin=True)
    except Exception:
        sock.close()
        raise


def allowed_request(path, verb, payload=None):
    if path == "/devices/list":
        return verb == "GET" and payload is None
    if not MIX_PATH.fullmatch(path):
        return False
    if verb == "GET":
        return payload is None
    return (verb == "SET" and isinstance(payload, dict) and set(payload) == {"balance"}
            and type(payload["balance"]) is int and 0 <= payload["balance"] <= 12)


def ghub_request(ws, path, verb="GET", payload=None):
    import websocket
    if not allowed_request(path, verb, payload):
        raise ValueError("Request is outside DockCue's local control allowlist")
    message = dict(path=path, verb=verb, msgId=uuid.uuid4().hex)
    if payload is not None:
        message["payload"] = payload
    ws.send(json.dumps(message))
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            raw = ws.recv()
        except websocket.WebSocketTimeoutException:
            continue
        if not raw:
            raise ConnectionError("G HUB closed the connection")
        if len(raw) > 1048576:
            raise ValueError("Unexpected G HUB response size")
        reply = json.loads(raw)
        if reply.get("msgId") == message["msgId"]:
            if reply.get("result", {}).get("code") != "SUCCESS":
                raise RuntimeError("G HUB request failed")
            return reply.get("payload", {})
    raise TimeoutError("G HUB response timed out")
