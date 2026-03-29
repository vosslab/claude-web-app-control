#!/bin/bash
# kill_sessions.sh - Kill all claude-*/codex-* tmux sessions and the web server

PORT=8741

# kill tmux sessions
KILLED=0
for s in $(tmux list-sessions -F '#{session_name}' 2>/dev/null); do
	case "$s" in
		claude-*|codex-*)
			tmux kill-session -t "$s"
			echo "Killed session: $s"
			KILLED=$((KILLED + 1))
			;;
	esac
done

if [ "$KILLED" -eq 0 ]; then
	echo "No claude/codex sessions found"
else
	echo "Killed $KILLED session(s)"
fi

# kill web server tmux session
SERVER_SESSION="cwac-server"
if tmux has-session -t "$SERVER_SESSION" 2>/dev/null; then
	tmux kill-session -t "$SERVER_SESSION"
	echo "Killed web server session: $SERVER_SESSION"
else
	# fallback: kill by port if running outside tmux
	SERVER_PID=$(lsof -iTCP:"$PORT" -sTCP:LISTEN -P -n -t 2>/dev/null)
	if [ -n "$SERVER_PID" ]; then
		kill "$SERVER_PID"
		echo "Killed web server (PID: $SERVER_PID)"
	else
		echo "No web server running"
	fi
fi
