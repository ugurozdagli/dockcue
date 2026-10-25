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
        self.details_open = getattr(self, "details_open", False)
        r.geometry("420x" + ("640" if self.details_open else "510"))
        r.resizable(False, False)
        r.configure(fg_color="#0d121a")
        if hasattr(self, "frame"):
            self.frame.destroy()
        card, muted, accent = "#18212d", "#99abc1", "#31d0dc"
        self.frame = f = ctk.CTkFrame(r, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=18, pady=14)

        def label(parent, value, size=12, color="#eef3fa", **kwargs):
            return ctk.CTkLabel(parent, text=value, font=("Segoe UI", size),
                                text_color=color, anchor="w", height=22, **kwargs)

        def panel():
            box = ctk.CTkFrame(f, fg_color=card, corner_radius=12)
            box.pack(fill="x", pady=(0, 8))
            box.grid_columnconfigure(0, weight=1)
            return box

        def switch(parent, variable, command):
            return ctk.CTkSwitch(parent, text="", variable=variable, width=38,
                                switch_width=36, switch_height=20,
                                progress_color=accent, command=command)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        header.grid_columnconfigure(0, weight=1)
        label(header, "DockCue", 24).grid(row=0, column=0, sticky="w")
        self.alive_label = label(header, "● " + self.t("alive"), 11, "#79d9b1")
        self.alive_label.grid(row=0, column=1, sticky="e")
        label(header, "Logitech G ASTRO A50 X", 11, muted).grid(row=1, column=0, sticky="w")
        label(header, "v" + __version__, 10, muted).grid(row=1, column=1, sticky="e")

        status = panel()
        self.base_label = label(status, self.t("base_no"), 12)
        self.base_label.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
        self.battery_label = label(status, "—", 14, accent)
        self.battery_label.grid(row=0, column=1, sticky="e", padx=12, pady=(8, 0))
        self.mic_label = label(status, self.t("mic_wait"), 11, muted)
        self.mic_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=12)
        self.battery_status_label = label(status, "", 11, muted)
        self.battery_status_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 7))

        audio = panel()
        label(audio, self.t("sounds"), 13).grid(row=0, column=0, sticky="w", padx=12, pady=(7, 0))
        self.sound_var = tk.BooleanVar(value=self.settings["sound"])
        switch(audio, self.sound_var, self.toggle_sound).grid(row=0, column=1, padx=12, pady=(7, 0))
        row = ctk.CTkFrame(audio, fg_color="transparent")
        row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(6, 9))
        self.volume_label = label(row, f'{round(self.settings["volume"] * 100)}%', 10, muted, width=32)
        self.volume_label.pack(side="left")
        slider = ctk.CTkSlider(row, from_=2, to=40, number_of_steps=38, height=14,
                              progress_color=accent, button_color=accent, command=self.change_volume)
        slider.set(round(self.settings["volume"] * 100))
        slider.pack(side="left", fill="x", expand=True, padx=(4, 10))
        ctk.CTkButton(row, text=self.t("preview"), width=58, height=25,
                      fg_color="#29394d", font=("Segoe UI", 11), command=self.demo_sounds).pack(side="right")

        media = panel()
        label(media, self.t("media_short"), 13).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))
        self.media_var = tk.BooleanVar(value=self.controller.enabled)
        switch(media, self.media_var, self.toggle_media).grid(row=0, column=1, padx=12, pady=(8, 0))
        self.media_label = label(media, "", 10, muted)
        self.media_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=12)
        controls = ctk.CTkFrame(media, fg_color="transparent")
        controls.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 4))
        self.button_menu = ctk.CTkSegmentedButton(controls, values=["Voice", "Game"], height=29,
                                                 selected_color="#146c79", selected_hover_color="#228c9e",
                                                 command=self.change_button, font=("Segoe UI", 11))
        self.button_menu.set(self.settings["button"].title())
        self.button_menu.pack(side="left")
        self.center_button = ctk.CTkButton(controls, text=self.t("center_mix"), width=150, height=29,
                                          fg_color="#29394d", font=("Segoe UI", 11), command=self.center_mix)
        self.center_button.pack(side="right")
        self.mix_hint = label(media, "", 10, muted)
        self.mix_hint.grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 7))

        self.details_frame = ctk.CTkFrame(f, fg_color=card, corner_radius=12)
        prefs = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        prefs.pack(fill="x", padx=12, pady=(10, 4))
        self.startup_var = tk.BooleanVar(value=startup_enabled())
        ctk.CTkCheckBox(prefs, text=self.t("startup"), variable=self.startup_var,
                        checkbox_width=16, checkbox_height=16, border_width=2,
                        fg_color=accent, text_color="#bfcedd", font=("Segoe UI", 11),
                        command=self.toggle_startup).pack(side="left")
        menu = ctk.CTkOptionMenu(prefs, values=[self.t("system"), "English", "Türkçe"], width=137, height=27,
                                 fg_color="#26364a", button_color="#30435c", font=("Segoe UI", 10),
                                 command=self.change_language)
        menu.set({"auto": self.t("system"), "en": "English", "tr": "Türkçe"}[self.settings["language"]])
        menu.pack(side="right")
        heading = ctk.CTkFrame(self.details_frame, fg_color="transparent")
        heading.pack(fill="x", padx=12)
        self.uptime_label = label(heading, "", 10, muted)
        self.uptime_label.pack(side="left")
        ctk.CTkButton(heading, text=self.t("logs"), width=100, height=24, font=("Segoe UI", 10),
                      fg_color="transparent", command=self.open_log).pack(side="right")
        self.activity_labels = []
        for _ in range(2):
            line = label(self.details_frame, "", 10, muted)
            line.pack(fill="x", padx=12)
            self.activity_labels.append(line)
        if self.details_open:
            self.details_frame.pack(fill="x", pady=(0, 8))

        bottom = ctk.CTkFrame(f, fg_color="transparent")
        bottom.pack(fill="x", pady=(3, 8))
        self.details_button = ctk.CTkButton(bottom, text=self.t("less" if self.details_open else "settings"),
                                           width=110, height=29, fg_color="transparent", hover_color="#202e40",
                                           anchor="w", font=("Segoe UI", 11), command=self.toggle_details)
        self.details_button.pack(side="left")
        ctk.CTkButton(bottom, text=self.t("hide"), width=115, height=29,
                      fg_color="#203246", font=("Segoe UI", 11), command=self.hide_to_tray).pack(side="right")
        self.footer = ctk.CTkFrame(f, fg_color="transparent")
        self.footer.pack(fill="x")
        label(self.footer, self.t("legal_short"), 10, muted).pack(fill="x")
        label(self.footer, self.t("footer_short"), 10, "#76baa9").pack(fill="x")
        icon_file = Path(getattr(sys, "_MEIPASS", application_folder())) / "assets" / "dockcue.ico"
        if icon_file.exists():
            r.iconbitmap(default=str(icon_file))
        self.update_state()
        self.update_media_label()
        self.update_history()

    def toggle_details(self):
        self.details_open = not self.details_open
        if self.details_open:
            self.details_frame.pack(fill="x", pady=(0, 8), before=self.details_button.master)
        else:
            self.details_frame.pack_forget()
        self.details_button.configure(text=self.t("less" if self.details_open else "settings"))
        self.root.geometry("420x" + ("640" if self.details_open else "510"))

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
        fresh = self.state.battery_is_fresh()
        self.battery_label.configure(text=f'{self.t("battery")} {self.state.battery}%' if fresh else "—")
        if not fresh:
            battery_status = self.t("battery_unknown")
        elif self.state.docked:
            battery_status = self.t("battery_full" if self.state.battery == 100 else "battery_charging")
        else:
            battery_status = self.t("battery_undocked")
        self.battery_status_label.configure(text=battery_status)

    def update_media_label(self):
        key = "media_off" if not self.controller.enabled else ("media_ready" if self.media_ready else "media_wait")
        self.media_label.configure(text=self.t(key), text_color="#99abc1")
        self.center_button.configure(state="normal" if self.media_ready else "disabled")
        self.mix_hint.configure(text=self.t("mix_locked" if self.controller.enabled else "mix_free"))

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

    def center_mix(self):
        if self.media_ready:
            self.commands.put(("center", None))
        else:
            self.media_label.configure(text=self.t("media_wait"))

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
                    self.controller.ready(balance, settle_seconds=.75)
                    if self.controller.needs_center(balance):
                        self.controller.center()
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
                        actual = ghub_request(ws, path).get("balance", 0)
                        if actual != value:
                            raise RuntimeError("Mix did not reach the requested position")
                        self.controller.handle(actual)
                    elif command == "center":
                        self.controller.center()
                    elif command == "refresh":
                        initialize()
                    if time.monotonic() >= health:
                        self.controller.handle(ghub_request(ws, path).get("balance", 0))
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
            elif kind == "mix_centered":
                if time.monotonic() - self.last_noted.get("evt_centered", 0) > 2:
                    self.note("evt_centered")
                    self.last_noted["evt_centered"] = time.monotonic()
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
