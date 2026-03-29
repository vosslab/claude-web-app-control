#!/usr/bin/env python3
"""
Tests for tmux_bridge module.

Uses a disposable tmux session created in a fixture and torn down after tests.
"""

import os
import sys
import time
import subprocess
import pytest

# add repo root to path
import git_file_utils
REPO_ROOT = git_file_utils.get_repo_root()
sys.path.insert(0, REPO_ROOT)

import tmux_bridge

# unique session name for test isolation
TEST_SESSION = "test-claude-bridge-pytest"


#============================================
@pytest.fixture(scope="module")
def tmux_session():
	"""
	Create a disposable tmux session for testing and tear it down after.
	"""
	# create a detached tmux session running bash
	subprocess.run(
		["tmux", "new-session", "-d", "-s", TEST_SESSION, "-x", "120", "-y", "40", "bash"],
		check=True,
	)
	# give it a moment to start
	time.sleep(0.5)
	yield TEST_SESSION
	# teardown: kill the session
	subprocess.run(["tmux", "kill-session", "-t", TEST_SESSION], check=False)


#============================================
def test_list_sessions(tmux_session):
	"""list_sessions returns sessions matching claude-*/codex-* convention."""
	# our test session starts with test- so it should NOT appear
	sessions = tmux_bridge.list_sessions()
	session_names = [s["name"] for s in sessions]
	assert TEST_SESSION not in session_names


#============================================
def test_list_sessions_includes_convention():
	"""
	Create a claude-* session and verify it appears in list_sessions.
	"""
	temp_name = "claude-testbridge-temp"
	subprocess.run(
		["tmux", "new-session", "-d", "-s", temp_name, "bash"],
		check=True,
	)
	time.sleep(0.3)
	sessions = tmux_bridge.list_sessions()
	session_names = [s["name"] for s in sessions]
	assert temp_name in session_names
	# cleanup
	subprocess.run(["tmux", "kill-session", "-t", temp_name], check=False)


#============================================
def test_capture_pane(tmux_session):
	"""capture_pane returns non-empty text from the test session."""
	# send a known string to the pane
	tmux_bridge.send_keys(tmux_session, "echo CAPTURE_TEST_MARKER")
	time.sleep(0.5)
	output = tmux_bridge.capture_pane(tmux_session)
	assert isinstance(output, str)
	assert "CAPTURE_TEST_MARKER" in output


#============================================
def test_capture_pane_returns_text(tmux_session):
	"""capture_pane returns a string, not a list."""
	output = tmux_bridge.capture_pane(tmux_session)
	assert isinstance(output, str)


#============================================
def test_send_keys(tmux_session):
	"""send_keys returns True on success."""
	result = tmux_bridge.send_keys(tmux_session, "echo hello_from_send_keys")
	assert result is True
	time.sleep(0.3)
	output = tmux_bridge.capture_pane(tmux_session)
	assert "hello_from_send_keys" in output


#============================================
def test_send_key_allowed(tmux_session):
	"""send_key accepts keys in the allowlist."""
	result = tmux_bridge.send_key(tmux_session, "Enter")
	assert result is True


#============================================
def test_send_key_rejected():
	"""send_key rejects keys not in the allowlist."""
	result = tmux_bridge.send_key("nonexistent-session", "Delete")
	assert result is False


#============================================
def test_send_key_all_allowed(tmux_session):
	"""All ALLOWED_KEYS can be sent without error."""
	for key_name in tmux_bridge.ALLOWED_KEYS:
		result = tmux_bridge.send_key(tmux_session, key_name)
		assert result is True, f"send_key failed for {key_name}"


#============================================
def test_send_interrupt(tmux_session):
	"""send_interrupt returns True."""
	result = tmux_bridge.send_interrupt(tmux_session)
	assert result is True


#============================================
def test_get_pane_size(tmux_session):
	"""get_pane_size returns a tuple of positive integers."""
	rows, cols = tmux_bridge.get_pane_size(tmux_session)
	assert rows > 0
	assert cols > 0


#============================================
def test_get_cwd(tmux_session):
	"""get_cwd returns a non-empty path string."""
	cwd = tmux_bridge.get_cwd(tmux_session)
	assert isinstance(cwd, str)
	assert len(cwd) > 0


#============================================
def test_is_session_alive(tmux_session):
	"""is_session_alive returns True for existing sessions."""
	assert tmux_bridge.is_session_alive(tmux_session) is True


#============================================
def test_is_session_alive_dead():
	"""is_session_alive returns False for non-existent sessions."""
	assert tmux_bridge.is_session_alive("nonexistent-session-xyz") is False


#============================================
def test_get_session_info(tmux_session):
	"""get_session_info returns a complete info dict."""
	# create a claude-* session briefly
	temp_name = "claude-testinfo-temp"
	subprocess.run(
		["tmux", "new-session", "-d", "-s", temp_name, "bash"],
		check=True,
	)
	time.sleep(0.3)
	info = tmux_bridge.get_session_info(temp_name)
	assert info["name"] == temp_name
	assert info["tool"] == "claude"
	assert info["alive"] is True
	assert isinstance(info["repo_name"], str)
	assert isinstance(info["cwd"], str)
	# cleanup
	subprocess.run(["tmux", "kill-session", "-t", temp_name], check=False)


#============================================
def test_capture_pane_nonexistent():
	"""capture_pane returns empty string for non-existent session."""
	output = tmux_bridge.capture_pane("nonexistent-session-xyz")
	assert output == ""


#============================================
def test_get_cwd_nonexistent():
	"""get_cwd returns empty string for non-existent session."""
	cwd = tmux_bridge.get_cwd("nonexistent-session-xyz")
	assert cwd == ""


#============================================
def test_get_pane_size_nonexistent():
	"""get_pane_size returns (0, 0) for non-existent session."""
	rows, cols = tmux_bridge.get_pane_size("nonexistent-session-xyz")
	assert rows == 0
	assert cols == 0
