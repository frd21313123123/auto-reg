from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_ACCOUNT_FOLDER_NAME = "Основная"

CANONICAL_ACCOUNT_STATUSES = {
    "not_registered",
    "registered",
    "plus",
    "business",
    "banned",
    "invalid_password",
}

ACCOUNT_STATUS_ALIASES = {
    "busnis": "business",
}

VALID_ACCOUNT_STATUSES = CANONICAL_ACCOUNT_STATUSES | set(ACCOUNT_STATUS_ALIASES.keys())


def normalize_account_status(value: str) -> str:
    status = value.strip().lower()
    status = ACCOUNT_STATUS_ALIASES.get(status, status)
    if status not in CANONICAL_ACCOUNT_STATUSES:
        raise ValueError("invalid status")
    return status


def normalize_account_folder(value: str | None) -> str:
    folder = str(value or "").strip()
    if not folder:
        return DEFAULT_ACCOUNT_FOLDER_NAME
    if " / " in folder or "\n" in folder or "\r" in folder:
        raise ValueError("invalid folder")
    return folder


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


class AccountCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password_openai: str = Field(min_length=1, max_length=255)
    password_mail: str | None = Field(default=None, max_length=255)
    status: str = "not_registered"
    folder: str = DEFAULT_ACCOUNT_FOLDER_NAME

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        if "@" not in value:
            raise ValueError("invalid email")
        return value.strip().lower()

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        return normalize_account_status(value)

    @field_validator("folder")
    @classmethod
    def _validate_folder(cls, value: str) -> str:
        return normalize_account_folder(value)


class AccountUpdateStatus(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        return normalize_account_status(value)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    password_openai: str
    password_mail: str
    status: str
    folder: str
    created_at: datetime
    updated_at: datetime


class AccountImportRequest(BaseModel):
    text: str = Field(min_length=1)
    folder: str | None = None

    @field_validator("folder")
    @classmethod
    def _validate_folder(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_account_folder(value)


class AccountImportResponse(BaseModel):
    added: int
    duplicates: int
    skipped: int


class MailTmCreateRequest(BaseModel):
    password_length: int = Field(default=12, ge=8, le=32)
    folder: str = DEFAULT_ACCOUNT_FOLDER_NAME

    @field_validator("folder")
    @classmethod
    def _validate_folder(cls, value: str) -> str:
        return normalize_account_folder(value)


class AccountUpdateFolder(BaseModel):
    folder: str

    @field_validator("folder")
    @classmethod
    def _validate_folder(cls, value: str) -> str:
        return normalize_account_folder(value)


class AccountFolderCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return normalize_account_folder(value)


class AccountFolderRename(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return normalize_account_folder(value)


class AccountFolderDeleteRequest(BaseModel):
    move_to: str = DEFAULT_ACCOUNT_FOLDER_NAME

    @field_validator("move_to")
    @classmethod
    def _validate_move_to(cls, value: str) -> str:
        return normalize_account_folder(value)


class AccountFolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    updated_at: datetime


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
