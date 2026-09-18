# notify — Claude Code & Codex plugin

A 100% local, free, offline **attention plugin** for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) and [OpenAI Codex](https://developers.openai.com/codex). When a long task finishes, hits a blocker, or needs a decision while you're away from the screen, the agent plays a sound — and optionally speaks a short, plain-English status update — to pull you back.

One repo ships the same skill + MCP server to both agents:

- 🔔 **`play_sound`** — a fast system-sound ping (`hero`, `glass`, `sosumi`, `basso`, …) for "glance at the screen".
- 🗣️ **`notify`** — plays a sound, then speaks a sequence of short "beats" with natural pauses, using a high-quality local voice.
- 🔒 Fully local: no API key, no network, no rate limits, no telemetry. Speech and sound come from OS built-ins.

The skill enforces *speech-friendly* messages (no tables, code, file paths, or markdown read aloud) — so what the agent says actually sounds like a person talking, while the detailed text stays in the chat.

The MCP server is published as a tiny `uvx`-runnable package, so both agents reference it **path-free** with the exact same command — no bundled-script paths, no per-tool substitution variables.

---

## Install

### Claude Code

```
/plugin marketplace add lucastononro/notify
/plugin install notify@notify-marketplace
```

Update later: `/plugin marketplace update notify-marketplace`

### Codex  *(best-effort, untested — see note)*

```
codex plugin marketplace add lucastononro/notify
codex plugin add notify@notify-marketplace
```

The subcommand is `plugin add`, not `install`. Then `codex plugin list` shows it (`installed, enabled`) and `codex mcp list` shows the `notify` server; `codex plugin remove notify` undoes it.

Verified on the Codex CLI: `marketplace add` → `plugin add` installs the plugin, bundles the skill, and registers the `notify` MCP server with the same path-free `uvx` command used by Claude Code. If you'd rather wire just the server up by hand:

```bash
codex mcp add notify -- \
  uvx --from "git+https://github.com/lucastononro/notify#subdirectory=mcp-server" notify-mcp
```

> Verified end-to-end on a live `codex` install: marketplace add → plugin add installs the plugin, bundles the skill, and registers the `notify` MCP server, and asking Codex to ping plays the sound + speaks. Built per OpenAI's [skills](https://developers.openai.com/codex/skills) / [plugin](https://developers.openai.com/codex/plugins/build) / [MCP](https://developers.openai.com/codex/mcp) docs.

### Prerequisites

- **[`uv`](https://docs.astral.sh/uv/)** on `PATH` — both agents launch the server with `uvx`, which builds + caches the package (and its one dependency, `mcp[cli]`) from git on first run. No manual venv.
  - No `uv`? Install it: `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or `winget install astral-sh.uv` (Windows).
- **macOS** — uses built-in `say` + `afplay`. Nothing to install.
- **Windows** — built-in PowerShell speech + `winsound`. Nothing to install. *(untested — see below)*
- **Linux** — needs a TTS tool (`spd-say` from speech-dispatcher, or `espeak`/`espeak-ng`) and a sound player (`canberra-gtk-play`, or `paplay`/`ffplay` + the freedesktop sound theme). *(untested — see below)*

---

## Use

Ask the agent any of:

- "notify me when the build finishes"
- "ping me when you're done"
- "let me know when the tests pass"
- "play a sound"

…or invoke explicitly: `/notify:notify` (Claude Code) or `$notify` (Codex).

The agent calls the MCP tool automatically — e.g. a chime plus *"All tests passed. The branch is ready for review."*

---

## Platform support

| Platform | Status | Speech | Sound |
| -------- | ------ | ------ | ----- |
| macOS    | ✅ tested | `say` (round robin per server session: Enhanced/Premium voices if available, otherwise standard voices) | `afplay` of `/System/Library/Sounds/*.aiff` |
| Windows  | ⚠️ best-effort, untested | PowerShell `System.Speech` (default SAPI voice) | `winsound` → closest `%WINDIR%\Media` file, falling back to a system beep |
| Linux    | ⚠️ best-effort, untested | `spd-say` → `espeak-ng` → `espeak` | `canberra-gtk-play` (freedesktop theme) → `paplay`/`ffplay`/`aplay` of `*.oga` |

> The named sounds (`hero`, `glass`, …) all resolve to a sensible per-platform equivalent. Every backend call is guarded — a missing voice/sound/player returns a descriptive string instead of crashing the server. The whole platform layer is one file: `mcp-server/notify_mcp/server.py`.

---

## Repo layout

```
.
├── mcp-server/                         # the shared, uvx-runnable MCP server (one source of truth)
│   ├── pyproject.toml                  #   entry point: notify-mcp = notify_mcp.server:main
│   └── notify_mcp/
│       ├── __init__.py
│       └── server.py                   #   cross-platform server (notify + play_sound tools)
│
├── .claude-plugin/
│   └── marketplace.json                # Claude Code marketplace catalog
├── plugins/
│   └── notify/                         # Claude Code plugin
│       ├── .claude-plugin/plugin.json
│       ├── .mcp.json                   #   uvx --from git+…#subdirectory=mcp-server  notify-mcp
│       └── skills/notify/SKILL.md
│
├── .agents/
│   └── plugins/marketplace.json        # Codex marketplace catalog
└── codex-plugin/
    └── notify/                         # Codex plugin
        ├── .codex-plugin/plugin.json
        ├── .mcp.json                   #   same uvx command (Codex's bare server-map shape)
        └── skills/notify/
            ├── SKILL.md
            └── agents/openai.yaml      #   declares the MCP dep + allow_implicit_invocation
```

Both `.mcp.json` files run the **same** path-free command:

```
uvx --from "git+https://github.com/lucastononro/notify#subdirectory=mcp-server" notify-mcp
```

---

## Develop locally

```bash
# Claude Code: load the plugin straight from the repo
claude --plugin-dir ./plugins/notify
claude plugin validate .

# Run / build the MCP server from local source (no git fetch)
uvx --from ./mcp-server notify-mcp
```

---

## Cost & privacy

- **Cost:** none. Speech and sound are produced entirely by OS built-ins — no API, no per-character billing, no rate limits.
- **Privacy:** nothing leaves your machine. There is no notify server, no telemetry, no third party.

---

## License

MIT
