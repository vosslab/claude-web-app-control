#!/usr/bin/env python3
"""
FastAPI web server for claude-web-app-control.

Provides token-gated access to tmux sessions running Claude Code or Codex.
Sessions are discovered by naming convention (claude-* / codex-*).
All user input is forwarded to tmux; the server never executes shell commands.
"""

import re
import time
import hmac
import random
import asyncio
import hashlib
import argparse
import pathlib
import subprocess

import fastapi
import fastapi.responses
import starlette.websockets
import uvicorn

import tmux_bridge

# path conventions
TOKEN_PATH = pathlib.Path.home() / ".claude-web-token"
PLANS_DIR = pathlib.Path.home() / ".claude" / "plans"
CLAUDE_SKILLS_DIR = pathlib.Path.home() / ".claude" / "skills"
CODEX_SKILLS_DIR = pathlib.Path.home() / ".codex" / "skills"

# plan filename validation pattern
PLAN_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_-]+\.md$")

# session name validation pattern
SESSION_NAME_RE = re.compile(r"^(claude|codex)-[a-zA-Z0-9_.-]+$")

# cookie name for session auth
COOKIE_NAME = "cwac_session"

# per-session last-activity tracking (session_name -> epoch timestamp)
last_activity = {}

# rate limiting: max messages per second per WebSocket client
RATE_LIMIT_MAX = 10
RATE_LIMIT_WINDOW = 1.0

app = fastapi.FastAPI()


#============================================
# word list for human-typable tokens (4 words = easy to type on phone)
TOKEN_WORDS = [
	"alpha", "brave", "cedar", "delta", "ember", "frost", "grain", "hover",
	"ivory", "jewel", "knack", "lemon", "maple", "noble", "olive", "prism",
	"quartz", "river", "solar", "tiger", "ultra", "vivid", "waltz", "xenon",
	"yacht", "zebra", "blaze", "cliff", "drift", "eagle", "flame", "globe",
	"hatch", "inlet", "joker", "kayak", "lunar", "merit", "north", "orbit",
	"pixel", "quest", "ridge", "storm", "torch", "unity", "vault", "wired",
]


#============================================
def generate_human_token() -> str:
	"""Generate a human-typable token from 4 random words."""
	words = random.sample(TOKEN_WORDS, 4)
	return "-".join(words)


#============================================
def load_or_create_token() -> str:
	"""
	Load the auth token from disk, or generate and save a new one.

	Returns:
		The token string
	"""
	if TOKEN_PATH.exists():
		token = TOKEN_PATH.read_text().strip()
		if token:
			return token
	# generate a human-typable token
	token = generate_human_token()
	TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
	TOKEN_PATH.write_text(token + "\n")
	# restrict permissions to owner only
	TOKEN_PATH.chmod(0o600)
	return token


# load token at startup
AUTH_TOKEN = load_or_create_token()


#============================================
def make_cookie_value(token: str) -> str:
	"""
	Create a cookie value derived from the token via HMAC.
	This survives server restarts as long as the token is the same.
	"""
	sig = hmac.new(token.encode(), b"cwac-session", hashlib.sha256).hexdigest()[:32]
	return sig


def verify_cookie(cookie_value: str) -> bool:
	"""Check if a cookie value is valid for the current token."""
	expected = make_cookie_value(AUTH_TOKEN)
	return hmac.compare_digest(cookie_value, expected)


#============================================
def require_auth(request: fastapi.Request) -> None:
	"""
	Validate that the request has a valid session cookie.
	Raises HTTPException 401 if not authenticated.
	"""
	cookie = request.cookies.get(COOKIE_NAME)
	if not cookie or not verify_cookie(cookie):
		raise fastapi.HTTPException(status_code=401, detail="Not authenticated")


#============================================
def validate_session_name(session_id: str) -> None:
	"""
	Validate that a session name matches the expected convention.
	Raises HTTPException 400 if invalid.
	"""
	if not SESSION_NAME_RE.match(session_id):
		raise fastapi.HTTPException(status_code=400, detail="Invalid session name")


#============================================
# Static files - serve index.html
static_dir = pathlib.Path(__file__).parent / "static"


@app.get("/")
async def serve_index() -> fastapi.responses.Response:
	"""Serve the main page (public, no auth required)."""
	index_path = static_dir / "index.html"
	if not index_path.exists():
		return fastapi.responses.PlainTextResponse("index.html not found", status_code=404)
	return fastapi.responses.FileResponse(index_path, media_type="text/html")


