---
name: notify
allowed-tools: mcp__notify__notify, mcp__notify__play_sound, Bash(afplay:*), Bash(say:*), Bash(powershell:*)
description: "Emit a sound and/or speak a short, informative status update to get the user's attention when they may be away from the screen. 100% local and free — no length cap, but messages must be speech-friendly (no tables, bullets, code, or markdown). PREFERRED: call the `mcp__notify__notify` MCP tool with a list of beats; it abstracts macOS vs Windows automatically. Use when finishing a long task, hitting a blocker, asking a question, or when told to notify/ping/alert/get my attention. Triggers on: notify me, ping me, alert me, let me know when, tell me when you're done, get my attention, play a sound, voice update."
---

# Notify

Get the user's attention with a sound — and optionally a short, informative spoken status update — when they may be away from the screen.

100% local, free, offline. Backed by OS built-ins (macOS `afplay`/`say`; Windows PowerShell speech + `winsound`).

## Preferred path: MCP tools

A local MCP server named `notify` exposes two tools:

- **`mcp__notify__notify`** — speak a sequence of short beats with pauses; optionally play a sound first.
  - Input: `beats` (list of `{text: str, pause_after?: float}`), `voice` (optional installed voice name, such as `"Samantha"`), `sound` (optional, e.g. `"hero"`, `"glass"`, `"sosumi"`, `"basso"`).
  - Behavior: plays sound (if any), then speaks each beat with the configured pause between them.
- **`mcp__notify__play_sound`** — play a system sound without speaking. Used for fast attention pings.
  - Input: `sound` (one of `hero`, `glass`, `sosumi`, `basso`, `funk`, `ping`, `tink`, `submarine`, `pop`, `purr`, `morse`, `frog`, `bottle`, `blow`).

**Always prefer these MCP tools** over shelling out — they handle voice selection, escaping, pacing, and the macOS/Windows platform difference automatically. The bash patterns below remain as a macOS-only fallback.

---

## Platforms

- **macOS** — tested. Speech via `say` with an explicit installed voice, defaulting to English. Without an override, the server rotates English Enhanced/Premium voices or standard English voices. Sounds from `/System/Library/Sounds`.
- **Windows** — supported but **untested**. The MCP server speaks via PowerShell `System.Speech` (installed English SAPI voice by default) and plays sounds via the stdlib `winsound` module, mapping each sound name to the closest `%WINDIR%\Media` file or a system beep. The named sounds (`hero`, `glass`, …) all resolve to a sensible Windows equivalent.
- Either way, **just call `mcp__notify__notify`** — the server resolves the backend. Sound names stay the same across platforms; voice names depend on the installed speech backend.

---

## Voice selection

Default to English speech and an English voice unless the user explicitly requests another language or voice.

- Honor the user's configured voice preference. On macOS, pass `voice: "Samantha"` for routine English notifications when no preference is known. `Daniel` is another English option. Use the exact installed name from `say -v '?'` when selecting another voice, including any `(Enhanced)` or `(Premium)` suffix.
- On Windows and Linux, omit `voice` to use the server's English default. Named voices are platform-specific, so do not pass macOS voice names to another platform.
- The optional `voice` argument overrides the server's `NOTIFY_VOICE` environment setting. Without either, macOS rotates English voices once per server session, preferring Enhanced/Premium voices. Windows selects an installed English SAPI voice; Linux requests English from its speech backend.
- If the MCP tools are unavailable and you use the OS speech command, select the voice explicitly. On macOS use `say -v Samantha`; on Linux use `espeak-ng -v en` or `spd-say -l en`. Do not rely on the user's system language or default voice.
- If a named voice is unavailable, choose another installed English voice and retry once. Use a sound-only notification if speech remains unavailable.

Example macOS tool input:

```json
{"beats": [{"text": "The tests passed. The branch is ready for review."}], "sound": "hero", "voice": "Samantha"}
```

## When to use this

Trigger this skill when:

- The user explicitly asks to be notified, pinged, alerted, or told when something is done
- You're finishing a long-running task they kicked off and walked away from
- You're blocked and need an answer from them
- They told you to "let me know when" something happens

Do NOT trigger for every response — only when there's a meaningful reason to interrupt the user away from their screen.

---

## Message guidelines

There is **no hard length cap** — speech is free and local, so you don't pay per character. But the message still has to sound like *spoken English*, not narrated documentation. Aim for **short and informative** — the user is listening, not reading.

Rough target: **one or two sentences per message** (~10–30 words). Longer is fine if the content genuinely needs it. Shorter is fine too — sometimes "Done. Build passed." is the whole point.

