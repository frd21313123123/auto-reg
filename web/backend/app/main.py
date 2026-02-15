from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import init_db
from app.routers import accounts, auth, mail, tools

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}/auth", tags=["auth"])
app.include_router(accounts.router, prefix=f"{settings.api_v1_prefix}/accounts", tags=["accounts"])
app.include_router(mail.router, prefix=f"{settings.api_v1_prefix}/mail", tags=["mail"])
app.include_router(tools.router, prefix=f"{settings.api_v1_prefix}/tools", tags=["tools"])
