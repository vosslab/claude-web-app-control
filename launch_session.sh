#!/bin/bash
# launch_session.sh - Create a fresh tmux session for Claude Code or Codex
#                     and start the web server if not already running.
#
# Usage:
#   launch_session.sh claude          # creates claude-{reponame}-{timestamp}
#   launch_session.sh codex           # creates codex-{reponame}-{timestamp}
#   launch_session.sh claude --name custom-name
#   launch_session.sh claude --attach
#
# Always creates a new session. Never reuses existing sessions.
# Starts the web server automatically if it is not already running.

set -e

# resolve script directory (where server.py lives)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# defaults
TOOL=""
CUSTOM_NAME=""
ATTACH=0

# parse arguments
while [ $# -gt 0 ]; do
	case "$1" in
		claude|codex)
			TOOL="$1"
			shift
			;;
		--name)
			CUSTOM_NAME="$2"
			shift 2
			;;
		--attach)
			ATTACH=1
			shift
			;;
		--no-attach)
			ATTACH=0
			shift
			;;
		*)
			echo "Unknown argument: $1" >&2
			echo "Usage: launch_session.sh <claude|codex> [--name NAME] [--attach]" >&2
			exit 1
			;;
	esac
done

# validate tool argument
if [ -z "$TOOL" ]; then
	echo "Error: specify 'claude' or 'codex' as the first argument" >&2
	echo "Usage: launch_session.sh <claude|codex> [--name NAME] [--attach]" >&2
	exit 1
fi

# detect repo root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
	echo "Error: not inside a git repository" >&2
	exit 1
fi

# derive repo name from directory basename
REPO_NAME=$(basename "$REPO_ROOT")

# generate session name
TIMESTAMP=$(date +%Y%m%d-%H%M)
if [ -n "$CUSTOM_NAME" ]; then
	# validate custom name starts with claude- or codex- (server filters by convention)
	case "$CUSTOM_NAME" in
		claude-*|codex-*)
			SESSION_NAME="$CUSTOM_NAME"
			;;
		*)
			echo "Error: custom name must start with 'claude-' or 'codex-'" >&2
			echo "The web server only discovers sessions matching that convention." >&2
			exit 1
			;;
	esac
else
	SESSION_NAME="${TOOL}-${REPO_NAME}-${TIMESTAMP}"
fi

# determine the command to launch
if [ "$TOOL" = "claude" ]; then
	LAUNCH_CMD="claude"
elif [ "$TOOL" = "codex" ]; then
	LAUNCH_CMD="codex"
fi

# create the tmux session in the repo root
tmux new-session -d -s "$SESSION_NAME" -c "$REPO_ROOT" "$LAUNCH_CMD"

# detect LAN IP for the web UI URL
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
PORT=8741

# start the web server in a tmux session if not already running
SERVER_SESSION="cwac-server"
if ! lsof -iTCP:"$PORT" -sTCP:LISTEN -P -n > /dev/null 2>&1; then
	echo "Starting web server..."
	tmux new-session -d -s "$SERVER_SESSION" -c "$SCRIPT_DIR" \
		"source $SCRIPT_DIR/source_me.sh && python3 $SCRIPT_DIR/server.py"
	sleep 1
	if lsof -iTCP:"$PORT" -sTCP:LISTEN -P -n > /dev/null 2>&1; then
		echo "Server running in tmux session: $SERVER_SESSION"
	else
		echo "Warning: server may have failed to start" >&2
		echo "Check with: tmux attach -t $SERVER_SESSION" >&2
	fi
else
	echo "Web server already running on port $PORT"
fi

# print session info
echo "Session: $SESSION_NAME"
echo "Repo: $REPO_ROOT"
echo "Tool: $TOOL"
echo "Time: $TIMESTAMP"
echo "Web UI: http://${LAN_IP}:${PORT}"

# optionally attach
if [ "$ATTACH" -eq 1 ]; then
	tmux attach-session -t "$SESSION_NAME"
fi
