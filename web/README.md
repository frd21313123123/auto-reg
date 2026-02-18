# Auto-reg Web

Web version of `auto-reg`.

- `backend/` - FastAPI API (auth, accounts, inbox, ban-check, generators)
- `frontend/` - React (Vite) UI

## Local Run

### 1) Backend
```bash
cd web/backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 2) Frontend
```bash
cd web/frontend
npm install
npm run dev
```

Frontend default API in local mode: `http://127.0.0.1:8000/api`.

## GitHub Pages

This repository includes workflow `.github/workflows/deploy-pages.yml`.

It deploys only the frontend to GitHub Pages.

Important:
- GitHub Pages cannot run Python backend.
- For full functionality, deploy backend separately and set repository variable `PAGES_API_URL`.

Recommended `PAGES_API_URL` example:
- `https://your-backend.example.com/api`

If `PAGES_API_URL` is not set, the Pages site will open, but API actions (login/register/accounts) will fail.
