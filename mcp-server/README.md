# notify-mcp-server

The MCP server behind the [`notify`](https://github.com/lucastononro/notify) Claude Code / Codex plugin.

Exposes two stdio MCP tools — `notify` (play a sound, then speak short "beats") and
`play_sound` (sound only). 100% local, free, offline. Cross-platform:

- **macOS** (tested): `say` + `afplay`.
- **Windows** (best-effort, untested): PowerShell `System.Speech` + `winsound`.
- **Linux** (best-effort, untested): `spd-say`/`espeak` + `canberra-gtk-play`/`paplay`.

## Run

Path-free, via `uvx` straight from git:

```bash
uvx --from "git+https://github.com/lucastononro/notify#subdirectory=mcp-server" notify-mcp
```

The same command goes in a Claude Code `.mcp.json` or a Codex `config.toml` /
`.mcp.json` — see the [repo README](https://github.com/lucastononro/notify).

## Develop

```bash
uvx --from . notify-mcp        # build + run from this directory
```

MIT.
