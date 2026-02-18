from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import AccountFolder, ManagedAccount, User
from app.schemas import (
    AccountCreate,
    AccountFolderCreate,
    AccountFolderDeleteRequest,
    AccountFolderOut,
    AccountFolderRename,
    AccountImportRequest,
    AccountImportResponse,
    AccountOut,
    AccountUpdateFolder,
    AccountUpdateStatus,
    MailTmCreateRequest,
    normalize_account_folder,
)
from app.services.account_parser import parse_accounts_blob
from app.services.mail_backend import mail_backend_service

router = APIRouter()


def _get_owned_account(db: Session, user: User, account_id: int) -> ManagedAccount:
    account = (
        db.query(ManagedAccount)
        .filter(ManagedAccount.id == account_id, ManagedAccount.user_id == user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    return account


def _find_folder_case_insensitive(
    db: Session,
    user: User,
    folder_name: str,
) -> AccountFolder | None:
    normalized = normalize_account_folder(folder_name)
    return (
        db.query(AccountFolder)
        .filter(
            AccountFolder.user_id == user.id,
            func.lower(AccountFolder.name) == normalized.lower(),
        )
        .first()
    )


def _ensure_default_folder(db: Session, user: User) -> AccountFolder:
    default_folder = _find_folder_case_insensitive(db, user, "Основная")
    if default_folder:
        return default_folder

    created = AccountFolder(user_id=user.id, name="Основная")
    db.add(created)
    db.flush()
    return created


def _ensure_folder_exists(db: Session, user: User, folder_name: str) -> str:
    normalized = normalize_account_folder(folder_name)
    existing = _find_folder_case_insensitive(db, user, normalized)
    if existing:
        return existing.name

    db.add(AccountFolder(user_id=user.id, name=normalized))
    db.flush()
    return normalized


def _sync_folders_from_accounts(db: Session, user: User) -> None:
    _ensure_default_folder(db, user)
    existing = {
        row[0].lower()
        for row in db.query(AccountFolder.name)
        .filter(AccountFolder.user_id == user.id)
        .all()
    }
    used: dict[str, str] = {}
    for row in (
        db.query(ManagedAccount.folder)
        .filter(ManagedAccount.user_id == user.id)
        .all()
    ):
        normalized = normalize_account_folder(row[0])
        key = normalized.lower()
        if key not in used:
            used[key] = normalized

    for key, folder_name in used.items():
        if key in existing:
            continue
        db.add(AccountFolder(user_id=user.id, name=folder_name))


def _get_owned_folder(db: Session, user: User, folder_id: int) -> AccountFolder:
    folder = (
        db.query(AccountFolder)
        .filter(AccountFolder.id == folder_id, AccountFolder.user_id == user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="folder not found")
    return folder


@router.get("", response_model=list[AccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ManagedAccount]:
    _sync_folders_from_accounts(db, current_user)
    folders_added = any(isinstance(item, AccountFolder) for item in db.new)
    accounts = (
        db.query(ManagedAccount)
        .filter(ManagedAccount.user_id == current_user.id)
        .order_by(ManagedAccount.created_at.desc())
        .all()
    )
    changed = False
    for account in accounts:
        normalized = normalize_account_folder(account.folder)
        if account.folder != normalized:
            account.folder = normalized
            changed = True
    if changed or folders_added:
        db.commit()
    else:
        db.flush()
    return accounts


@router.get("/folders", response_model=list[AccountFolderOut])
def list_account_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AccountFolder]:
    _sync_folders_from_accounts(db, current_user)
    db.commit()
    folders = (
        db.query(AccountFolder)
        .filter(AccountFolder.user_id == current_user.id)
        .order_by(AccountFolder.created_at.asc())
        .all()
    )
    folders.sort(key=lambda folder: (folder.name.lower() != "основная", folder.created_at))
    return folders


@router.post("/folders", response_model=AccountFolderOut, status_code=status.HTTP_201_CREATED)
def create_account_folder(
    payload: AccountFolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountFolder:
    existing = _find_folder_case_insensitive(db, current_user, payload.name)
    if existing:
        raise HTTPException(status_code=400, detail="folder already exists")

    folder = AccountFolder(user_id=current_user.id, name=normalize_account_folder(payload.name))
    db.add(folder)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="folder already exists")
    db.refresh(folder)
    return folder


@router.patch("/folders/{folder_id}", response_model=AccountFolderOut)
def rename_account_folder(
    folder_id: int,
    payload: AccountFolderRename,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountFolder:
    folder = _get_owned_folder(db, current_user, folder_id)
    if folder.name.lower() == "основная":
        raise HTTPException(status_code=400, detail="default folder cannot be renamed")

    new_name = normalize_account_folder(payload.name)
    if folder.name.lower() == new_name.lower():
        return folder

    conflict = _find_folder_case_insensitive(db, current_user, new_name)
    if conflict and conflict.id != folder.id:
        raise HTTPException(status_code=400, detail="folder already exists")

    old_name = folder.name
    folder.name = new_name

    accounts = (
        db.query(ManagedAccount)
        .filter(
            ManagedAccount.user_id == current_user.id,
            func.lower(ManagedAccount.folder) == old_name.lower(),
        )
        .all()
    )
    for account in accounts:
        account.folder = new_name

    db.commit()
    db.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account_folder(
    folder_id: int,
    payload: AccountFolderDeleteRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    folder = _get_owned_folder(db, current_user, folder_id)
    if folder.name.lower() == "основная":
        raise HTTPException(status_code=400, detail="default folder cannot be deleted")

    target_name = normalize_account_folder(
        payload.move_to if payload is not None else "Основная"
    )
    if target_name.lower() == folder.name.lower():
        target_name = "Основная"
    target_folder_name = _ensure_folder_exists(db, current_user, target_name)

    accounts = (
        db.query(ManagedAccount)
        .filter(
            ManagedAccount.user_id == current_user.id,
            func.lower(ManagedAccount.folder) == folder.name.lower(),
        )
        .all()
    )
    for account in accounts:
        account.folder = target_folder_name

    db.delete(folder)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagedAccount:
    password_mail = payload.password_mail or payload.password_openai
    folder_name = _ensure_folder_exists(db, current_user, payload.folder)
    account = ManagedAccount(
        user_id=current_user.id,
        email=payload.email.strip().lower(),
        password_openai=payload.password_openai,
        password_mail=password_mail,
        status=payload.status,
        folder=folder_name,
    )

    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="account already exists")

    db.refresh(account)
    return account


@router.post("/import", response_model=AccountImportResponse)
def import_accounts(
    payload: AccountImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountImportResponse:
    parsed_accounts = parse_accounts_blob(payload.text)
    if not parsed_accounts:
        return AccountImportResponse(added=0, duplicates=0, skipped=0)

    fallback_folder = normalize_account_folder(payload.folder)
    _ensure_folder_exists(db, current_user, fallback_folder)

    existing_emails = {
        row[0]
        for row in db.query(ManagedAccount.email)
        .filter(ManagedAccount.user_id == current_user.id)
        .all()
    }

    added = 0
    duplicates = 0
    skipped = 0

    for parsed in parsed_accounts:
        if parsed.email in existing_emails:
            duplicates += 1
            continue
        if "@" not in parsed.email:
            skipped += 1
            continue

        target_folder = normalize_account_folder(parsed.folder or fallback_folder)
        target_folder = _ensure_folder_exists(db, current_user, target_folder)

        account = ManagedAccount(
            user_id=current_user.id,
            email=parsed.email,
            password_openai=parsed.password_openai,
            password_mail=parsed.password_mail,
            status=parsed.status,
            folder=target_folder,
        )
        db.add(account)
        existing_emails.add(parsed.email)
        added += 1

    if added:
        db.commit()
    else:
        db.rollback()

    return AccountImportResponse(added=added, duplicates=duplicates, skipped=skipped)


@router.post("/create-mailtm", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_mail_tm_account(
    payload: MailTmCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagedAccount:
    try:
        email, password = mail_backend_service.create_mail_tm_account(payload.password_length)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    folder_name = _ensure_folder_exists(db, current_user, payload.folder)
    account = ManagedAccount(
        user_id=current_user.id,
        email=email,
        password_openai=password,
        password_mail=password,
        status="not_registered",
        folder=folder_name,
    )

    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="created account already exists")

    db.refresh(account)
    return account


@router.patch("/{account_id}/status", response_model=AccountOut)
def update_account_status(
    account_id: int,
    payload: AccountUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagedAccount:
    account = _get_owned_account(db, current_user, account_id)
    account.status = payload.status
    db.commit()
    db.refresh(account)
    return account


@router.patch("/{account_id}/folder", response_model=AccountOut)
def update_account_folder(
    account_id: int,
    payload: AccountUpdateFolder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagedAccount:
    account = _get_owned_account(db, current_user, account_id)
    account.folder = _ensure_folder_exists(db, current_user, payload.folder)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}/mailbox", status_code=status.HTTP_204_NO_CONTENT)
def delete_account_mailbox(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    account = _get_owned_account(db, current_user, account_id)
    try:
        mail_backend_service.delete_mail_tm_account(account.email, account.password_mail)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    mail_backend_service.clear_connection(current_user.id, account.id)
    db.delete(account)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    account = _get_owned_account(db, current_user, account_id)
    mail_backend_service.clear_connection(current_user.id, account.id)
    db.delete(account)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
