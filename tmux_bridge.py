#!/usr/bin/env python3
"""
tmux bridge module for claude-web-app-control.

Provides a Python interface to interact with tmux sessions:
list sessions, capture pane output, send keys, and query pane state.
All calls use subprocess.run with list args (no shell=True).
"""

import subprocess

# Named keys allowed to be sent via send_key()
ALLOWED_KEYS = frozenset({
	"Up", "Down", "Left", "Right",
	"Enter", "Tab", "BTab",
	"Escape", "BSpace", "Space",
	"C-c",
})


#============================================
def _run_tmux(args: list) -> subprocess.CompletedProcess:
	"""
	Run a tmux command and return the CompletedProcess result.

	Args:
		args: list of arguments to pass to tmux

	Returns:
		CompletedProcess with stdout, stderr, returncode
	"""
	cmd = ["tmux"] + args
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
	return result


#============================================
def list_sessions() -> list:
	"""
	List all tmux sessions matching claude-* or codex-* naming convention.

	Returns:
		List of dicts with keys: name, created, attached
	"""
	result = _run_tmux(["list-sessions", "-F", "#{session_name}\t#{session_created}\t#{session_attached}"])
	if result.returncode != 0:
		return []
	sessions = []
	for line in result.stdout.strip().split("\n"):
		if not line:
			continue
		parts = line.split("\t")
		if len(parts) < 3:
			continue
		name = parts[0]
		# only include sessions matching the naming convention
		if not (name.startswith("claude-") or name.startswith("codex-")):
			continue
		sessions.append({
			"name": name,
			"created": parts[1],
			"attached": parts[2] != "0",
		})
	return sessions


#============================================
def capture_pane(session: str, pane: str = "0", full_history: bool = False) -> str:
	"""
	Capture the content of a tmux pane.

	Args:
		session: tmux session name
		pane: pane index (default "0")
		full_history: if True, capture entire scrollback buffer, not just visible

	Returns:
		Pane content as a single string with newlines
	"""
	target = f"{session}:0.{pane}"
	# -e preserves ANSI escape codes
	# -S - starts from beginning of scrollback, -E - goes to end
	if full_history:
		cmd = ["capture-pane", "-t", target, "-p", "-e", "-S", "-"]
	else:
		cmd = ["capture-pane", "-t", target, "-p", "-e"]
	result = _run_tmux(cmd)
	if result.returncode != 0:
		return ""
	return result.stdout


#============================================
def send_keys(session: str, text: str, pane: str = "0") -> bool:
	"""
	Send text followed by Enter to a tmux pane.

	Args:
		session: tmux session name
		text: text to send
		pane: pane index (default "0")

	Returns:
		True if successful, False otherwise
	"""
	target = f"{session}:0.{pane}"
	result = _run_tmux(["send-keys", "-t", target, text, "Enter"])
	return result.returncode == 0


#============================================
def send_key(session: str, key_name: str, pane: str = "0") -> bool:
	"""
	Send a single named terminal key to a tmux pane.

	Args:
		session: tmux session name
		key_name: name of the key (must be in ALLOWED_KEYS)
		pane: pane index (default "0")

	Returns:
		True if successful, False otherwise
	"""
	if key_name not in ALLOWED_KEYS:
		return False
	target = f"{session}:0.{pane}"
	result = _run_tmux(["send-keys", "-t", target, key_name])
	return result.returncode == 0


#============================================
def send_interrupt(session: str, pane: str = "0") -> bool:
	"""
	Send Ctrl-C to a tmux pane.

	Args:
		session: tmux session name
		pane: pane index (default "0")

	Returns:
		True if successful, False otherwise
	"""
	return send_key(session, "C-c", pane)


#============================================
def get_pane_size(session: str, pane: str = "0") -> tuple:
	"""
	Get the dimensions of a tmux pane.

	Args:
		session: tmux session name
		pane: pane index (default "0")

	Returns:
		Tuple of (rows, cols) as integers, or (0, 0) on failure
	"""
	target = f"{session}:0.{pane}"
	result = _run_tmux(["display-message", "-t", target, "-p", "#{pane_height}\t#{pane_width}"])
	if result.returncode != 0:
		return (0, 0)
	parts = result.stdout.strip().split("\t")
	if len(parts) < 2:
		return (0, 0)
	rows = int(parts[0])
	cols = int(parts[1])
	return (rows, cols)


#============================================
def get_cwd(session: str, pane: str = "0") -> str:
	"""
	Get the current working directory of a tmux pane process.
	Best-effort: returns empty string on failure.

	Args:
		session: tmux session name
		pane: pane index (default "0")

	Returns:
		Working directory path as string, or empty string on failure
	"""
	target = f"{session}:0.{pane}"
	result = _run_tmux(["display-message", "-t", target, "-p", "#{pane_current_path}"])
	if result.returncode != 0:
		return ""
	return result.stdout.strip()


#============================================
def is_session_alive(session: str) -> bool:
	"""
	Check if a tmux session exists and its pane 0 can be captured.

	Args:
		session: tmux session name

	Returns:
		True if session is alive and capturable
	"""
	result = _run_tmux(["has-session", "-t", session])
	if result.returncode != 0:
		return False
	# verify pane is capturable
	target = f"{session}:0.0"
	result = _run_tmux(["capture-pane", "-t", target, "-p"])
	return result.returncode == 0


#============================================
def get_session_info(session: str) -> dict:
	"""
	Get combined info about a session for the session picker.

	Args:
		session: tmux session name

	Returns:
		Dict with: name, tool, repo_name, alive, cwd
	"""
	# determine tool type from name prefix
	tool = "unknown"
	if session.startswith("claude-"):
		tool = "claude"
	elif session.startswith("codex-"):
		tool = "codex"
	alive = is_session_alive(session)
	cwd = get_cwd(session) if alive else ""
	# derive repo name from cwd basename
	repo_name = "unknown"
	if cwd:
		repo_name = cwd.rstrip("/").split("/")[-1]
	return {
		"name": session,
		"tool": tool,
		"repo_name": repo_name,
		"alive": alive,
		"cwd": cwd,
	}
