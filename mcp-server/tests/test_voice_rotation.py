import io
import multiprocessing
import os
import tempfile
import unittest
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from notify_mcp import server


VOICES = ["Ava (Premium)", "Daniel (Enhanced)", "Evan (Enhanced)", "Zoe (Premium)"]
LISTING = "\n".join(f"{voice}    en_US    # Hello." for voice in VOICES)


def allocate_voice(state_file):
    os.environ["NOTIFY_VOICE_STATE_FILE"] = state_file
    return server.next_mac_voice(VOICES)


class VoiceRotationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name) / "rotation.sqlite3"
        self.env = patch.dict(os.environ, {"NOTIFY_VOICE_STATE_FILE": str(self.state)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.platform = patch.object(server, "PLATFORM", "mac")
        self.platform.start()
        self.addCleanup(self.platform.stop)
        self.cache = patch.object(server, "_voice_cache", None)
        self.cache.start()
        self.addCleanup(self.cache.stop)

    def test_enhanced_and_premium_exclude_standard_voices(self):
        listing = "Samantha    en_US    # Hello.\n" + LISTING + "\n" + LISTING
        self.assertEqual(server.eligible_mac_voices(listing), VOICES)

    def test_no_upgraded_voices_uses_only_english_standard_voices(self):
        listing = "Samantha    en_US    # Hello.\nAmélie    fr_CA    # Bonjour.\n"
        self.assertEqual(server.eligible_mac_voices(listing), ["Samantha"])

    def test_foreign_premium_voice_does_not_displace_english_standard_voice(self):
        listing = "Luciana (Premium)    pt_BR    # Olá.\nSamantha    en_US    # Hello.\n"
        self.assertEqual(server.eligible_mac_voices(listing), ["Samantha"])

    def test_english_variants_are_eligible_but_foreign_upgraded_voices_are_not(self):
        listing = LISTING + "\nAmélie (Premium)    fr_CA    # Bonjour.\nDaniel    en_GB    # Hello.\n"
        self.assertEqual(server.eligible_mac_voices(listing), VOICES)

    def test_no_english_voice_never_falls_back_to_foreign_voice(self):
        listing = "Luciana (Premium)    pt_BR    # Olá.\n"
        self.assertEqual(server.eligible_mac_voices(listing), [])
        with patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=listing)):
            self.assertEqual(server.pick_voice(), "Samantha")
        self.assertFalse(self.state.exists())

    def test_successive_sessions_wrap_and_keep_their_voice(self):
        with patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=LISTING)):
            selected = []
            for _ in range(6):
                server._voice_cache = None  # a newly started server session
                first = server.pick_voice()
                self.assertEqual(server.pick_voice(), first)
                selected.append(first)
        self.assertEqual(selected, VOICES + VOICES[:2])

    def test_standard_pool_rotates_when_upgraded_voices_are_absent(self):
        listing = "Samantha    en_US    # Hello.\nDaniel    en_GB    # Hello.\n"
        with patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=listing)):
            selected = []
            for _ in range(3):
                server._voice_cache = None
                selected.append(server.pick_voice())
        self.assertEqual(selected, ["Daniel", "Samantha", "Daniel"])

    def test_concurrent_first_calls_in_one_session_advance_only_once(self):
        with patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=LISTING)):
            with ThreadPoolExecutor(max_workers=8) as pool:
                chosen = list(pool.map(lambda _: server.pick_voice(), range(16)))
        self.assertEqual(chosen, [VOICES[0]] * 16)
        self.assertEqual(server.next_mac_voice(VOICES), VOICES[1])

    def test_concurrent_processes_share_one_rotation(self):
        with multiprocessing.get_context("spawn").Pool(4) as pool:
            chosen = pool.map(allocate_voice, [str(self.state)] * 12)
        self.assertEqual(Counter(chosen), Counter({voice: 3 for voice in VOICES}))
        self.assertEqual(server.next_mac_voice(VOICES), VOICES[0])

    def test_changed_pool_continues_after_last_name(self):
        self.assertEqual(server.next_mac_voice(VOICES), "Ava (Premium)")
        self.assertEqual(server.next_mac_voice(VOICES), "Daniel (Enhanced)")
        self.assertEqual(server.next_mac_voice([VOICES[0], VOICES[2]]), "Evan (Enhanced)")
        self.assertEqual(server.next_mac_voice(["Samantha"]), "Samantha")

    def test_unavailable_state_still_uses_upgraded_pool(self):
        self.state.mkdir()  # a directory cannot be opened as a SQLite database
        with patch.object(server.subprocess, "run", return_value=SimpleNamespace(stdout=LISTING)):
            with redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(server.pick_voice(), "Ava (Premium)")
        self.assertIn("voice rotation unavailable", errors.getvalue())

    def test_sound_only_does_not_allocate_a_voice(self):
        with patch.object(server, "_play", return_value=True):
            server.play_sound("glass")
        self.assertFalse(self.state.exists())
        self.assertIsNone(server._voice_cache)


if __name__ == "__main__":
    unittest.main()
