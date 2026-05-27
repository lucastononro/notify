# notify — Claude Code marketplace

A 100% local, free, offline **attention skill** for [Claude Code](https://docs.claude.com/en/docs/claude-code/overview). When a long task finishes, hits a blocker, or needs a decision while you're away from the screen, Claude plays a sound — and optionally speaks a short, plain-English status update — to pull you back.

This repository is a **plugin marketplace**. It ships one plugin: `notify`, which bundles a small MCP server exposing two tools.

What you get:

- 🔔 **`play_sound`** — a fast system-sound ping (`hero`, `glass`, `sosumi`, `basso`, …) for "glance at the screen".
- 🗣️ **`notify`** — plays a sound, then speaks a sequence of short "beats" with natural pauses, using a high-quality local voice.
- 🔒 Fully local: no API key, no network, no rate limits, no telemetry. Speech and sound come from OS built-ins.

The skill enforces *speech-friendly* messages (no tables, code, file paths, or markdown read aloud) — so what Claude says actually sounds like a person talking, while the detailed text stays in the chat.

---

## Install

In Claude Code:

```
/plugin marketplace add lucastononro/notify
/plugin install notify@notify-marketplace
```

To update later:

```
/plugin marketplace update notify-marketplace
```

### Prerequisites

- **[`uv`](https://docs.astral.sh/uv/)** on `PATH` — the bundled MCP server runs via `uv run --script`, which auto-installs its one dependency (`mcp[cli]`) on first launch. No manual venv.
  - No `uv`? Install it (`curl -LsSf https://astral.sh/uv/install.sh | sh`, or `winget install astral-sh.uv` on Windows), or edit `plugins/notify/.mcp.json` to call your own Python with `mcp[cli]` installed.
- **macOS** — uses the built-in `say` and `afplay`. Nothing to install.
- **Windows** — uses the built-in PowerShell speech engine + `winsound`. Nothing to install. **(See platform note below — Windows is untested.)**

---

## Use

Once installed, ask Claude any of:

- "notify me when the build finishes"
- "ping me when you're done"
- "let me know when the tests pass"
- "play a sound"

…or invoke the skill explicitly:

```
/notify:notify
```

Claude calls the MCP tool automatically — e.g. a chime plus *"All tests passed. The branch is ready for review."*

---

## Platform support

| Platform | Status | Speech | Sound |
| -------- | ------ | ------ | ----- |
| macOS    | ✅ tested | `say` (auto-picks best neural voice — Ava Premium → … → Samantha) | `afplay` of `/System/Library/Sounds/*.aiff` |
| Windows  | ⚠️ **best-effort, untested** | PowerShell `System.Speech` (default SAPI voice) | `winsound` → closest `%WINDIR%\Media` file, falling back to a system beep |
| Linux    | ➖ not supported | — | — |

> **Windows is implemented but has not been run on a Windows machine.** The named sounds all map to a sensible Windows equivalent, and speech goes through the built-in SAPI engine via PowerShell. If you hit a snag on Windows, please open an issue — the platform layer lives in one file (`plugins/notify/mcp-servers/notify/server.py`) and is easy to tweak.

---

## Repo layout

```
.
├── .claude-plugin/
│   └── marketplace.json              # the marketplace catalog
└── plugins/
    └── notify/                       # the plugin
        ├── .claude-plugin/
        │   └── plugin.json           # plugin manifest
        ├── .mcp.json                 # registers the bundled MCP server
        ├── mcp-servers/
        │   └── notify/
        │       └── server.py         # cross-platform MCP server (uv PEP-723 script)
        └── skills/
            └── notify/
                └── SKILL.md          # skill definition + instructions
```

The plugin registers its MCP server with `${CLAUDE_PLUGIN_ROOT}`, so the bundled `server.py` is found wherever the plugin is installed.

---

## Develop locally

Test the plugin without publishing:

```bash
claude --plugin-dir ./plugins/notify
```

Or test the marketplace end-to-end from a sibling directory:

```
/plugin marketplace add /absolute/path/to/notify
/plugin install notify@notify-marketplace
```

Validate the marketplace + plugin JSON:

```bash
claude plugin validate .
```

Boot the MCP server by hand (resolves deps via uv, then waits on stdio — Ctrl-C to exit):

```bash
uv run --script ./plugins/notify/mcp-servers/notify/server.py
```

---

## Cost & privacy

- **Cost:** none. Speech and sound are produced entirely by OS built-ins — no API, no per-character billing, no rate limits.
- **Privacy:** nothing leaves your machine. There is no notify server, no telemetry, no third party.

---

## License

MIT
