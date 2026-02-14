# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Windows Tkinter GUI app for creating mail.tm temporary email accounts and monitoring their inboxes via REST API or IMAP. Used for managing bulk registrations with status tracking, credential management, and OpenAI ban detection.

## Commands

```bash
pip install -r requirements.txt   # Install dependencies
python main.py                    # Run the app (auto-installs missing deps on startup)
python build_exe.py               # Build Windows exe via PyInstaller → dist/Auto-reg.exe
```

No test suite exists. Validate manually: launch app, create account, check inbox refresh, open a message.

## Architecture

**Entry point**: `main.py` — checks/installs missing pip packages, then launches `MailApp` in a Tkinter root window.

**Core UI** (`app/mail_app.py`, ~1600 lines): Single `MailApp` class owns the entire GUI. Split into:
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

## Coding Style

- Python PEP 8, 4-space indent, UTF-8.
- `snake_case` functions/modules, `PascalCase` classes, `UPPER_SNAKE_CASE` constants.
- UI language is Russian for user-facing strings.
