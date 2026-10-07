import os
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from notify_mcp import server

LISTING = "Samantha    en_US    # Hello.\nDaniel    en_GB    # Hello.\nLuciana    pt_BR    # Olá.\n"


class VoiceSelectionTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop("NOTIFY_VOICE", None)
        cache = patch.object(server, "_voice_cache", None)
        cache.start()
        self.addCleanup(cache.stop)

    def test_call_voice_overrides_environment_and_does_not_advance_rotation(self):
        with (
            patch.object(server, "PLATFORM", "mac"),
            patch.dict(os.environ, {"NOTIFY_VOICE": "Daniel"}),
            patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=LISTING)),
            patch.object(server, "next_mac_voice") as rotation,
            patch.object(server, "_speak") as speak,
        ):
            result = server.notify([{"text": "Done.", "pause_after": 0}], voice="Samantha")
        speak.assert_called_once_with("Samantha", "Done.")
        rotation.assert_not_called()
        self.assertIsNone(server._voice_cache)
        self.assertIn("Samantha", result)

    def test_environment_voice_is_used_for_every_call(self):
        with (
            patch.object(server, "PLATFORM", "mac"),
            patch.dict(os.environ, {"NOTIFY_VOICE": "Daniel"}),
            patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=LISTING)),
        ):
            self.assertEqual(server.pick_voice(), "Daniel")
            self.assertEqual(server.pick_voice(), "Daniel")

    def test_explicit_foreign_voice_is_allowed(self):
        with (
            patch.object(server, "PLATFORM", "mac"),
            patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=LISTING)),
        ):
            self.assertEqual(server.pick_voice("Luciana"), "Luciana")

    def test_named_voice_overrides_cached_session_default(self):
        with (
            patch.object(server, "PLATFORM", "mac"),
            patch.object(server, "_voice_cache", "Daniel"),
            patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=LISTING)),
        ):
            self.assertEqual(server.pick_voice("Samantha"), "Samantha")
            self.assertEqual(server.pick_voice(), "Daniel")

    def test_missing_named_voice_reports_error_without_speech_or_rotation(self):
        with (
            patch.object(server, "PLATFORM", "mac"),
            patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=LISTING)),
            patch.object(server, "next_mac_voice") as rotation,
            patch.object(server, "_speak") as speak,
        ):
            result = server.notify([{"text": "Done."}], voice="Missing")
        self.assertIn("not installed", result)
        speak.assert_not_called()
        rotation.assert_not_called()

    def test_listing_failure_does_not_silently_replace_named_voice(self):
        with (
            patch.object(server, "PLATFORM", "mac"),
            patch.object(server.subprocess, "run", side_effect=OSError("no say")),
            self.assertRaises(ValueError),
        ):
            server.pick_voice("Daniel")

    def test_windows_selects_english_instead_of_the_os_default(self):
        with (
            patch.object(server, "PLATFORM", "win"),
            patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout="Microsoft Zira Desktop\n")) as run,
        ):
            self.assertEqual(server.pick_voice(), "Microsoft Zira Desktop")
        self.assertIn("Culture.TwoLetterISOLanguageName -eq 'en'", run.call_args.args[0][-1])
        self.assertTrue(run.call_args.kwargs["check"])

    def test_windows_honors_named_voice_without_interpolating_powershell(self):
        name = "Voice ' with $punctuation"
        with (
            patch.object(server, "PLATFORM", "win"),
            patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=name)) as run,
        ):
            self.assertEqual(server.pick_voice(name), name)
            server._speak(name, "Done.")
        self.assertEqual(run.call_args.kwargs["env"]["NOTIFY_VOICE"], name)
        self.assertNotIn(name, run.call_args.args[0][-1])
        self.assertIn("SelectVoice($env:NOTIFY_VOICE)", run.call_args.args[0][-1])

    def test_windows_without_english_voice_reports_error(self):
        with (
            patch.object(server, "PLATFORM", "win"),
            patch.object(server.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "powershell")),
        ):
            self.assertIn("Could not select voice", server.notify([{"text": "Done."}]))

    def test_linux_speech_dispatcher_uses_english_and_an_optional_named_voice(self):
        with (
            patch.object(server, "PLATFORM", "linux"),
            patch.object(server.shutil, "which", side_effect=lambda cmd: cmd if cmd == "spd-say" else None),
            patch.object(server.subprocess, "run") as run,
        ):
            server._speak(server.pick_voice(), "Done.")
            self.assertEqual(run.call_args.args[0], ["spd-say", "-w", "-l", "en", "Done."])
            server._speak(server.pick_voice("English voice"), "Done.")
            self.assertEqual(run.call_args.args[0], ["spd-say", "-w", "-y", "English voice", "Done."])

    def test_linux_espeak_uses_english_or_the_explicit_voice(self):
        with (
            patch.object(server, "PLATFORM", "linux"),
            patch.object(server.shutil, "which", side_effect=lambda cmd: cmd if cmd == "espeak-ng" else None),
            patch.object(server.subprocess, "run") as run,
        ):
            server._speak(server.pick_voice(), "Done.")
            self.assertEqual(run.call_args.args[0], ["espeak-ng", "-v", "en", "Done."])
            server._speak(server.pick_voice("pt-br"), "Pronto.")
            self.assertEqual(run.call_args.args[0], ["espeak-ng", "-v", "pt-br", "Pronto."])


if __name__ == "__main__":
    unittest.main()
