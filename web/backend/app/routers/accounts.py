from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import ManagedAccount, User
from app.schemas import (
    AccountCreate,
    AccountImportRequest,
    AccountImportResponse,
    AccountOut,
    AccountUpdateStatus,
    MailTmCreateRequest,
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


@router.get("", response_model=list[AccountOut])
def list_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ManagedAccount]:
    return (
        db.query(ManagedAccount)
        .filter(ManagedAccount.user_id == current_user.id)
        .order_by(ManagedAccount.created_at.desc())
        .all()
    )


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ManagedAccount:
    password_mail = payload.password_mail or payload.password_openai
    account = ManagedAccount(
        user_id=current_user.id,
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
    try:
        email, password = mail_backend_service.create_mail_tm_account(payload.password_length)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    account = ManagedAccount(
        user_id=current_user.id,
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
