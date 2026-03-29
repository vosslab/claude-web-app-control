## 2026-03-29

### Additions and New Features

- Added `tmux_bridge.py`: Python interface for tmux sessions (list, capture, send keys, send named keys, get cwd/size).
- Added `server.py`: FastAPI web server with token-gated auth, multi-session API, WebSocket streaming, plan file serving, and skills discovery.
- Added `launch_session.sh`: bash launcher script that creates fresh `{tool}-{reponame}-{timestamp}` tmux sessions for Claude Code or Codex.
- Added `static/index.html`: single-file mobile-first web UI with token entry, session picker, ANSI-colored output, navigation pad, session controls, and plans viewer.
- Added `tests/test_tmux_bridge.py`: 17 tests for the tmux bridge module.
- Added `tests/test_server.py`: 14 tests for auth, session API, and plan path traversal hardening.
- Added `docs/USAGE.md`: detailed usage documentation for server, launcher, and web UI.
- Updated `pip_requirements.txt` with fastapi, uvicorn.
- Updated `README.md` with project description, quick start, and architecture overview.
- Added `kill_sessions.sh`: kills all claude/codex tmux sessions and the web server.

### Behavior or Interface Changes

- Changed token format from random base64 to human-typable 4-word format (e.g., `globe-vivid-quartz-storm`).
- Changed cookie auth from in-memory set to HMAC-derived from token, so cookies survive server restarts.
- Changed server default bind from `127.0.0.1` to `0.0.0.0` for LAN access by default.
- Changed output rendering from append-event chunks to full-replace model using complete scrollback capture, fixing repeated output display.
- Launcher script now auto-starts the web server in a tmux session (`cwac-server`) if not already running.
- Launcher script prints browsable LAN URL (e.g., `http://192.168.2.75:8741`).

### Fixes and Maintenance

- Added return type hints to all async endpoints and `main()` in `server.py`.
- Removed unused `fastapi.staticfiles` import from `server.py`.
- Reordered imports by length then alphabetical in `server.py`.
- Removed dead `userScrolledUp` variable from `static/index.html`.
- Added 10-second timeout to `subprocess.run()` in `tmux_bridge._run_tmux()`.
- Added custom session name validation in `launch_session.sh` (must start with `claude-` or `codex-`).
- Fixed token comparison to use constant-time `hmac.compare_digest`.
- Added 4096-character length cap on text input forwarded to tmux.
- Removed unused `pyyaml` from `pip_requirements.txt`.
- Fixed `docs/USAGE.md` default host to match `server.py` (`0.0.0.0`).

### Decisions and Failures

- Chose to discover sessions by tmux naming convention (claude-*/codex-*) instead of config file, reducing maintenance overhead.
- Chose to always create fresh tmux sessions instead of reusing existing ones, avoiding stale session ambiguity.
- Plans are read from `~/.claude/plans/` (global) not per-repo, matching how Claude Code stores plans.
- No audit log in MVP: single-user setup behind private network makes it unnecessary complexity.
- No git status display: the app is for planning and editing, not git control.
- All user input routed through tmux only: server never executes shell commands.

## 2026-03-13

### Additions and New Features

- Added `docs/CLAUDE_HOOK_USAGE_GUIDE.md` to `STYLE_FILES` in `propagate_style_guides.py` so it is copied to target repos.
- Added `@docs/CLAUDE_HOOK_USAGE_GUIDE.md` reference to template `CLAUDE.md`.

### Behavior or Interface Changes

- Changed `propagate_style_guides.py` to merge `CLAUDE.md` instead of overwriting, preserving repo-specific `@` reference lines in target repos.

## 2026-02-25

### Fixes and Maintenance

- Fixed `devel/commit_changelog.py` to detect staged (`git add`) changelog changes by falling back to `git diff --cached` when the unstaged diff is empty.

## 2026-02-22

