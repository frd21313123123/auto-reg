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


def init_db() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if engine.dialect.name != "sqlite":
        return

    with engine.begin() as conn:
        columns = {
            row[1].lower()
            for row in conn.exec_driver_sql("PRAGMA table_info(managed_accounts)").fetchall()
        }
        if "folder" not in columns:
            conn.exec_driver_sql(
                "ALTER TABLE managed_accounts "
                "ADD COLUMN folder VARCHAR(120) NOT NULL DEFAULT 'Основная'"
            )
