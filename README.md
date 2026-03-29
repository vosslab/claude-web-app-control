# claude-web-app-control

Phone-friendly web UI for interacting with Claude Code and Codex sessions running in tmux on a Mac Studio. The app is a remote view and input surface that sends keystrokes to tmux and displays output. It never executes shell commands itself; tool-use policy is enforced by Claude Code's `PreToolUse` permission hook.

## Quick start

From inside any git repository on the Mac Studio:

```bash
./launch_session.sh claude
```

This creates a tmux session, starts the web server if needed, and prints the URL and token. Open the URL on your phone and enter the token.

## Documentation

- [docs/USAGE.md](docs/USAGE.md): CLI flags, session management, and web UI controls
- [docs/CHANGELOG.md](docs/CHANGELOG.md): chronological record of changes
- [docs/AUTHORS.md](docs/AUTHORS.md): maintainer and attribution
- [docs/REPO_STYLE.md](docs/REPO_STYLE.md): repository conventions
- [docs/PYTHON_STYLE.md](docs/PYTHON_STYLE.md): Python coding standards
- [docs/MARKDOWN_STYLE.md](docs/MARKDOWN_STYLE.md): Markdown formatting rules
- [docs/CLAUDE_HOOK_USAGE_GUIDE.md](docs/CLAUDE_HOOK_USAGE_GUIDE.md): permission hook reference

## Testing

```bash
source source_me.sh && python3 -m pytest tests/ -q
```