- Updated `docs/REPO_STYLE.md` to require consistent section headings for each changelog day block (`Added`, `Changed`, `Fixed`, `Failures`, `Decisions`) and to keep empty sections with `- None.`.
- Updated `docs/REPO_STYLE.md` section names for changelog day blocks to `Additions`, `Updates`, `Removals`, `Failures`, and `Validations`.
- Updated `docs/REPO_STYLE.md` changelog day template to also require `Fixes` and `Decisions` sections.
- Updated `docs/REPO_STYLE.md` changelog policy language: empty categories are optional, every entry must be categorized, entries are never removed (only rephrased), and day category names are now the six longer labels.

## 2026-02-20

- Added `tests/test_init_files.py` to enforce surface-level `__init__.py` style rules from `docs/PYTHON_STYLE.md`, including checks for non-docstring implementation, imports, exports/maps, global assignments, and `__version__` assignments.
- Scoped `tests/test_init_files.py` to analyze only substantial `__init__.py` files and write violations to `report_init.txt` with stale report cleanup at test startup.
- Updated `propagate_style_guides.py` and `.gitignore` to include `test_init_files.py`.
- Simplified gitignore management to require `report_*.txt` and clean up legacy per-report entries in `propagate_style_guides.py`.
- Updated `tests/test_init_files.py` so the no-`__init__.py` case reports pass instead of skip.
- Updated `propagate_style_guides.py` to skip propagating `source_me.sh` into repositories that are already present on `PATH` (for example `junk-drawer`).
- Optimized `tests/test_pyflakes_code_lint.py` to run `pyflakes` once per pytest session and reuse indexed results for per-file tests, preserving one-dot-per-file output while reducing runtime overhead.
- Updated `docs/REPO_STYLE.md` to clarify that changelog entries should capture notable failures and key implementation choices, not only successful changes.

## 2026-02-19

- Added `tests/test_import_dot.py` to fail on relative from-import statements such as `from . import x` and `from .module import x`.
- Updated `propagate_style_guides.py` so `test_import_dot.py` is included in propagated test scripts.
- Updated `tests/test_import_star.py` and `tests/test_import_dot.py` to write per-test report files (`report_import_star.txt` and `report_import_dot.txt`), remove stale reports at test start, and include report paths in assertion failures.
- Renamed `tests/test_import_requirements.py` output to `report_import_requirements.txt` (from `report_imports.txt`) while preserving existing report generation and stale-file cleanup behavior.
- Added import report files to `.gitignore` and `propagate_style_guides.py` required ignore entries: `report_import_star.txt`, `report_import_dot.txt`, and `report_import_requirements.txt`.
- Restored per-file parametrized execution in `tests/test_import_star.py` and `tests/test_import_dot.py` so pytest shows one dot/failure per scanned file while still writing per-test report files.

## 2026-02-16

- Fixed false positives in `tests/test_shebangs.py` where Rust inner attributes (`#![...]`) were misidentified as shebangs, causing `.rs` files to be flagged under `shebang_not_executable`.

## 2026-02-14

- Trimmed `propagate_style_guides.py` to stop editing existing `AGENTS.md` files in target repositories while keeping a no-overwrite bootstrap copy when `AGENTS.md` is missing.
- Added a no-overwrite style file category in `propagate_style_guides.py` so `AGENTS.md` and `docs/AUTHORS.md` are copied only when absent and never updated in-place.
- Updated `propagate_style_guides.py` style destination routing so `CLAUDE.md` is propagated with overwrite to repo root while standard style guides continue to copy into `docs/`.
- Refactored `propagate_style_guides.py` file lists to explicit `(source_name, target_path)` mappings for overwrite and no-overwrite categories, removing special-case destination branching.
- Simplified `propagate_style_guides.py` file lists again to target-relative paths only, deriving source filenames from basename while preserving overwrite/no-overwrite behavior.
- Updated `propagate_style_guides.py` default source lookup/help text to use `<base>/starter_repo_template` instead of `<base>/junk-drawer`.
- Clarified in `README.md` that only `README.md` and `docs/CHANGELOG.md` are repo-specific, while other files are intended to remain generic template infrastructure.
- Standardized `README.md` with a concise infrastructure-focused overview, curated `docs/` links, and a verifiable quick-start test command.
- Updated `AGENTS.md` to direct AI agents to run commands with `bash -lc` (not Zsh) so `source_me.sh` works with expected shell semantics.
