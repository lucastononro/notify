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
import subprocess
import sys
import time
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

# --- macOS voice preference (best installed neural voice, falling back) -------------
VOICE_PRIORITY = [
    "Ava (Premium)",
    "Zoe (Premium)",
    "Evan (Premium)",
    "Allison (Premium)",
    "Tom (Premium)",
    "Samantha (Enhanced)",
    "Daniel (Enhanced)",
    "Samantha",
]

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


# --- Voice selection ----------------------------------------------------------------
def pick_voice() -> str:
    """Return the best available voice name for the current platform (cached)."""
    global _voice_cache
    if _voice_cache:
        return _voice_cache

    if PLATFORM == "mac":
        try:
            out = subprocess.run(
                ["say", "-v", "?"], capture_output=True, text=True
            ).stdout
            for v in VOICE_PRIORITY:
                esc = re.escape(v)
                if re.search(rf"^{esc}\s+[a-z]{{2}}_[A-Z]{{2}}", out, re.MULTILINE):
                    _voice_cache = v
                    return v
        except Exception:
            pass
        _voice_cache = "Samantha"
        return _voice_cache

    if PLATFORM == "win":
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                 "Add-Type -AssemblyName System.Speech; "
                 "(New-Object System.Speech.Synthesis.SpeechSynthesizer).Voice.Name"],
                capture_output=True, text=True,
            ).stdout.strip()
            _voice_cache = out or "default (SAPI)"
            return _voice_cache
        except Exception:
            _voice_cache = "default (SAPI)"
            return _voice_cache

    _voice_cache = "default"
    return _voice_cache


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
        env = {**os.environ, "NOTIFY_TEXT": text}
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
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
        for cmd in (["spd-say", "-w", text], ["espeak-ng", text], ["espeak", text]):
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
) -> str:
    """Speak a sequence of short status beats with pauses between them.

    Use this to get the user's attention when they may be away from the screen:
    finishing a long task, hitting a blocker, asking a question, or whenever
    they asked to be pinged/notified.

    Each beat is spoken using a high-quality local voice (macOS picks Ava Premium
    if installed, falling back through Premium/Enhanced/legacy voices; Windows uses
    the default SAPI voice; Linux uses spd-say/espeak). 100% local, free, offline.

    Speech-friendly rules — the model MUST follow these when composing beats:
    - Plain English sentences only. No tables, bullets, markdown, code, file
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

    Returns:
        Confirmation string with voice used and beat count.
    """
    if sound:
        _play(sound)

    voice = pick_voice()
    spoken = 0
    for beat in beats:
        text = (beat.get("text") or "").strip()
        if not text:
            continue
        _speak(voice, text)
        spoken += 1
        pause = beat.get("pause_after", 0.3)
        if pause and pause > 0:
            time.sleep(min(float(pause), 5.0))

    return f"Played {spoken} beat(s) with voice '{voice}' on {PLATFORM}"


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