#============================================
@app.post("/auth")
async def authenticate(request: fastapi.Request) -> fastapi.responses.JSONResponse:
	"""
	Validate the bootstrap token and set an HttpOnly session cookie.

	Expects JSON body: {"token": "..."}
	"""
	body = await request.json()
	submitted_token = body.get("token", "")
	if not hmac.compare_digest(submitted_token, AUTH_TOKEN):
		raise fastapi.HTTPException(status_code=401, detail="Invalid token")
	# create a deterministic session cookie derived from the token
	cookie_value = make_cookie_value(AUTH_TOKEN)
	response = fastapi.responses.JSONResponse({"status": "ok"})
	response.set_cookie(
		key=COOKIE_NAME,
		value=cookie_value,
		httponly=True,
		samesite="lax",
		# no secure flag: plain HTTP on LAN
	)
	return response


#============================================
@app.get("/api/sessions")
async def list_sessions(request: fastapi.Request) -> list:
	"""
	List all claude-*/codex-* tmux sessions with status info.
	"""
	require_auth(request)
	sessions = tmux_bridge.list_sessions()
	result = []
	for s in sessions:
		name = s["name"]
		info = tmux_bridge.get_session_info(name)
		# include last activity time
		activity = last_activity.get(name, 0)
		info["last_activity"] = activity
		result.append(info)
	# sort by last activity descending (most recent first)
	result.sort(key=lambda x: x["last_activity"], reverse=True)
	return result


#============================================
@app.get("/api/skills/{tool}")
async def list_skills(tool: str, request: fastapi.Request) -> list:
	"""
	List available skills for claude or codex.
	Discovered from ~/.claude/skills/ or ~/.codex/skills/.
	"""
	require_auth(request)
	if tool == "claude":
		skills_dir = CLAUDE_SKILLS_DIR
	elif tool == "codex":
		skills_dir = CODEX_SKILLS_DIR
	else:
		raise fastapi.HTTPException(status_code=400, detail="Tool must be claude or codex")
	if not skills_dir.exists():
		return []
	skills = []
	for entry in sorted(skills_dir.iterdir()):
		if entry.is_dir():
			# skill name is the directory name
			skill_name = entry.name
			# try to read description from SKILL.md
			skill_md = entry / "SKILL.md"
			description = ""
			if skill_md.exists():
				# read first non-empty, non-frontmatter line as description
				in_frontmatter = False
				for line in skill_md.read_text().split("\n"):
					stripped = line.strip()
					if stripped == "---":
						in_frontmatter = not in_frontmatter
						continue
					if in_frontmatter:
						# extract description from frontmatter
						if stripped.startswith("description:"):
							description = stripped[len("description:"):].strip()
						continue
					if stripped and not stripped.startswith("#"):
						if not description:
							description = stripped
						break
			skills.append({"name": skill_name, "description": description})
	return skills


#============================================
@app.get("/api/plans")
async def list_plans(request: fastapi.Request) -> list:
	"""
	List plan files from ~/.claude/plans/, sorted by mtime descending.
	"""
	require_auth(request)
	if not PLANS_DIR.exists():
		return []
	plans = []
	for f in PLANS_DIR.iterdir():
		if f.is_file() and f.suffix == ".md":
			plans.append({
				"filename": f.name,
				"mtime": f.stat().st_mtime,
			})
	# sort by modification time, most recent first
	plans.sort(key=lambda x: x["mtime"], reverse=True)
	return plans


#============================================
@app.get("/api/plans/{filename}")
async def read_plan(filename: str, request: fastapi.Request) -> dict:
	"""
	Read a specific plan file. Path hardened against traversal.
	"""
	require_auth(request)
	# validate filename pattern
	if not PLAN_FILENAME_RE.match(filename):
		raise fastapi.HTTPException(status_code=400, detail="Invalid filename")
	# resolve the full path and verify it is inside PLANS_DIR
	target = (PLANS_DIR / filename).resolve()
	plans_resolved = PLANS_DIR.resolve()
	if not str(target).startswith(str(plans_resolved)):
		raise fastapi.HTTPException(status_code=400, detail="Path traversal rejected")
	if not target.exists():
		raise fastapi.HTTPException(status_code=404, detail="Plan not found")
	content = target.read_text()
	return {"filename": filename, "content": content}


