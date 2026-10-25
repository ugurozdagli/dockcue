import io
import json
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch

from dockcue.core import (DeviceState, MixController, choose_language,
                          clean_settings, parse_packet)
from dockcue.i18n import TEXT
from dockcue.runtime import allowed_request, read_settings, safe_error, setup_log, tone_wav


class ProtocolTests(unittest.TestCase):
    def test_observed_mic_events_and_query_reply(self):
        for packet, result in [("020c07000c000000000b", True),
                                ("020c07000c000000000a", False),
                                ("020c07000c2e0000000a", False)]:
            self.assertEqual(parse_packet(bytes.fromhex(packet) + bytes(54)), ("mic", result))

    def test_observed_mix_event(self):
        self.assertEqual(parse_packet(bytes.fromhex("020c04000a0005") + bytes(57)), ("mix", 5))

    def test_docked_base_is_not_headset_radio_proof(self):
        packet = bytes.fromhex("020c0600060c5c5f03") + bytes(55)
        self.assertEqual(parse_packet(packet), ("battery", (92, True)))
        state = DeviceState()
        state.connect()
        state.update_battery(92, True, now=100)
        self.assertTrue(state.base_present)
        self.assertTrue(state.docked)
        self.assertTrue(state.battery_is_fresh(now=101))
        self.assertIsNone(state.mic_open)

    def test_cached_battery_expires_and_disconnect_clears_status(self):
        state = DeviceState(base_present=True, mic_open=True)
        state.update_battery(80, False, now=100)
        self.assertFalse(state.battery_is_fresh(now=131))
        state.disconnect()
        self.assertFalse(state.base_present)
        self.assertIsNone(state.mic_open)
        self.assertIsNone(state.battery)

    def test_bad_packets_do_not_change_state(self):
        for data in [b"", b"\x02", bytes.fromhex("020c04000a0010"),
                     bytes.fromhex("020c0600060cff0000"), bytes(64)]:
            self.assertIsNone(parse_packet(data))


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.clock = 100.0
        self.timer = patch("dockcue.core.time.monotonic", side_effect=lambda: self.clock)
        self.timer.start()
        self.addCleanup(self.timer.stop)

    def controller(self, button="voice", balance=6):
        self.restores, self.toggles, self.notices = [], [], []
        c = MixController(self.restores.append, lambda: self.toggles.append(1),
                          lambda *args: self.notices.append(args))
        c.button = button
        c.ready(balance)
        return c

    def test_voice_once_and_delayed_restoration_echo_no_double_toggle(self):
        c = self.controller()
        c.handle(5)
        c.handle(5)
        c.handle(6)
        c.handle(5)  # late HID packet after G HUB acknowledgement
        c.handle(6)
        self.assertEqual(self.toggles, [1])
        self.assertIsNone(c.pending)
        self.clock += .5
        c.handle(5)
        self.assertEqual(self.toggles, [1, 1])
        self.assertTrue(all(x == 6 for x in self.restores))

    def test_game_selected_maps_only_game_and_both_sides_center(self):
        c = self.controller("game")
        c.handle(5)
        self.assertEqual(self.toggles, [])
        self.assertEqual(self.restores, [6])
        c.handle(6)
        self.clock += .5
        c.handle(7)
        self.assertEqual(self.restores, [6, 6])
        self.assertEqual(self.toggles, [1])

    def test_center_never_preserves_old_custom_mix_or_sends_media(self):
        for balance in (0, 3, 8, 12):
            c = self.controller(balance=balance)
            self.assertTrue(c.center())
            c.handle(6)
            self.assertEqual(self.restores, [6])
            self.assertEqual(self.toggles, [])
            self.assertEqual(c.reference, 6)

    def test_manual_move_to_center_does_not_restore_old_position(self):
        c = self.controller(balance=12)
        c.handle(6)
        self.assertEqual(self.restores, [])
        self.assertEqual(self.toggles, [])
        self.assertEqual(c.reference, 6)

    def test_disabled_media_allows_mix_and_manual_center_still_works(self):
        c = self.controller()
        c.enabled = False
        c.handle(12)
        self.assertEqual(self.restores, [])
        c.center()
        c.handle(6)
        self.assertEqual(self.restores, [6])
        self.assertEqual(self.toggles, [])

    def test_disconnected_mode_cannot_send_media_or_center(self):
        c = self.controller()
        c.unavailable()
        self.assertFalse(c.center())
        c.handle(5)
        c.handle(4)
        self.assertEqual(self.restores, [])
        self.assertEqual(self.toggles, [])

    def test_enabled_mode_centers_every_non_center_position(self):
        c = self.controller()
        for balance in range(13):
            self.assertEqual(c.needs_center(balance), balance != 6)
        c.enabled = False
        self.assertFalse(c.needs_center(12))

    def test_invalid_balance_is_rejected(self):
        c = self.controller()
        for value in (-1, 99, True, "6"):
            c.handle(value)
            with self.assertRaises(ValueError):
                c.ready(value)
        self.assertEqual(self.toggles, [])

    def test_startup_baseline_correction_does_not_send_playback_commands(self):
        c = self.controller(balance=12)
        c.ready(12, settle_seconds=.75)
        c.center()
        c.handle(12)
        c.handle(6)
        self.assertEqual(self.toggles, [])
        self.clock += 1
        c.handle(5)
        self.assertEqual(self.toggles, [1])

    def test_failed_restore_disables_control_until_reconnect(self):
        c = self.controller()
        c.center()
        self.clock += 3
        c.handle(12)
        self.assertFalse(c.available)
        self.assertIn(("restore_timeout",), self.notices)
        self.assertEqual(self.toggles, [])


