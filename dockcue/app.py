"""DockCue's Windows application. There is no inbound server or remote control."""
from collections import deque
import ctypes
import os
from pathlib import Path
import queue
import re
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from . import __version__
from .core import (VID, PID, STATUS_QUERY, BATTERY_QUERY, DeviceState,
                   MixController, choose_language, parse_packet)
from .i18n import text
from .runtime import (app_icon, application_folder, connect_ghub, data_folder,
                      ghub_request, media_toggle, read_settings, safe_error,
                      save_settings, set_startup, setup_log, startup_enabled,
                      tone_wav, windows_ui_language)


class App:
    def __init__(self, root, directory, logger, *, hidden=False, show_event=None,
                 quit_event=None, workers=True):
        self.root, self.directory, self.log = root, directory, logger
        self.settings = read_settings(directory)
        self.language = choose_language(self.settings["language"], windows_ui_language())
        self.stop = threading.Event()
        self.events, self.commands, self.sounds = queue.Queue(), queue.Queue(), queue.Queue()
        self.state = DeviceState()
        self.started = time.monotonic()
        self.history = deque(maxlen=2)
        self.media_ready = False
        self.tray = None
        self.tray_ready = threading.Event()
        self.hidden = hidden
        self.show_event, self.quit_event = show_event, quit_event
        self.last_heartbeat = self.started
        self.last_status_second = -1
        self.save_job = None
        self.last_noted = {}
        self.controller = MixController(lambda value: self.commands.put(("restore", value)),
                                        media_toggle, self.emit)
        self.controller.enabled = self.settings["media"]
        self.controller.button = self.settings["button"]
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.root.bind("<Unmap>", self.on_minimize)
        self.root.report_callback_exception = self.tk_error
        self.threads = []
        if workers:
            for func in (self.hid_worker, self.ghub_worker, self.sound_worker, self.tray_worker):
                thread = threading.Thread(target=self.supervise, args=(func,), daemon=True,
                                          name=func.__name__)
                self.threads.append(thread)
                thread.start()
        if (directory / "session.flag").exists():
            self.log.warning("previous_session_unclean")
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "session.flag").write_text("running", encoding="ascii")
        self.note("evt_start")
        self.log.info("version=%s language=%s", __version__, self.language)
        self.root.after(80, self.refresh)
        if not hidden:
            self.root.after(100, self.show_window)

    def t(self, key):
        return text(self.language, key)

    def emit(self, kind, value=None):
        self.events.put((kind, value))

    def note(self, key):
        self.history.append((time.strftime("%H:%M:%S"), key))
        self.log.info("%s", key)
        if hasattr(self, "activity_labels"):
            self.update_history()

    def supervise(self, function):
        while not self.stop.is_set():
            try:
                function()
            except Exception as error:
                safe_error(self.log, "worker_error_" + function.__name__, error)
                self.emit("recoverable_error")
            if not self.stop.is_set():
                self.stop.wait(2)

    def tk_error(self, exc_type, error, traceback):
        safe_error(self.log, "ui_callback_error", error)
        self.note("evt_error")

    def build_ui(self):
        r = self.root
        r.title("DockCue")
        r.geometry("500x782")
        r.resizable(False, False)
        r.configure(fg_color="#0c1118")
        if hasattr(self, "frame"):
            self.frame.destroy()
        bg, card, muted, accent = "#0c1118", "#171f2a", "#8fa0b5", "#20d3e6"
        self.frame = f = ctk.CTkFrame(r, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=24, pady=20)

        def label(parent, value, size=12, color="#eef3fa", **kwargs):
            return ctk.CTkLabel(parent, text=value, font=("Segoe UI", size),
                                text_color=color, anchor="w", **kwargs)

        def switch(parent, variable, command):
            return ctk.CTkSwitch(parent, text="", variable=variable, width=42,
                                  switch_width=40, switch_height=22,
                                  progress_color=accent, command=command)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0, 13))
        label(header, "DockCue", 27).grid(row=0, column=0, sticky="w")
        self.alive_label = label(header, "● " + self.t("alive"), 11, "#72dcb9")
        self.alive_label.grid(row=0, column=1, sticky="e")
        header.grid_columnconfigure(0, weight=1)
        label(header, "Logitech G Astro A50 X", 12, muted).grid(row=1, column=0, columnspan=2, sticky="w")
        status = ctk.CTkFrame(f, fg_color=card, corner_radius=15)
        status.pack(fill="x", pady=(0, 10))
        status.grid_columnconfigure(0, weight=1)
        self.base_label = label(status, self.t("base_no"), 14)
        self.base_label.grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        self.battery_label = label(status, "—", 13, accent)
        self.battery_label.grid(row=0, column=1, padx=16, pady=(12, 0))
        self.mic_label = label(status, self.t("mic_wait"), 11, muted)
        self.mic_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=16)
        self.battery_note = label(status, self.t("battery_note"), 10, "#72859c", wraplength=410)
        self.battery_note.grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(1, 11))
        audio = ctk.CTkFrame(f, fg_color=card, corner_radius=15)
        audio.pack(fill="x", pady=(0, 10))
        audio.grid_columnconfigure(0, weight=1)
        label(audio, self.t("sounds"), 14).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        label(audio, self.t("sounds_sub"), 11, muted).grid(row=1, column=0, sticky="w", padx=16)
        self.sound_var = tk.BooleanVar(value=self.settings["sound"])
        switch(audio, self.sound_var, self.toggle_sound).grid(row=0, column=1, rowspan=2, padx=16)
        row = ctk.CTkFrame(audio, fg_color="transparent")
        row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 12))
        self.volume_label = label(row, f'{round(self.settings["volume"] * 100)}%', 11, muted, width=38)
        self.volume_label.pack(side="left")
        slider = ctk.CTkSlider(row, from_=2, to=40, number_of_steps=38, height=16,
                              progress_color=accent, button_color=accent, command=self.change_volume)
        slider.set(round(self.settings["volume"] * 100))
        slider.pack(side="left", fill="x", expand=True, padx=(5, 12))
        ctk.CTkButton(row, text=self.t("preview"), width=66, height=27, corner_radius=7,
                      fg_color="#29384a", hover_color="#354b62", font=("Segoe UI", 11),
                      command=self.demo_sounds).pack(side="right")
        media = ctk.CTkFrame(f, fg_color=card, corner_radius=15)
        media.pack(fill="x", pady=(0, 12))
        media.grid_columnconfigure(0, weight=1)
        label(media, self.t("media"), 14).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 0))
        self.media_label = label(media, "", 11, muted)
        self.media_label.grid(row=1, column=0, sticky="w", padx=16)
        self.media_var = tk.BooleanVar(value=self.controller.enabled)
        switch(media, self.media_var, self.toggle_media).grid(row=0, column=1, rowspan=2, padx=16)
        label(media, self.t("button"), 11, muted).grid(row=2, column=0, sticky="w", padx=16, pady=(8, 12))
        self.button_menu = ctk.CTkSegmentedButton(media, values=["Voice", "Game"], width=150,
                                                 selected_color="#176c7c", selected_hover_color="#228c9e",
                                                 command=self.change_button, font=("Segoe UI", 11))
        self.button_menu.set(self.settings["button"].title())
        self.button_menu.grid(row=2, column=1, sticky="e", padx=16, pady=(8, 12))
        prefs = ctk.CTkFrame(f, fg_color="transparent")
        prefs.pack(fill="x", pady=(0, 10))
        self.startup_var = tk.BooleanVar(value=startup_enabled())
        ctk.CTkCheckBox(prefs, text=self.t("startup"), variable=self.startup_var,
                        checkbox_width=18, checkbox_height=18, border_width=2,
                        fg_color=accent, text_color="#bfcedd", font=("Segoe UI", 11),
                        command=self.toggle_startup).pack(side="left")
        language_values = [self.t("system"), "English", "Türkçe"]
        menu = ctk.CTkOptionMenu(prefs, values=language_values, width=143, height=29,
                                 fg_color="#202d3c", button_color="#2a3a4e",
                                 font=("Segoe UI", 11), command=self.change_language)
        menu.set({"auto": self.t("system"), "en": "English", "tr": "Türkçe"}[self.settings["language"]])
        menu.pack(side="right")
        activity = ctk.CTkFrame(f, fg_color=card, corner_radius=12)
        activity.pack(fill="x", pady=(0, 10))
        heading = ctk.CTkFrame(activity, fg_color="transparent")
        heading.pack(fill="x", padx=14, pady=(7, 0))
        self.uptime_label = label(heading, "", 10, muted)
        self.uptime_label.pack(side="left")
        ctk.CTkButton(heading, text=self.t("logs"), width=105, height=23, font=("Segoe UI", 10),
                      fg_color="transparent", hover_color="#28384c", command=self.open_log).pack(side="right")
        self.activity_labels = []
        for _ in range(2):
            line = label(activity, "", 10, "#a9bbce", height=19)
            line.pack(fill="x", padx=14)
            self.activity_labels.append(line)
        footer = ctk.CTkFrame(f, fg_color="transparent")
        footer.pack(fill="x")
        label(footer, self.t("privacy"), 10, "#72c8b1").pack(fill="x")
        label(footer, self.t("unofficial") + " " + self.t("independent"), 10, muted, wraplength=450).pack(fill="x")
        label(footer, self.t("ai"), 10, muted).pack(fill="x")
        bottom = ctk.CTkFrame(f, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", pady=(8, 0))
        label(bottom, "v" + __version__, 10, "#61768f").pack(side="left")
        ctk.CTkButton(bottom, text=self.t("hide"), width=130, height=30, corner_radius=8,
                      fg_color="#203246", hover_color="#2b4861", font=("Segoe UI", 11),
                      command=self.hide_to_tray).pack(side="right")
        icon_file = Path(getattr(sys, "_MEIPASS", application_folder())) / "assets" / "dockcue.ico"
        if icon_file.exists():
            r.iconbitmap(default=str(icon_file))
        self.update_state()
        self.update_media_label()
        self.update_history()

    def update_history(self):
        rows = list(self.history)
        for i, label in enumerate(self.activity_labels):
            label.configure(text=(rows[i][0] + "  " + self.t(rows[i][1])) if i < len(rows) else "")

    def update_state(self):
        present = self.state.base_present
        self.base_label.configure(text=self.t("base_yes" if present else "base_no"),
                                   text_color="#eaf3fc" if present else "#e9b974")
        if self.state.docked and self.state.battery_is_fresh():
            line = self.t("docked")
        elif self.state.mic_open is None:
            line = self.t("mic_wait")
        else:
            line = self.t("last_mic") + ": " + self.t("mic_on" if self.state.mic_open else "mic_off")
        self.mic_label.configure(text=line)
        self.battery_label.configure(text=f"{self.state.battery}%" if self.state.battery_is_fresh() else "—")

    def update_media_label(self):
        key = "media_off" if not self.controller.enabled else ("media_ready" if self.media_ready else "media_wait")
        self.media_label.configure(text=self.t(key), text_color="#8fa0b5")

    def change_language(self, value):
        self.settings["language"] = {"English": "en", "Türkçe": "tr"}.get(value, "auto")
        self.language = choose_language(self.settings["language"], windows_ui_language())
        self.persist()
        # Let the native menu finish its focus/unpost callbacks before replacing
        # widgets. Destroying them inside the menu callback can raise TclError.
        self.root.after(350, self.rebuild_language_ui)

    def rebuild_language_ui(self):
        if self.stop.is_set():
            return
        self.build_ui()
        if self.tray:
            self.tray.menu = self.tray_menu()
            self.tray.update_menu()

    def persist(self):
        try:
            save_settings(self.directory, self.settings)
        except OSError as error:
            safe_error(self.log, "settings_write_error", error)

    def toggle_sound(self):
        self.settings["sound"] = self.sound_var.get()
        self.persist()
        if self.tray:
            self.tray.update_menu()

    def toggle_media(self):
        with self.controller.lock:
            self.controller.enabled = self.media_var.get()
        self.settings["media"] = self.controller.enabled
        self.commands.put(("refresh", None))
        self.update_media_label()
        self.persist()
        if self.tray:
            self.tray.update_menu()

    def change_button(self, value):
        value = value.lower()
        if value not in ("voice", "game"):
            return
        with self.controller.lock:
            self.controller.button = value
        self.settings["button"] = value
        self.commands.put(("refresh", None))
        self.log.info("media_button=%s", value)
        self.persist()

    def change_volume(self, value):
        self.settings["volume"] = round(float(value)) / 100
        self.volume_label.configure(text=f'{round(self.settings["volume"] * 100)}%')
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(250, self.persist)

    def toggle_startup(self):
        try:
            set_startup(self.startup_var.get())
            self.log.info("startup_enabled=%s", self.startup_var.get())
        except OSError as error:
            safe_error(self.log, "startup_setting_error", error)
            self.startup_var.set(startup_enabled())
            messagebox.showerror("DockCue", self.t("startup_error"), parent=self.root)

    def open_log(self):
        os.startfile(str(self.directory / "dockcue.log"))

    def demo_sounds(self):
        self.sounds.put(True)
        self.sounds.put(False)

    def tray_menu(self):
        import pystray
        return pystray.Menu(
            pystray.MenuItem(self.t("open"), lambda icon, item: self.emit("show"), default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.t("sounds"), lambda icon, item: self.emit("toggle_sound"),
                             checked=lambda item: self.settings["sound"]),
            pystray.MenuItem(self.t("media"), lambda icon, item: self.emit("toggle_media"),
                             checked=lambda item: self.controller.enabled),
            pystray.MenuItem(self.t("logs"), lambda icon, item: self.emit("open_log")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(self.t("exit"), lambda icon, item: self.emit("exit")))

    def tray_worker(self):
        import pystray
        self.tray = pystray.Icon("DockCue", app_icon(64), "DockCue", menu=self.tray_menu())
        def setup(icon):
            icon.visible = True
            self.tray_ready.set()
            self.emit("tray_ready")
        self.tray.run(setup=setup)
        if not self.stop.is_set():
            self.tray_ready.clear()
            self.emit("tray_error")

    def hide_to_tray(self):
        if self.tray_ready.is_set():
            self.root.withdraw()
            self.note("evt_hidden")
        else:
            self.root.iconify()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.note("evt_shown")

    def on_minimize(self, event):
        if event.widget == self.root and self.root.state() == "iconic":
            self.root.after(0, self.hide_to_tray)

    def sound_worker(self):
        import winsound
        while not self.stop.is_set():
            try:
                opened = self.sounds.get(timeout=.2)
            except queue.Empty:
                continue
            try:
                winsound.PlaySound(tone_wav(opened, self.settings["volume"]),
                                   winsound.SND_MEMORY | winsound.SND_NODEFAULT)
            except Exception as error:
                safe_error(self.log, "sound_error", error)
                self.emit("recoverable_error")

    def hid_worker(self):
        import hid
        last_present = None
        while not self.stop.is_set():
            device = None
            try:
                matches = [d for d in hid.enumerate(VID, PID)
                           if d["usage_page"] == 0xFF32 and d["usage"] == 0x74]
                if not matches:
                    if last_present is not False:
                        self.emit("base_missing")
                        last_present = False
                    self.stop.wait(2)
                    continue
                device = hid.device()
                device.open_path(matches[0]["path"])
                self.emit("base_connected")
                last_present = True
                previous_mic = None
                next_status = next_battery = 0
                last_reply = time.monotonic()
                while not self.stop.is_set():
                    now = time.monotonic()
                    if now >= next_status:
                        device.write(STATUS_QUERY)
                        next_status = now + 1
                    if now >= next_battery:
                        device.write(BATTERY_QUERY)
                        next_battery = now + 10
                    data = device.read(64, 150)
                    if data:
                        last_reply = time.monotonic()
                    if time.monotonic() - last_reply > 8:
                        raise TimeoutError("Base did not reply")
                    parsed = parse_packet(data)
                    if not parsed:
                        continue
                    kind, value = parsed
                    if kind == "mic" and value != previous_mic:
                        initial = previous_mic is None
                        previous_mic = value
                        self.emit("mic", (value, initial))
                        if not initial and self.settings["sound"]:
                            self.sounds.put(value)
                    elif kind == "mix":
                        self.controller.handle(value)
                    elif kind == "battery":
                        self.emit("battery", value)
            except Exception as error:
                safe_error(self.log, "base_retry", error)
                self.controller.unavailable()
                self.emit("base_missing")
                last_present = False
                self.stop.wait(2)
            finally:
                if device:
                    device.close()

    def ghub_worker(self):
        reported = None
        while not self.stop.is_set():
            ws = None
            try:
                ws = connect_ghub()
                listing = ghub_request(ws, "/devices/list")
                dev = next(d for d in listing.get("deviceInfos", [])
                           if d.get("deviceBaseModel") == "a50_x" and d.get("state") == "ACTIVE"
                           and re.fullmatch(r"dev[A-Za-z0-9_-]{1,64}", d.get("id", "")))
                path = f'/audio/{dev["id"]}/centurion_mix'
                def initialize():
                    balance = ghub_request(ws, path).get("balance", 0)
                    if self.controller.needs_center(balance):
                        balance = 6
                        ghub_request(ws, path, "SET", {"balance": balance})
                    # Initial G HUB/HID replies can arrive out of order. Let
                    # their baseline settle without emitting a media key.
                    self.controller.ready(balance, settle_seconds=.75)
                initialize()
                if reported is not True:
                    self.emit("ghub_ready")
                    reported = True
                health = time.monotonic() + 5
                while not self.stop.is_set() or not self.commands.empty():
                    try:
                        command, value = self.commands.get(timeout=.15)
                    except queue.Empty:
                        command = None
                    if command == "restore":
                        restored = ghub_request(ws, path, "SET", {"balance": value})
                        if restored.get("balance", 0) != value:
                            raise RuntimeError("Mix restoration was not acknowledged")
                        self.controller.handle(value)
                    elif command == "refresh":
                        initialize()
                    if time.monotonic() >= health:
                        ghub_request(ws, path)
                        health = time.monotonic() + 5
            except Exception as error:
                self.controller.unavailable()
                if reported is not False:
                    safe_error(self.log, "ghub_retry", error)
                    self.emit("ghub_missing")
                    reported = False
                self.stop.wait(2)
            finally:
                if ws:
                    try:
                        ws.close()
                    except Exception:
                        pass

    def refresh(self):
        if self.show_event or self.quit_event:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            if self.quit_event and kernel.WaitForSingleObject(self.quit_event, 0) == 0:
                self.exit_app()
                return
            if self.show_event and kernel.WaitForSingleObject(self.show_event, 0) == 0:
                self.show_window()
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "base_connected":
                if not self.state.base_present:
                    self.note("evt_base_yes")
                self.state.connect()
                self.commands.put(("refresh", None))
                self.update_state()
            elif kind == "base_missing":
                if self.state.base_present:
                    self.note("evt_base_no")
                self.state.disconnect()
                self.update_state()
            elif kind == "mic":
                opened, initial = value
                self.state.mic_open = opened
                if not initial:
                    self.note("evt_mic_on" if opened else "evt_mic_off")
                self.update_state()
            elif kind == "battery":
                percent, docked = value
                old = self.state.docked
                self.state.update_battery(percent, docked)
                if old != docked:
                    self.note("evt_dock" if docked else "evt_undock")
                self.update_state()
            elif kind == "ghub_ready":
                self.media_ready = True
                self.note("evt_ghub_yes")
                self.update_media_label()
            elif kind == "ghub_missing":
                self.media_ready = False
                self.note("evt_ghub_no")
                self.update_media_label()
            elif kind == "media_action":
                self.note("evt_media")
                self.media_label.configure(text=self.t("media_action"), text_color="#72dcb9")
            elif kind in ("recoverable_error", "restore_timeout"):
                self.note("evt_error")
            elif kind == "show":
                self.show_window()
            elif kind == "toggle_sound":
                self.sound_var.set(not self.settings["sound"])
                self.toggle_sound()
            elif kind == "toggle_media":
                self.media_var.set(not self.controller.enabled)
                self.toggle_media()
            elif kind == "open_log":
                self.open_log()
            elif kind == "tray_ready":
                self.log.info("tray_ready")
                if self.hidden:
                    self.root.withdraw()
            elif kind == "tray_error":
                self.show_window()
                self.log.warning("tray_unavailable")
            elif kind == "exit":
                self.exit_app()
                return
        elapsed = int(time.monotonic() - self.started)
        if elapsed != self.last_status_second:
            self.last_status_second = elapsed
            self.alive_label.configure(text="● " + self.t("alive"),
                                       text_color="#72dcb9" if elapsed % 2 else "#40967c")
            self.uptime_label.configure(text=f'{self.t("uptime")}: {elapsed // 60}m {elapsed % 60:02d}s')
            if self.tray:
                self.tray.title = "DockCue · " + self.t("alive")
            self.update_state()
        if time.monotonic() - self.last_heartbeat > 300:
            self.log.info("heartbeat uptime_seconds=%s", elapsed)
            self.last_heartbeat = time.monotonic()
        if not self.stop.is_set():
            self.root.after(80, self.refresh)

    def exit_app(self):
        self.persist()
        self.note("evt_exit")
        self.stop.set()
        for thread in self.threads:
            thread.join(.3)
        if self.tray:
            self.tray.stop()
        (self.directory / "session.flag").unlink(missing_ok=True)
        self.root.destroy()


def main():
    if sys.platform != "win32":
        raise SystemExit("DockCue requires Windows")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    mutex = kernel.CreateMutexW(None, False, "Local\\DockCue.Instance")
    if not mutex:
        raise OSError("Could not create the application mutex")
    if ctypes.get_last_error() == 183:
        if "--tray" not in sys.argv:
            kernel.OpenEventW.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_wchar_p]
            kernel.OpenEventW.restype = ctypes.c_void_p
            name = "Local\\DockCue.Quit" if "--quit" in sys.argv else "Local\\DockCue.Show"
            event = kernel.OpenEventW(2, False, name)
            if event:
                kernel.SetEvent.argtypes = [ctypes.c_void_p]
                kernel.SetEvent(event)
        return
    if "--quit" in sys.argv:
        return
    directory = data_folder()
    logger = setup_log(directory)
    kernel.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.CreateEventW.restype = ctypes.c_void_p
    show = kernel.CreateEventW(None, False, False, "Local\\DockCue.Show")
    quit_event = kernel.CreateEventW(None, False, False, "Local\\DockCue.Quit")
    try:
        ctk.set_appearance_mode("dark")
        root = ctk.CTk()
        root.withdraw()
        App(root, directory, logger, hidden="--tray" in sys.argv,
            show_event=show, quit_event=quit_event)
        root.mainloop()
    except Exception as error:
        safe_error(logger, "fatal_error", error)
        # Keep private OS exception messages out of the dialog and log.
        messagebox.showerror("DockCue", "DockCue stopped. See data/dockcue.log for the local error record.")
        raise SystemExit(1)
    finally:
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        for handle in (show, quit_event, mutex):
            if handle:
                kernel.CloseHandle(handle)