#============================================
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: starlette.websockets.WebSocket, session_id: str) -> None:
	"""
	WebSocket endpoint for streaming tmux pane output and receiving input.

	Authenticates via session cookie. Validates session name.
	Polls capture-pane at ~2Hz and sends diffs to the client.
	Receives JSON messages: {"type": "text", "data": "..."} or {"type": "key", "data": "Up"}
	"""
	# authenticate via cookie
	cookie = websocket.cookies.get(COOKIE_NAME)
	if not cookie or not verify_cookie(cookie):
		await websocket.close(code=1008, reason="Not authenticated")
		return
	# validate session name
	if not SESSION_NAME_RE.match(session_id):
		await websocket.close(code=1008, reason="Invalid session name")
		return
	await websocket.accept()
	# track last known pane content for diffing
	last_content = ""
	# start streaming
	async def stream_output():
		"""Poll capture-pane and send diffs to the client."""
		nonlocal last_content
		while True:
			content = tmux_bridge.capture_pane(session_id, full_history=True)
			if content != last_content:
				# send the new content
				# compute what is new: simple approach - send full content on change
				# client handles append-event chunking
				await websocket.send_json({
					"type": "pane_update",
					"content": content,
					"timestamp": time.time(),
				})
				last_content = content
				# update last activity
				last_activity[session_id] = time.time()
			await asyncio.sleep(0.5)
	# run output streaming as a background task
	stream_task = asyncio.create_task(stream_output())
	# receive input from the client with rate limiting
	# track message timestamps for rate limiting
	msg_timestamps = []
	try:
		while True:
			data = await websocket.receive_json()
			# rate limit: drop messages exceeding RATE_LIMIT_MAX per second
			now = time.time()
			# remove timestamps older than the window
			msg_timestamps = [t for t in msg_timestamps if now - t < RATE_LIMIT_WINDOW]
			if len(msg_timestamps) >= RATE_LIMIT_MAX:
				# drop this message silently
				await websocket.send_json({"type": "error", "message": "Rate limit exceeded"})
				continue
			msg_timestamps.append(now)
			msg_type = data.get("type", "")
			msg_data = data.get("data", "")
			if msg_type == "text":
				# send text + Enter to tmux (cap length to prevent abuse)
				tmux_bridge.send_keys(session_id, msg_data[:4096])
				last_activity[session_id] = time.time()
			elif msg_type == "key":
				# send a named key to tmux
				tmux_bridge.send_key(session_id, msg_data)
				last_activity[session_id] = time.time()
	except starlette.websockets.WebSocketDisconnect:
		pass
	finally:
		stream_task.cancel()


#============================================
def parse_args() -> argparse.Namespace:
	"""
	Parse command-line arguments.
	"""
	parser = argparse.ArgumentParser(description="Claude Web App Control server")
	parser.add_argument(
		"-H", "--host", dest="host", type=str, default="0.0.0.0",
		help="Bind host (default: 0.0.0.0 for LAN access)",
	)
	parser.add_argument(
		"-p", "--port", dest="port", type=int, default=8741,
		help="Bind port (default: 8741)",
	)
	parser.add_argument(
		"-r", "--rotate-token", dest="rotate_token", action="store_true",
		help="Generate a new token and exit",
	)
	args = parser.parse_args()
	return args


#============================================
def main() -> None:
	"""Start the server."""
	args = parse_args()
	if args.rotate_token:
		# delete existing token and generate a new one
		if TOKEN_PATH.exists():
			TOKEN_PATH.unlink()
		new_token = load_or_create_token()
		print(f"New token generated: {new_token}")
		print(f"Saved to: {TOKEN_PATH}")
		return
	# display token and browsable URL for user
	# resolve a browsable address (0.0.0.0 is not browsable)
	display_host = args.host
	if display_host == "0.0.0.0":
		# detect LAN IP
		result = subprocess.run(["ipconfig", "getifaddr", "en0"], capture_output=True, text=True)
		lan_ip = result.stdout.strip()
		if lan_ip:
			display_host = lan_ip
		else:
			display_host = "127.0.0.1"
	print(f"Token: {AUTH_TOKEN}")
	print(f"Token file: {TOKEN_PATH}")
	print(f"Server: http://{display_host}:{args.port}")
	print()
	# start uvicorn
	uvicorn.run(app, host=args.host, port=args.port)


#============================================
if __name__ == "__main__":
	main()
