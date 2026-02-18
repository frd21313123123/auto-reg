# Backend (FastAPI)

## Install
```bash
pip install -r requirements.txt
```

## Run
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Environment
Supported env vars use `AUTO_REG_` prefix.

See `.env.example` for:
- `AUTO_REG_SECRET_KEY`
- `AUTO_REG_DATABASE_URL`
- `AUTO_REG_CORS_ORIGINS`
