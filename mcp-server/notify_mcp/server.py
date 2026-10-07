"""MCP notify server — speak short beats with pauses, optionally preceded by a sound.

Cross-platform:
  - macOS  (tested):    `say` for speech, `afplay` for system sounds.
  - Windows (UNTESTED): PowerShell System.Speech for speech, winsound for sounds.
  - Linux  (UNTESTED):  spd-say/espeak for speech, canberra-gtk-play/paplay for sounds.

The two tools (`notify`, `play_sound`) expose the same signatures on every platform;
the platform layer below picks the right backend. Every backend call is guarded so a
missing voice/sound/player never crashes the server — it returns a descriptive string
instead. Run it with `notify-mcp` (console entry point) or `python -m notify_mcp.server`.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from bisect import bisect_right
from contextlib import closing
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("notify")

if sys.platform == "darwin":
    PLATFORM = "mac"
elif sys.platform == "win32" or os.name == "nt":
    PLATFORM = "win"
elif sys.platform.startswith("linux"):
    PLATFORM = "linux"
else:
    PLATFORM = "other"

# --- Sound catalog ------------------------------------------------------------------
# The public sound names are platform-agnostic. Each maps to a macOS system sound and,
# for portability, to a semantic CATEGORY used to pick a Windows/Linux equivalent.
MAC_SOUNDS = {
    name.lower(): f"/System/Library/Sounds/{name}.aiff"
    for name in [
        "Hero", "Glass", "Sosumi", "Basso", "Funk",
        "Ping", "Tink", "Submarine", "Pop", "Purr",
        "Morse", "Frog", "Bottle", "Blow",
    ]
}

# sound name -> semantic category (drives the Windows/Linux fallbacks)
SOUND_CATEGORY = {
    "hero": "success", "glass": "neutral", "sosumi": "blocked", "basso": "error",
    "funk": "warning", "ping": "fyi", "tink": "fyi", "submarine": "attention",
    "pop": "neutral", "purr": "fyi", "morse": "attention", "frog": "neutral",
    "bottle": "neutral", "blow": "neutral",
}

VALID_SOUNDS = sorted(SOUND_CATEGORY)

# Windows: candidate %WINDIR%\Media wav files per category (best-effort, names vary by
# Windows version), and a winsound.MessageBeep flag fallback if none exist.
WIN_MEDIA = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Media"
WIN_WAV_CANDIDATES = {
    "success":   ["tada.wav", "Windows Notify System Generic.wav"],
    "neutral":   ["Windows Ding.wav", "ding.wav", "chimes.wav"],
    "fyi":       ["Windows Notify System Generic.wav", "Windows Notify.wav", "chimes.wav"],
    "attention": ["Windows Notify.wav", "Windows Notify Calendar.wav", "notify.wav"],
    "warning":   ["Windows Exclamation.wav", "Windows Background.wav"],
    "blocked":   ["Windows Exclamation.wav", "Windows Foreground.wav"],
    "error":     ["Windows Critical Stop.wav", "Windows Error.wav", "chord.wav"],
}
# winsound.MessageBeep flags (avoid importing winsound off-Windows)
_MB = {"MB_OK": 0x0, "MB_ICONHAND": 0x10, "MB_ICONEXCLAMATION": 0x30, "MB_ICONASTERISK": 0x40}
WIN_BEEP_FLAG = {
    "success": _MB["MB_ICONASTERISK"], "neutral": _MB["MB_OK"], "fyi": _MB["MB_OK"],
    "attention": _MB["MB_ICONASTERISK"], "warning": _MB["MB_ICONEXCLAMATION"],
    "blocked": _MB["MB_ICONEXCLAMATION"], "error": _MB["MB_ICONHAND"],
}

# Linux: freedesktop sound theme event names (canberra) and oga file basenames.
LINUX_CANBERRA_EVENT = {
    "success": "complete", "neutral": "bell", "fyi": "message",
    "attention": "message-new-instant", "warning": "dialog-warning",
    "blocked": "dialog-warning", "error": "dialog-error",
}
LINUX_OGA_DIRS = [
    "/usr/share/sounds/freedesktop/stereo",
    "/usr/share/sounds/gnome/default/alerts",
]

_voice_cache: str | None = None
_voice_lock = threading.Lock()


# --- Voice selection ----------------------------------------------------------------
def installed_mac_voices(listing: str) -> dict[str, str]:
    """Map installed voice names to their language/region identifiers."""
    return dict(re.findall(
        r"^(.+?)\s+([a-z]{2,3}_[A-Z]{2})\s+#", listing, re.MULTILINE
    ))


def eligible_mac_voices(listing: str) -> list[str]:
    """Prefer English Enhanced/Premium voices, then standard English voices."""
    voices = sorted(
        (name for name, locale in installed_mac_voices(listing).items()
         if locale.startswith("en_")),
        key=str.casefold,
    )
    upgraded = [v for v in voices if v.endswith(("(Enhanced)", "(Premium)"))]
    return upgraded or voices


def next_mac_voice(voices: list[str]) -> str:
    """Advance the shared round robin atomically across server processes."""
    state_path = Path(os.environ.get(
        "NOTIFY_VOICE_STATE_FILE",
        str(Path.home() / "Library/Application Support/notify/voice-rotation.sqlite3"),
    )).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(state_path, timeout=10)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE IF NOT EXISTS rotation (id INTEGER PRIMARY KEY, voice TEXT NOT NULL)")
        previous = db.execute("SELECT voice FROM rotation WHERE id = 1").fetchone()
        # Remember a name rather than an index so adding/removing voices is safe.
        index = bisect_right([v.casefold() for v in voices], previous[0].casefold()) if previous else 0
        voice = voices[index % len(voices)]
        db.execute("INSERT OR REPLACE INTO rotation (id, voice) VALUES (1, ?)", (voice,))
    return voice


def pick_voice(voice: str | None = None) -> str:
    """Honor a named voice; otherwise cache the English session default."""
    preferred = (voice or "").strip() or os.environ.get("NOTIFY_VOICE", "").strip()
    if preferred:
        return _select_voice(preferred)
    global _voice_cache
    with _voice_lock:
        if _voice_cache is None:
            _voice_cache = _select_voice()
        return _voice_cache


def _select_voice(preferred: str | None = None) -> str:
    if PLATFORM == "mac":
        try:
            out = subprocess.run(
                ["say", "-v", "?"], capture_output=True, text=True, check=True
            ).stdout
        except (OSError, subprocess.SubprocessError) as exc:
            if preferred:
                raise ValueError(f"could not verify installed voice '{preferred}'") from exc
            print(f"notify: could not list voices: {exc}", file=sys.stderr)
            return "Samantha"
        if preferred:
            if preferred not in installed_mac_voices(out):
                raise ValueError(f"voice '{preferred}' is not installed; list voices with say -v '?'")
            return preferred
        voices = eligible_mac_voices(out)
        if not voices:
            return "Samantha"
        try:
            return next_mac_voice(voices)
        except (OSError, sqlite3.Error) as exc:
            # Keep notifications working and stay within the eligible pool.
            print(f"notify: voice rotation unavailable: {exc}", file=sys.stderr)
            return voices[0]

    if PLATFORM == "win":
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$voices = $s.GetInstalledVoices() | Where-Object { $_.Enabled } | "
            "ForEach-Object { $_.VoiceInfo }; "
            "if ($env:NOTIFY_VOICE) { "
            "$v = $voices | Where-Object { $_.Name -eq $env:NOTIFY_VOICE } "
            "} else { "
            "$v = $voices | Where-Object { $_.Culture.TwoLetterISOLanguageName -eq 'en' } "
            "}; $v = $v | Select-Object -First 1; "
            "if (-not $v) { Write-Error 'No matching installed voice'; exit 1 }; $v.Name"
        )
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                env={**os.environ, "NOTIFY_VOICE": preferred or ""},
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError("no matching installed SAPI voice; install an English voice or set NOTIFY_VOICE") from exc
        if not out:
            raise ValueError("no matching installed SAPI voice")
        return out

    return preferred or "en"


# --- Sound playback -----------------------------------------------------------------
def _play(sound: str) -> bool:
    """Play a system sound by name. Returns True if something was played."""
    name = sound.lower()
    if name not in SOUND_CATEGORY:
        return False
    category = SOUND_CATEGORY[name]

    if PLATFORM == "mac":
        path = MAC_SOUNDS.get(name)
        if path and Path(path).exists():
            subprocess.run(["afplay", path], check=False)
            return True
        return False

    if PLATFORM == "win":
        try:
            import winsound  # Windows-only stdlib module
        except Exception:
            return False
        for fname in WIN_WAV_CANDIDATES.get(category, []):
            wav = WIN_MEDIA / fname
            if wav.exists():
                try:
                    winsound.PlaySound(str(wav), winsound.SND_FILENAME)
                    return True
                except Exception:
                    break
        try:
            winsound.MessageBeep(WIN_BEEP_FLAG.get(category, _MB["MB_OK"]))
            return True
        except Exception:
            return False

    if PLATFORM == "linux":
        # Prefer the freedesktop sound theme via canberra; else play an .oga directly.
        if shutil.which("canberra-gtk-play"):
            event = LINUX_CANBERRA_EVENT.get(category, "bell")
            r = subprocess.run(
                ["canberra-gtk-play", "-i", event], check=False,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if r.returncode == 0:
                return True
        event = LINUX_CANBERRA_EVENT.get(category, "bell")
        player = shutil.which("paplay") or shutil.which("ffplay") or shutil.which("aplay")
        if player:
            for d in LINUX_OGA_DIRS:
                oga = Path(d) / f"{event}.oga"
                if oga.exists():
                    args = [player, str(oga)]
                    if player.endswith("ffplay"):
                        args = [player, "-autoexit", "-nodisp", "-loglevel", "quiet", str(oga)]
                    subprocess.run(args, check=False,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
        return False

    return False


# --- Speech -------------------------------------------------------------------------
def _speak(voice: str, text: str) -> None:
    """Speak text using the platform TTS backend. Best-effort, never raises."""
    if PLATFORM == "mac":
        subprocess.run(["say", "-v", voice, text], check=False)
        return

    if PLATFORM == "win":
        # Pass the text through an env var so PowerShell never has to quote/escape it.
        env = {**os.environ, "NOTIFY_TEXT": text, "NOTIFY_VOICE": voice}
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "$s.SelectVoice($env:NOTIFY_VOICE); "
            "$s.Speak($env:NOTIFY_TEXT)"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                env=env, check=False,
            )
        except Exception:
            pass
        return

    if PLATFORM == "linux":
        spd_voice = ["-l", "en"] if voice == "en" else ["-y", voice]
        for cmd in (
            ["spd-say", "-w", *spd_voice, text],
            ["espeak-ng", "-v", voice, text],
            ["espeak", "-v", voice, text],
        ):
            if shutil.which(cmd[0]):
                subprocess.run(cmd, check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
        return
    # PLATFORM == "other": no TTS backend; silently skip (caller still returns a summary).


@mcp.tool()
def notify(
    beats: list[dict],
    sound: str | None = None,
    voice: str | None = None,
) -> str:
    """Speak a sequence of short status beats with pauses between them.

    Use this to get the user's attention when they may be away from the screen:
    finishing a long task, hitting a blocker, asking a question, or whenever
    they asked to be pinged/notified.

    English voices are the default on every platform. On macOS, each server
    session rotates through installed English Enhanced/Premium voices, or
    standard English voices if none are installed. Pass voice or set NOTIFY_VOICE
    to select a specific installed voice. 100% local, free, offline.

    Speech-friendly rules — the model MUST follow these when composing beats:
    - Plain English sentences by default, unless the user requests another
      language. No tables, bullets, markdown, code, file
      paths, URLs, long numbers, version strings, or punctuation-heavy text.
    - Each beat should be short and natural — read it out loud mentally first.
      Typical beat: one sentence, ~5–20 words. Length follows content.
    - Split into multiple beats when content has distinct parts (e.g. headline
      + detail, or phase one + phase two). 1–3 beats is normal; more than 3
      means rewrite shorter.

    Args:
        beats: List of beat dicts. Each must have "text" (str) and may have
            "pause_after" (float seconds, default 0.3) — pause inserted AFTER
            this beat finishes speaking, before the next begins.
            Example: [
                {"text": "Build done.", "pause_after": 0.4},
                {"text": "All tests passed."}
            ]
        sound: Optional name of a system sound to play BEFORE the first beat.
            Choose based on situation:
              - "hero": triumphant — task completed successfully
              - "glass": neutral chime — generic "I'm done"
              - "sosumi": sharp — "I'm blocked, need input"
              - "basso" / "funk": warning/error — something failed
              - "ping" / "tink": gentle — low-urgency FYI
              - "submarine": distinctive, hard to miss
            Other valid names: pop, purr, morse, frog, bottle, blow.
        voice: Optional installed voice name, such as "Samantha" or "Daniel"
            on macOS. Overrides NOTIFY_VOICE and the English session default.
            Use a non-English voice only when explicitly requested by the user.

    Returns:
        Confirmation string with voice used and beat count.
    """
    try:
        selected_voice = pick_voice(voice)
    except ValueError as exc:
        return f"Could not select voice: {exc}"
    if sound:
        _play(sound)
    spoken = 0
    for beat in beats:
        text = (beat.get("text") or "").strip()
        if not text:
            continue
        _speak(selected_voice, text)
        spoken += 1
        pause = beat.get("pause_after", 0.3)
        if pause and pause > 0:
            time.sleep(min(float(pause), 5.0))

    return f"Played {spoken} beat(s) with voice '{selected_voice}' on {PLATFORM}"


@mcp.tool()
def play_sound(sound: str = "glass") -> str:
    """Play a system sound without speaking. Use for fast attention pings.

    Args:
        sound: Sound name — hero, glass, sosumi, basso, funk, ping, tink,
            submarine, pop, purr, morse, frog, bottle, blow.

    Returns:
        Confirmation string.
    """
    if sound.lower() not in SOUND_CATEGORY:
        return f"Unknown sound '{sound}'. Valid: {', '.join(VALID_SOUNDS)}"
    if _play(sound):
        return f"Played sound '{sound}' on {PLATFORM}"
    return f"Could not play sound '{sound}' on {PLATFORM} (no audio backend available)"


def main() -> None:
    """Console entry point (`notify-mcp`)."""
    mcp.run()


if __name__ == "__main__":
    main()
