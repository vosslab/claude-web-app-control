# Usage

## Launching sessions

From inside any git repository, use the launcher script to create a tmux session:

```bash
bash launch_session.sh claude          # Claude Code session
bash launch_session.sh codex           # Codex session
bash launch_session.sh claude --name custom-name
bash launch_session.sh claude --attach # also open tmux directly
```

Each invocation creates a fresh session named `{tool}-{reponame}-{YYYYMMDD-HHMM}`.

## Starting the server

```bash
source source_me.sh && python3 server.py
```

### CLI flags

| Flag | Default | Description |
| --- | --- | --- |
| `-H`, `--host` | `0.0.0.0` | Bind address (LAN access by default) |
| `-p`, `--port` | `8741` | Bind port |
| `-r`, `--rotate-token` | off | Generate a new token and exit |

The server prints the access token on startup. Enter this token once on each device.

## Using the web UI

1. Open `http://<host>:<port>` in a browser
2. Enter the access token when prompted
3. Pick a session from the list
4. Use the text input for typed replies
5. Use the navigation pad for arrow keys, Tab, Shift-Tab, Enter, Escape, Ctrl-C
6. Use the top bar controls for Model, Effort, Mode, and Skills

## Session discovery

The server discovers tmux sessions by naming convention:
- Sessions starting with `claude-` are identified as Claude Code
- Sessions starting with `codex-` are identified as Codex

## Plans viewer

The plans viewer reads from `~/.claude/plans/*.md` and lists them by modification time (most recent first). Tap a plan to view its content.

## Token management

- Token is stored at `~/.claude-web-token`
- Token is generated automatically on first run
- Rotate with `python3 server.py --rotate-token`
- Token file permissions are set to 600 (owner-only)

## Security notes

- Default bind is `127.0.0.1` (localhost only)
- Set `--host 0.0.0.0` explicitly for LAN access
- Designed for use behind UniFi Teleport or equivalent private access
- Cookie is HttpOnly with SameSite=Lax
- No Secure flag (plain HTTP on LAN)
- Session names are validated against `claude-*` / `codex-*` convention
- Plan file paths are hardened against traversal
