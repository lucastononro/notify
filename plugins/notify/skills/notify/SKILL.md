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
  - Input: `beats` (list of `{text: str, pause_after?: float}`), `sound` (optional, e.g. `"hero"`, `"glass"`, `"sosumi"`, `"basso"`).
  - Behavior: plays sound (if any), then speaks each beat with the configured pause between them.
- **`mcp__notify__play_sound`** — play a system sound without speaking. Used for fast attention pings.
  - Input: `sound` (one of `hero`, `glass`, `sosumi`, `basso`, `funk`, `ping`, `tink`, `submarine`, `pop`, `purr`, `morse`, `frog`, `bottle`, `blow`).

**Always prefer these MCP tools** over shelling out — they handle voice selection, escaping, pacing, and the macOS/Windows platform difference automatically. The bash patterns below remain as a macOS-only fallback.

---

## Platforms

- **macOS** — tested. Speech via `say` (auto-picks the best installed neural voice: Ava Premium, falling back through Premium/Enhanced/legacy). Sounds from `/System/Library/Sounds`.
- **Windows** — supported but **untested**. The MCP server speaks via PowerShell `System.Speech` (default SAPI voice) and plays sounds via the stdlib `winsound` module, mapping each sound name to the closest `%WINDIR%\Media` file or a system beep. The named sounds (`hero`, `glass`, …) all resolve to a sensible Windows equivalent.
- Either way, **just call `mcp__notify__notify`** — the server resolves the backend. Sound and voice names stay the same across platforms.

---

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

✅ Plain English, full sentences, natural sentence flow.
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
)
```

---

## Fallback: shelling out (macOS only)

If the MCP tools are unavailable, you can shell out on macOS. (On Windows, prefer the MCP
tool — there's no portable one-liner.)

```bash
# Sound only
afplay /System/Library/Sounds/Glass.aiff

# Sound + spoken status with the best installed voice
afplay /System/Library/Sounds/Hero.aiff && \
VOICE=$(for v in "Ava (Premium)" "Zoe (Premium)" "Evan (Premium)" "Allison (Premium)" "Tom (Premium)" "Samantha (Enhanced)" "Daniel (Enhanced)" "Samantha"; do
  esc=$(echo "$v" | sed 's/[][()]/\\&/g')
  if say -v '?' 2>/dev/null | grep -qE "^${esc} +[a-z]{2}_[A-Z]{2}"; then echo "$v"; break; fi
done) && \
say -v "$VOICE" "All tests passed. The branch is ready for review."
```

Windows fallback (one line, default voice):

```powershell
powershell -NoProfile -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('All tests passed.')"
```

---

## Notes

- Fully offline, free, no API key, no rate limits.
- Sounds play at system volume — if it's too quiet, that's a system-volume issue.
- Always still write the normal text response in chat. The sound/voice is the attention-getter; the chat message is where details (and any tables/code/paths) belong.