### Speech-friendly = these things only

✅ Plain English by default, full sentences, natural sentence flow. Use another language only when the user requests it.
✅ Concrete facts the user actually needs to know.
✅ Conversational phrasing — write like you're telling them in person.

### NOT speech-friendly — strip these before speaking

❌ **Tables** — TTS reads them column-by-column and it's nonsense.
❌ **Bullet/numbered lists** — turn them into prose. "First X, then Y, finally Z."
❌ **Markdown** — no asterisks, backticks, headings, links, code blocks.
❌ **Code, file paths, URLs** — TTS will read `src/foo.ts` as "S R C slash foo dot T S". Either omit, or rephrase ("the auth file", "the README").
❌ **Long numbers, hashes, hex values** — read literally and unintelligible. Round or omit.
❌ **Punctuation-heavy strings** — `!@#$%`, version strings like `v2.3.4-beta.1`, etc.
❌ **Acronyms TTS mangles** — spell out or rephrase: `API` → "A P I" (acceptable), but `SQL` becomes "Sequel" which may surprise. Test if unsure.

### Multiple messages — when to split

If there's genuinely too much to say in one breath, **break it into 2–3 separate beats** (or `say` calls in sequence). Reasons to split:

- Distinct phases ("done with phase one" … pause … "moving to phase two")
- A headline + a detail ("Tests passed." … "Coverage went up two percent.")
- A blocker + a question ("Blocked on the migration." … "Should I roll back, or push through?")

A small pause between beats reads naturally. Don't split more than 3 — at that point write less, not more.

### Good vs bad

| ✅ Good                                                       | ❌ Bad — why                                                                       |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `"Done. Build passed. Coverage is up two percent."`          | `"Done. Build passed. Coverage: 87.4% (+2.1%)."` — reads numbers/% literally       |
| `"Blocked. Need you to choose between Postgres and Mongo."`  | `"Blocked. Options: 1) Postgres, 2) Mongo, 3) SQLite."` — list, not speech         |
| `"Auth tests are failing on the login endpoint."`            | `"Tests failing in src/auth/login.test.ts at line 47"` — file paths sound awful   |
| `"Migration done. Ready for review on the auth branch."`     | `"Migration complete. PR #1234 ready at github.com/..."` — URL, hash              |
| Two beats: `"Refactor done."` + `"Two test files still need updates."` | `"Refactor done. Two test files still need updates and I left TODOs at lines..."` — too much, includes line numbers |

If unsure, **say it out loud yourself first.** If it sounds robotic or you can't get through it in one breath, rewrite.

---

## Picking the right combo for the situation

| Situation                          | Recommended                                                          |
| ---------------------------------- | -------------------------------------------------------------------- |
| Task completed successfully        | `hero` + spoken summary (one or two sentences)                       |
| Generic "I'm done"                 | `glass` (no speech needed)                                           |
| Need user's input / blocked        | `sosumi` + spoken description + the actual question                  |
| Something failed / error           | `basso` + spoken plain-English description (NOT the stack trace)     |
| Quick FYI, low urgency             | `ping` only                                                          |
| Multi-phase milestone              | sound + 2–3 beats with short pauses between                          |

Call it like this (preferred path):

```
mcp__notify__notify(
  beats=[{"text": "All tests passed."}, {"text": "The branch is ready for review."}],
  sound="hero",
  voice="Samantha",  # macOS; omit on other platforms for their English default
)
```

---

## Fallback: shelling out (macOS only)

If the MCP tools are unavailable, you can shell out on macOS. (On Windows, prefer the MCP
tool — there's no portable one-liner.)

```bash
# Sound only
afplay /System/Library/Sounds/Glass.aiff

# Sound + spoken status with an explicit English voice
afplay /System/Library/Sounds/Hero.aiff && \
say -v Samantha "All tests passed. The branch is ready for review."
```

On Windows, use the MCP tool so it selects an installed English SAPI voice. If you need a PowerShell fallback, select an enabled English voice explicitly:

```powershell
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$v = $s.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.TwoLetterISOLanguageName -eq 'en' } | Select-Object -First 1
if (-not $v) { throw 'No installed English voice' }
$s.SelectVoice($v.VoiceInfo.Name)
$s.Speak('All tests passed.')
```

---

## Notes

- Fully offline, free, no API key, no rate limits.
- Sounds play at system volume — if it's too quiet, that's a system-volume issue.
- Always still write the normal text response in chat. The sound/voice is the attention-getter; the chat message is where details (and any tables/code/paths) belong.