class SettingsAndPrivacyTests(unittest.TestCase):
    def test_language_defaults_to_english_for_every_non_turkish_os(self):
        for lang_id in [0x0409, 0x0407, 0x040C, 0x0411, 0x0809]:
            self.assertEqual(choose_language("auto", lang_id), "en")
        self.assertEqual(choose_language("auto", 0x041F), "tr")
        self.assertEqual(choose_language("en", 0x041F), "en")

    def test_translation_keys_match(self):
        self.assertEqual(set(TEXT["en"]), set(TEXT["tr"]))

    def test_unknown_settings_cannot_supply_urls_paths_or_credentials(self):
        settings = clean_settings({"server": "http://example.invalid", "token": "private", "path": "private"})
        self.assertEqual(set(settings), {"sound", "media", "volume", "button", "language"})

    def test_invalid_and_missing_settings_recover(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertEqual(read_settings(path)["button"], "voice")
            (path / "settings.json").write_text("broken", encoding="utf-8")
            self.assertEqual(read_settings(path)["language"], "auto")
            (path / "settings.json").write_text(json.dumps({"volume": 99, "button": "game"}), encoding="utf-8")
            self.assertEqual(read_settings(path)["volume"], .4)
            self.assertEqual(read_settings(path)["button"], "game")
        self.assertEqual(clean_settings({"volume": float("nan")})["volume"], .15)

    def test_ghub_endpoint_and_payload_allowlist(self):
        path = "/audio/dev00000001/centurion_mix"
        self.assertTrue(allowed_request("/devices/list", "GET"))
        self.assertTrue(allowed_request(path, "SET", {"balance": 6}))
        for endpoint, verb, payload in [("/configuration", "SET", {}),
                                        ("/devices/list", "SET", {}),
                                        (path, "SET", {"balance": 13}),
                                        (path, "SET", {"balance": True}),
                                        (path, "SET", {"balance": 6, "url": "private"}),
                                        ("/audio/../../configuration", "SET", {})]:
            self.assertFalse(allowed_request(endpoint, verb, payload))

    def test_error_log_omits_exception_message_and_personal_path(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = setup_log(Path(directory))
            try:
                raise OSError(r"secret-token C:\Users\private-owner\private-file")
            except OSError as error:
                safe_error(logger, "test_event", error)
            for handler in logger.handlers:
                handler.flush()
            contents = (Path(directory) / "dockcue.log").read_text(encoding="utf-8")
            self.assertIn("OSError", contents)
            self.assertNotIn("secret-token", contents)
            self.assertNotIn("private-owner", contents)
            for handler in list(logger.handlers):
                handler.close()
                logger.removeHandler(handler)

    def test_generated_tones_are_short_mono_pcm(self):
        for opened in (True, False):
            with wave.open(io.BytesIO(tone_wav(opened, .15)), "rb") as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getsampwidth(), 2)
                self.assertAlmostEqual(audio.getnframes() / audio.getframerate(), .26, places=2)


if __name__ == "__main__":
    unittest.main()
