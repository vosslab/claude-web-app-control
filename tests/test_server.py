#!/usr/bin/env python3
"""
Tests for the FastAPI server module.

Tests auth, session listing, and plan file path hardening.
"""

import sys
import pytest

# add repo root to path
import git_file_utils
REPO_ROOT = git_file_utils.get_repo_root()
sys.path.insert(0, REPO_ROOT)

import server
import fastapi.testclient

#============================================
def make_client():
	"""Create a fresh test client (no cookies carried over)."""
	return fastapi.testclient.TestClient(server.app, cookies={})


#============================================
def authed_client():
	"""Create a test client with a valid session cookie."""
	c = make_client()
	resp = c.post("/auth", json={"token": server.AUTH_TOKEN})
	assert resp.status_code == 200
	# transfer the session cookie
	cookie_val = resp.cookies.get(server.COOKIE_NAME)
	c.cookies.set(server.COOKIE_NAME, cookie_val)
	return c


#============================================
def test_index_public():
	"""GET / should be public (no auth required)."""
	c = make_client()
	resp = c.get("/")
	assert resp.status_code == 200


#============================================
def test_auth_rejects_bad_token():
	"""POST /auth with wrong token returns 401."""
	c = make_client()
	resp = c.post("/auth", json={"token": "wrong-token-value"})
	assert resp.status_code == 401


#============================================
def test_auth_accepts_valid_token():
	"""POST /auth with correct token returns 200 and sets cookie."""
	c = make_client()
	resp = c.post("/auth", json={"token": server.AUTH_TOKEN})
	assert resp.status_code == 200
	assert server.COOKIE_NAME in resp.cookies


#============================================
def test_sessions_requires_auth():
	"""GET /api/sessions without auth returns 401."""
	c = make_client()
	resp = c.get("/api/sessions")
	assert resp.status_code == 401


#============================================
def test_sessions_with_auth():
	"""GET /api/sessions with valid cookie returns a list."""
	c = authed_client()
	resp = c.get("/api/sessions")
	assert resp.status_code == 200
	assert isinstance(resp.json(), list)


#============================================
def test_plans_requires_auth():
	"""GET /api/plans without auth returns 401."""
	c = make_client()
	resp = c.get("/api/plans")
	assert resp.status_code == 401


#============================================
def test_plans_with_auth():
	"""GET /api/plans with valid cookie returns a list."""
	c = authed_client()
	resp = c.get("/api/plans")
	assert resp.status_code == 200
	assert isinstance(resp.json(), list)


#============================================
def test_plan_path_traversal_dotdot():
	"""GET /api/plans/../../etc/passwd is rejected."""
	c = authed_client()
	resp = c.get("/api/plans/../../etc/passwd")
	assert resp.status_code != 200


#============================================
def test_plan_path_traversal_bad_filename():
	"""GET /api/plans/foo.txt is rejected (not .md pattern)."""
	c = authed_client()
	resp = c.get("/api/plans/foo.txt")
	assert resp.status_code == 400


#============================================
def test_plan_path_traversal_spaces():
	"""GET /api/plans/foo bar.md is rejected."""
	c = authed_client()
	resp = c.get("/api/plans/foo%20bar.md")
	assert resp.status_code == 400


#============================================
def test_skills_requires_auth():
	"""GET /api/skills/claude without auth returns 401."""
	c = make_client()
	resp = c.get("/api/skills/claude")
	assert resp.status_code == 401


#============================================
def test_skills_bad_tool():
	"""GET /api/skills/invalid returns 400."""
	c = authed_client()
	resp = c.get("/api/skills/invalid")
	assert resp.status_code == 400


#============================================
def test_skills_claude_returns_list():
	"""GET /api/skills/claude returns a list."""
	c = authed_client()
	resp = c.get("/api/skills/claude")
	assert resp.status_code == 200
	assert isinstance(resp.json(), list)


#============================================
def test_session_name_validation():
	"""validate_session_name rejects bad names."""
	# valid names
	server.validate_session_name("claude-myrepo-20260329-1530")
	server.validate_session_name("codex-test.repo-123")
	# invalid names should raise
	with pytest.raises(fastapi.HTTPException):
		server.validate_session_name("bad-session")
	with pytest.raises(fastapi.HTTPException):
		server.validate_session_name("../../../etc")
	with pytest.raises(fastapi.HTTPException):
		server.validate_session_name("")
