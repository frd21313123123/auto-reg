# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

> **SYNC RULE**: `CLAUDE.md` and `AGENTS.md` must always have identical content. When editing either file, immediately copy the same changes to the other file so they stay in sync.

## What This Is

A Windows Tkinter GUI app for creating mail.tm temporary email accounts and monitoring their inboxes via REST API or IMAP. Used for managing bulk registrations with status tracking, credential management, and OpenAI ban detection.

## Project Structure & Module Organization

- `main.py`: app entry point; checks/installs missing pip packages, then starts the Tkinter GUI.
- `app/`: core Python modules (`mail_app.py`, `imap_client.py`, themes, widgets, generators, hotkey settings).
- `assets/`: app icons and bundled UI assets.
- `build_exe.py`: PyInstaller build script for Windows GUI executable.
- `cpp/`: experimental C++ implementation (`auto_reg_cpp.cpp`) and `build_cpp.ps1`.
- `dist/`, `build/`: generated artifacts (do not edit manually).
- Local data: `accounts.txt`, `accounts.xlsx`, `hotkeys.json` (runtime/user data, git-ignored).

## Commands

```bash
pip install -r requirements.txt   # Install dependencies
python main.py                    # Run the app (auto-installs missing deps on startup)
python build_exe.py               # Build Windows exe via PyInstaller → dist/Auto-reg.exe
```

Build C++ binary (optional):
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_cpp.ps1
```

## Testing

No formal automated test suite exists. Minimum validation before PR:
- Launch app with `python main.py`.
- Create/login account flow works.
- Inbox refresh and message open work.
- `python build_exe.py` completes successfully.

If adding complex logic, include focused unit tests in a new `tests/` folder (recommended: `pytest`).

## Architecture

**Core UI** (`app/mail_app.py`): Single `MailApp` class owns the entire GUI. Split into:
- Left panel: account list, action buttons, random data generator
- Right panel: email header, inbox Treeview, message viewer
- All network operations run in background threads, UI updates via `root.after()`

**Dual mail backend**: Accounts connect via mail.tm REST API first; if that fails, falls back to IMAP (`app/imap_client.py`). The `account_type` field ("api"/"imap") tracks which is active.

**Theme system**: `app/themes.py` defines `THEMES["light"]` and `THEMES["dark"]` color dictionaries. `set_theme()` in MailApp applies colors to every widget. Custom widgets in `app/widgets.py` (`HoverButton`, `AnimatedToggle`, `SectionLabel`) each have `update_colors()` methods for theme switching.

**Account format**: `accounts.txt` stores `email / password_openai;password_mail / status`. Status values: `not_registered`, `registered`, `plus`, `banned`, `invalid_password`. Excel export mirrors this with color-coded rows.

**Ban checker**: Multi-threaded (`ThreadPoolExecutor`) — each thread gets its own `requests.Session`. For non-mail.tm domains, uses IMAP with cached host discovery.

**Sub-windows**: `sk_generator.py`, `in_generator.py`, `minesweeper.py`, `hotkey_settings.py` — each opened via `Toplevel`, receives theme name as parameter.

## Key Constraints

- **Tkinter limitations**: No alpha colors (e.g. `#00000015` will crash), no CSS, no rounded corners on native widgets. Use Canvas-based drawing for custom shapes.
- **Windows-only features**: `winsound`, `os.startfile()`, `ctypes.windll` — guard with platform checks if cross-platform needed.
- **Threading model**: Never touch Tkinter widgets from background threads. Always use `self.root.after(0, callback)` to schedule UI updates on the main thread.
- **VPN resilience**: HTTP sessions auto-reset on connection errors. Credentials are cached (`current_email`/`current_password`) for automatic re-authentication after network changes.
- **Python/C++ parity**: If behavior or business logic is changed in Python, review and update the C++ implementation in `cpp/` within the same task whenever applicable. Do not leave C++ behavior outdated unless explicitly requested.
- Keep Tkinter callbacks small; move network/file logic into helper methods.
- Prefer explicit error handling around network and IMAP operations; surface user-safe messages in UI.

## Coding Style

- Python PEP 8, 4-space indent, UTF-8.
- `snake_case` functions/modules, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.
- UI language is Russian for user-facing strings.
- C++ (if touched): use modern C++ (`-std=c++20`), RAII for resource handles.

## Commit & Pull Request Guidelines

- Short, task-focused messages; keep commits concise and imperative (e.g. `fix: reconnect IMAP after token expiry`).
- One logical change per commit; avoid mixing refactor + feature + build output.
- PRs should include what changed, steps to verify, screenshots for UI changes.
