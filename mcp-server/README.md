# notify-mcp-server

The MCP server behind the [`notify`](https://github.com/lucastononro/notify) Claude Code / Codex plugin.

Exposes two stdio MCP tools — `notify` (play a sound, then speak short "beats") and
`play_sound` (sound only). 100% local, free, offline. Cross-platform:

- **macOS** (tested): `say` + `afplay`.
- **Windows** (best-effort, untested): PowerShell `System.Speech` + `winsound`.
- **Linux** (best-effort, untested): `spd-say`/`espeak` + `canberra-gtk-play`/`paplay`.

## macOS voice rotation

Each Notify server session selects the next eligible voice on its first `notify`
call, then keeps that voice until the server process exits. Calls to `play_sound`
do not consume a turn in the rotation. Restarting Codex can start a new server
session even for an existing task; this is not a permanent voice assignment to a
task ID.

The pool contains all installed voices labelled `(Enhanced)` or `(Premium)` if
any exist. Otherwise it contains all installed standard voices. Voices cycle in
alphabetical order, wrapping after the last one. The installed pool is refreshed
for each new server session.

The last selected voice is stored in
`~/Library/Application Support/notify/voice-rotation.sqlite3`. SQLite transactions
serialize concurrent sessions so they each advance the rotation once. Set
`NOTIFY_VOICE_STATE_FILE` to use a different state file, for example during tests.
If state storage is unavailable, the session uses the first eligible voice and
logs a warning to stderr. If voice enumeration fails, it falls back to Samantha.

This local checkout can be selected in Codex with:

```bash
codex mcp add notify -- uvx --from /absolute/path/to/notify/mcp-server notify-mcp
```

Existing running servers retain their voice and code until restarted. The MCP
dependency is constrained to version 1 because this server uses its FastMCP API.

## Run

Path-free, via `uvx` straight from git:

```bash
uvx --from "git+https://github.com/lucastononro/notify#subdirectory=mcp-server" notify-mcp
```

The same command goes in a Claude Code `.mcp.json` or a Codex `config.toml` /
`.mcp.json` — see the [repo README](https://github.com/lucastononro/notify).

## Voices

`notify(beats, sound=None, voice=None)` defaults to English. On macOS the default rotates through English Enhanced/Premium voices, falling back to standard English voices. A per-call `voice` selects an exact installed name, such as `Samantha` or `Daniel`. Set `NOTIFY_VOICE` in the server environment for a persistent preference. The per-call argument takes precedence and bypasses rotation without changing its state.

Windows selects an enabled English SAPI voice by default and explicitly uses the selected name for speech. Linux passes English language/voice arguments to `spd-say` or `espeak`. Overrides use names supported by the platform's speech backend. Missing named macOS or Windows voices return a selection error; Windows never falls back to a non-English OS default.

## Develop

```bash
uvx --from . notify-mcp        # build + run from this directory
```

MIT.
