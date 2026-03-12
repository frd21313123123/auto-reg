from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

VALID_ACCOUNT_STATUSES = {
    "not_registered",
    "registered",
    "plus",
    "banned",
    "invalid_password",
}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("folder name is required")
        return normalized


class FolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    account_count: int = 0


class AccountCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password_openai: str = Field(min_length=1, max_length=255)
    password_mail: str | None = Field(default=None, max_length=255)
    status: str = "not_registered"
    folder_id: int | None = Field(default=None, ge=1)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("invalid email")
        return value.strip().lower()

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        status = value.strip()
        if status not in VALID_ACCOUNT_STATUSES:
            raise ValueError("invalid status")
        return status


class AccountUpdateStatus(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        status = value.strip()
        if status not in VALID_ACCOUNT_STATUSES:
            raise ValueError("invalid status")
        return status


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    folder_id: int | None = None
    folder_name: str | None = None
    email: str
    password_openai: str
    password_mail: str
    status: str
    created_at: datetime
    updated_at: datetime


class AccountImportRequest(BaseModel):
    text: str = Field(min_length=1)
    folder_id: int | None = Field(default=None, ge=1)


class AccountImportResponse(BaseModel):
    added: int
    duplicates: int
    skipped: int


class MailTmCreateRequest(BaseModel):
    password_length: int = Field(default=12, ge=8, le=32)
    folder_id: int | None = Field(default=None, ge=1)


class BulkAccountDeleteRequest(BaseModel):
    account_ids: list[int] = Field(min_length=1)


class BulkAccountMoveRequest(BaseModel):
    account_ids: list[int] = Field(min_length=1)
    folder_id: int | None = Field(default=None, ge=1)


class DeleteAllAccountsRequest(BaseModel):
    scope: Literal["all", "folder", "unassigned"] = "all"
    folder_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _validate_scope(self) -> "DeleteAllAccountsRequest":
        if self.scope == "folder" and self.folder_id is None:
            raise ValueError("folder_id is required for folder scope")
        if self.scope != "folder" and self.folder_id is not None:
            raise ValueError("folder_id is only allowed for folder scope")
        return self


class BulkActionResponse(BaseModel):
    affected: int


class ConnectResponse(BaseModel):
    account_type: str
    connected: bool


class MessageSummary(BaseModel):
    id: str
    sender: str
    subject: str
    created_at: str


class MessageDetail(BaseModel):
    id: str
    sender: str
    subject: str
    text: str
    html: str | None = None
    code: str | None = None


class BanCheckResult(BaseModel):
    account_id: int
    email: str
    result: str
    reason: str


class BulkBanCheckRequest(BaseModel):
    account_ids: list[int] | None = None
    max_workers: int = Field(default=8, ge=1, le=60)


class BulkBanCheckResponse(BaseModel):
    checked: int
    banned: int
    invalid_password: int
    errors: int
    results: list[BanCheckResult]


class RandomPersonResponse(BaseModel):
    name: str
    birthdate: str
