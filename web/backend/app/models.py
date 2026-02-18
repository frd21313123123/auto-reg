from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

DEFAULT_ACCOUNT_FOLDER_NAME = "Основная"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    accounts: Mapped[list["ManagedAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    account_folders: Mapped[list["AccountFolder"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AccountFolder(Base):
    __tablename__ = "account_folders"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_user_folder_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="account_folders")


class ManagedAccount(Base):
    __tablename__ = "managed_accounts"
    __table_args__ = (UniqueConstraint("user_id", "email", name="uq_user_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    password_openai: Mapped[str] = mapped_column(String(255), nullable=False)
    password_mail: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="not_registered", nullable=False)
    folder: Mapped[str] = mapped_column(
        String(120),
        default=DEFAULT_ACCOUNT_FOLDER_NAME,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="accounts")
