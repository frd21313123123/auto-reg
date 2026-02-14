# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: app entry point; starts the Tkinter GUI.
- `app/`: core Python modules (`mail_app.py`, `imap_client.py`, themes, widgets, generators, hotkey settings).
- `assets/`: app icons and bundled UI assets.
- `build_exe.py`: PyInstaller build script for Windows GUI executable.
- `cpp/`: experimental C++ implementation (`auto_reg_cpp.cpp`) and `build_cpp.ps1`.
- `dist/`, `build/`: generated artifacts (do not edit manually).
- Local data: `accounts.txt`, `accounts.xlsx`, `hotkeys.json` (runtime/user data).

## Build, Test, and Development Commands
- Install dependencies:
  - `python -m pip install -r requirements.txt`
- Run GUI locally:
  - `python main.py`
- Build Windows GUI executable:
  - `python build_exe.py`
  - Output: `dist/Auto-reg.exe`
- Build C++ binary (optional path):
  - `powershell -NoProfile -ExecutionPolicy Bypass -File .\build_cpp.ps1`

## Coding Style & Naming Conventions
- Python: follow PEP 8, 4-space indentation, UTF-8 files.
- Naming: modules/functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE`.
- Keep Tkinter callbacks small; move network/file logic into helper methods.
- Prefer explicit error handling around network and IMAP operations; surface user-safe messages in UI.
- C++ (if touched): use modern C++ (`-std=c++20`), RAII for resource handles, and clear function-level separation.

## Testing Guidelines
- No formal automated test suite is currently configured.
- Minimum validation before PR:
  - Launch app with `python main.py`.
  - Create/login account flow works.
  - Inbox refresh and message open work.
  - `python build_exe.py` completes successfully.
- If adding complex logic, include focused unit tests in a new `tests/` folder (recommended: `pytest`).

## Commit & Pull Request Guidelines
- Existing history uses short, task-focused messages; keep commits concise and imperative.
  - Example: `fix: reconnect IMAP after token expiry`
- One logical change per commit; avoid mixing refactor + feature + build output.
- PRs should include:
  - What changed and why.
  - Steps to verify (commands run, manual checks).
  - Screenshots/GIFs for UI changes.
  - Linked issue/task when available.

## Security & Configuration Tips
- Never commit real account credentials or personal inbox data.
- Keep `accounts.txt`/`accounts.xlsx` as local-only data.
- Treat API/IMAP errors as untrusted input; validate and sanitize displayed content.
