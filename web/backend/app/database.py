import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args: dict[str, object] = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
_init_lock = threading.Lock()
_db_initialized = False


def init_db() -> None:
    global _db_initialized

    if _db_initialized:
        return

    with _init_lock:
        if _db_initialized:
            return

        from app import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        _db_initialized = True
