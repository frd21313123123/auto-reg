from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.deps import get_current_user, get_db
from app.models import AccountFolder, ManagedAccount, User
from app.schemas import (
    AccountCreate,
    AccountImportRequest,
    AccountImportResponse,
    AccountOut,
    AccountUpdateStatus,
    BulkAccountDeleteRequest,
    BulkAccountMoveRequest,
    BulkActionResponse,
    DeleteAllAccountsRequest,
    FolderCreate,
    FolderOut,
    MailTmCreateRequest,
)
from app.services.account_parser import parse_accounts_blob
from app.services.mail_backend import mail_backend_service

router = APIRouter()


def _get_owned_account(db: Session, user: User, account_id: int) -> ManagedAccount:
    account = (
        db.query(ManagedAccount)
        .options(selectinload(ManagedAccount.folder))
        .filter(ManagedAccount.id == account_id, ManagedAccount.user_id == user.id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    return account


def _get_owned_folder(db: Session, user: User, folder_id: int) -> AccountFolder:
    folder = (
        db.query(AccountFolder)
        .filter(AccountFolder.id == folder_id, AccountFolder.user_id == user.id)
        .first()
    )
    if not folder:
        raise HTTPException(status_code=404, detail="folder not found")
    return folder


def _resolve_optional_folder(
    db: Session,
    user: User,
    folder_id: int | None,
) -> AccountFolder | None:
    if folder_id is None:
        return None
    return _get_owned_folder(db, user, folder_id)


def _query_owned_accounts(db: Session, user: User):
    return (
        db.query(ManagedAccount)
        .options(selectinload(ManagedAccount.folder))
        .filter(ManagedAccount.user_id == user.id)
    )


def _delete_accounts_for_user(current_user: User, accounts: list[ManagedAccount], db: Session) -> int:
    for account in accounts:
        mail_backend_service.clear_connection(current_user.id, account.id)
        db.delete(account)
    db.commit()
    return len(accounts)


@router.get("/folders", response_model=list[FolderOut])
def list_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[FolderOut]:
    rows = (
        db.query(AccountFolder, func.count(ManagedAccount.id))
        .outerjoin(ManagedAccount, ManagedAccount.folder_id == AccountFolder.id)
        .filter(AccountFolder.user_id == current_user.id)
        .group_by(AccountFolder.id)
        .order_by(AccountFolder.name.asc())
        .all()
    )
    return [
        FolderOut(
            id=folder.id,
            name=folder.name,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            account_count=account_count,
        )
        for folder, account_count in rows
    ]


@router.post("/folders", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FolderOut:
    folder = AccountFolder(user_id=current_user.id, name=payload.name)
    db.add(folder)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="folder already exists")

    db.refresh(folder)
    return FolderOut(
        id=folder.id,
        name=folder.name,
        created_at=folder.created_at,
        updated_at=folder.updated_at,
        account_count=0,
    )


@router.get("", response_model=list[AccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ManagedAccount]:
    return (
        _query_owned_accounts(db, current_user)
        .order_by(ManagedAccount.created_at.desc())
        .all()
    )


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagedAccount:
    folder = _resolve_optional_folder(db, current_user, payload.folder_id)
    password_mail = payload.password_mail or payload.password_openai
    account = ManagedAccount(
        user_id=current_user.id,
        folder_id=folder.id if folder else None,
        email=payload.email.strip().lower(),
        password_openai=payload.password_openai,
        password_mail=password_mail,
        status=payload.status,
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
    folder = _resolve_optional_folder(db, current_user, payload.folder_id)
    parsed_accounts = parse_accounts_blob(payload.text)
    if not parsed_accounts:
        return AccountImportResponse(added=0, duplicates=0, skipped=0)

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

        account = ManagedAccount(
            user_id=current_user.id,
            folder_id=folder.id if folder else None,
            email=parsed.email,
            password_openai=parsed.password_openai,
            password_mail=parsed.password_mail,
            status=parsed.status,
        )
        db.add(account)
        existing_emails.add(parsed.email)
        added += 1

    if added:
        db.commit()

    return AccountImportResponse(added=added, duplicates=duplicates, skipped=skipped)


@router.post("/create-mailtm", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_mail_tm_account(
    payload: MailTmCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagedAccount:
    folder = _resolve_optional_folder(db, current_user, payload.folder_id)
    try:
        email, password = mail_backend_service.create_mail_tm_account(payload.password_length)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    account = ManagedAccount(
        user_id=current_user.id,
        folder_id=folder.id if folder else None,
        email=email,
        password_openai=password,
        password_mail=password,
        status="not_registered",
    )

    db.add(account)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="created account already exists")

    db.refresh(account)
    return account


@router.post("/bulk-move", response_model=BulkActionResponse)
def bulk_move_accounts(
    payload: BulkAccountMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkActionResponse:
    folder = _resolve_optional_folder(db, current_user, payload.folder_id)
    account_ids = list(dict.fromkeys(payload.account_ids))
    accounts = (
        _query_owned_accounts(db, current_user)
        .filter(ManagedAccount.id.in_(account_ids))
        .all()
    )
    for account in accounts:
        account.folder_id = folder.id if folder else None
    db.commit()
    return BulkActionResponse(affected=len(accounts))


@router.post("/bulk-delete", response_model=BulkActionResponse)
def bulk_delete_accounts(
    payload: BulkAccountDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkActionResponse:
    account_ids = list(dict.fromkeys(payload.account_ids))
    accounts = (
        _query_owned_accounts(db, current_user)
        .filter(ManagedAccount.id.in_(account_ids))
        .all()
    )
    affected = _delete_accounts_for_user(current_user, accounts, db)
    return BulkActionResponse(affected=affected)


@router.post("/delete-all", response_model=BulkActionResponse)
def delete_all_accounts(
    payload: DeleteAllAccountsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkActionResponse:
    accounts_query = _query_owned_accounts(db, current_user)
    if payload.scope == "folder":
        folder = _get_owned_folder(db, current_user, int(payload.folder_id))
        accounts_query = accounts_query.filter(ManagedAccount.folder_id == folder.id)
    elif payload.scope == "unassigned":
        accounts_query = accounts_query.filter(ManagedAccount.folder_id.is_(None))

    accounts = accounts_query.all()
    affected = _delete_accounts_for_user(current_user, accounts, db)
    return BulkActionResponse(affected=affected)


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
