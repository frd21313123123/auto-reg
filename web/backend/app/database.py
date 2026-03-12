import threading

from sqlalchemy import create_engine, inspect, text
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


def _run_sqlite_migrations() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "managed_accounts" not in table_names:
        return

    managed_account_columns = {
        column["name"] for column in inspect(engine).get_columns("managed_accounts")
    }
    if "folder_id" in managed_account_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE managed_accounts ADD COLUMN folder_id INTEGER"))
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_managed_accounts_folder_id "
                "ON managed_accounts (folder_id)"
            )
        )


def init_db() -> None:
    global _db_initialized

    if _db_initialized:
        return

    with _init_lock:
        if _db_initialized:
            return

        from app import models  # noqa: F401

        Base.metadata.create_all(bind=engine)
        _run_sqlite_migrations()
        _db_initialized = True
