# auto-reg

GUI tool for creating mail.tm accounts and reading inbox via API/IMAP..

## Requirements
- Python 3.10+
- Windows (for best UI + sound support)

Install deps:
```
pip install -r requirements.txt
```

## Run
```
python main.py
```

## Web version (React + FastAPI)
- Docs: `web/README.md`
- Backend: `web/backend` (auth, accounts, inbox, ban-check, generators)
- Frontend: `web/frontend` (browser UI)
- GitHub Pages workflow: `.github/workflows/deploy-pages.yml`

Important:
- GitHub Pages hosts only the frontend.
- Backend must be deployed separately for login/register/inbox to work on Pages.
- Set repository variable `PAGES_API_URL` for Pages build (example: `https://your-backend.example.com/api`).

Quick start:
```bash
cd web/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd web/frontend
npm install
npm run dev
```

## C++ version (console)
- Source: `cpp/auto_reg_cpp.cpp`
- Build on Windows:
```
powershell -NoProfile -ExecutionPolicy Bypass -File .\build_cpp.ps1
```
- Binary output: `build/auto_reg_cpp.exe`
- Run:
```
build\auto_reg_cpp.exe          # GUI mode (default, interface similar to Python app)
build\auto_reg_cpp.exe --cli    # Legacy console mode
```

## Notes
- Local data files `accounts.txt` and `accounts.xlsx` are ignored by git.
- Sound notification plays when new emails arrive.
