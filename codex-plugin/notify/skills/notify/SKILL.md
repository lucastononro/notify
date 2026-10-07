---
name: notify
description: "Emit a sound and/or speak a short spoken status update to get the user's attention when they may be away from the screen. TRIGGER when the user asks to be notified/pinged/alerted/told when something is done, when finishing a long-running task they walked away from, when blocked and needing an answer, or when told to play a sound. DO NOT trigger on every response — only when there is a real reason to interrupt someone away from the screen. PREFERRED: call the `notify` MCP tool (tools `notify` and `play_sound`); messages must be speech-friendly (no tables, bullets, code, file paths, URLs, or markdown). 100% local, free, offline."
---

# Notify

Get the user's attention with a sound — and optionally a short, informative spoken status update — when they may be away from the screen.

100% local, free, offline. Backed by OS built-ins (macOS `say`/`afplay`; Windows PowerShell speech + `winsound`; Linux `spd-say`/`espeak` + `canberra-gtk-play`/`paplay`).

## Tools (from the bundled `notify` MCP server)

- **`notify`** — play a sound (optional), then speak a sequence of short beats with pauses.
  - Input: `beats` (list of `{text: str, pause_after?: float}`), `voice` (optional installed voice name, such as `Samantha` on macOS), `sound` (optional: `hero`, `glass`, `sosumi`, `basso`, `funk`, `ping`, `tink`, `submarine`, `pop`, `purr`, `morse`, `frog`, `bottle`, `blow`).
- **`play_sound`** — play a system sound without speaking. Input: `sound` (one of the names above).

Always prefer these tools over shelling out — they handle voice selection, escaping, pacing, and the macOS/Windows/Linux platform difference automatically.

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

- The user explicitly asks to be notified, pinged, alerted, or told when something is done.
- You're finishing a long-running task they kicked off and walked away from.
- You're blocked and need an answer from them.
- They told you to "let me know when" something happens.

Do NOT trigger for every response — only when there's a meaningful reason to interrupt the user away from their screen.

## Message guidelines

There is no hard length cap — speech is free and local. But the message still has to sound like *spoken English*, not narrated documentation. Aim for one or two sentences (~10–30 words).

Speech-friendly = plain English by default, full sentences, concrete facts, conversational phrasing. Use another language only when the user requests it.

NOT speech-friendly — strip these before speaking:

- Tables and bullet/numbered lists — turn them into prose ("first X, then Y, finally Z").
- Markdown — no asterisks, backticks, headings, links, code blocks.
- Code, file paths, URLs — TTS reads `src/foo.ts` as "S R C slash foo dot T S". Omit or rephrase ("the auth file", "the README").
- Long numbers, hashes, hex, version strings, punctuation-heavy text — round or omit.

Split into 2–3 beats when there are distinct parts (headline + detail, or phase one + phase two). Don't split more than 3 — at that point write less, not more.

## Picking a sound

| Situation | Sound |
| --- | --- |
| Task completed successfully | `hero` + spoken summary |
| Generic "I'm done" | `glass` (no speech needed) |
| Need input / blocked | `sosumi` + spoken description + the question |
| Something failed / error | `basso` + plain-English description (not the stack trace) |
| Quick FYI, low urgency | `ping` only |
| Multi-phase milestone | sound + 2–3 beats |

## Notes

- Fully offline, free, no API key, no rate limits.
- Always still write the normal text response in chat. The sound/voice is the attention-getter; the chat message is where details (and any tables/code/paths) belong.
