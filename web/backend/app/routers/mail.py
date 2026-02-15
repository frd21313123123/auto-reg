from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import ManagedAccount, User
from app.schemas import (
    BanCheckResult,
    BulkBanCheckRequest,
    BulkBanCheckResponse,
    ConnectResponse,
    MessageDetail,
    MessageSummary,
)
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


@router.post("/accounts/{account_id}/connect", response_model=ConnectResponse)
def connect_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConnectResponse:
    account = _get_owned_account(db, current_user, account_id)

    try:
        result = mail_backend_service.connect(
            current_user.id,
            account.id,
            account.email,
            account.password_mail,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return ConnectResponse(**result)


@router.get("/accounts/{account_id}/messages", response_model=list[MessageSummary])
def get_messages(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageSummary]:
    account = _get_owned_account(db, current_user, account_id)

    try:
        messages = mail_backend_service.fetch_messages(
            current_user.id,
            account.id,
            account.email,
            account.password_mail,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return [MessageSummary(**message) for message in messages]


@router.get("/accounts/{account_id}/messages/{message_id}", response_model=MessageDetail)
def get_message_detail(
    account_id: int,
    message_id: str,
    sender: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageDetail:
    account = _get_owned_account(db, current_user, account_id)

    try:
        message = mail_backend_service.fetch_message(
            current_user.id,
            account.id,
            account.email,
            account.password_mail,
            message_id,
            sender_hint=sender,
            subject_hint=subject,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return MessageDetail(**message)


@router.post("/accounts/{account_id}/ban-check", response_model=BanCheckResult)
def ban_check_single(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BanCheckResult:
    account = _get_owned_account(db, current_user, account_id)

    result, reason = mail_backend_service.check_account_for_ban(
        account.email,
        account.password_mail,
    )

    if result == "banned":
        account.status = "banned"
    elif result == "invalid_password":
        account.status = "invalid_password"

    db.commit()

    return BanCheckResult(
        account_id=account.id,
        email=account.email,
        result=result,
        reason=reason,
    )


@router.post("/ban-check/bulk", response_model=BulkBanCheckResponse)
def ban_check_bulk(
    payload: BulkBanCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkBanCheckResponse:
    query = db.query(ManagedAccount).filter(ManagedAccount.user_id == current_user.id)

    if payload.account_ids:
        query = query.filter(ManagedAccount.id.in_(payload.account_ids))

    accounts = query.all()
    if not accounts:
        return BulkBanCheckResponse(
            checked=0,
            banned=0,
            invalid_password=0,
            errors=0,
            results=[],
        )

    checked = 0
    banned = 0
    invalid_password = 0
    errors = 0
    results: list[BanCheckResult] = []

    account_by_id = {account.id: account for account in accounts}

    def worker(account: ManagedAccount) -> tuple[int, str, str, str]:
        result, reason = mail_backend_service.check_account_for_ban(
            account.email,
            account.password_mail,
        )
        return account.id, account.email, result, reason

    with ThreadPoolExecutor(max_workers=payload.max_workers) as executor:
        future_map = {executor.submit(worker, account): account.id for account in accounts}

        for future in as_completed(future_map):
            checked += 1
            account_id, email, result, reason = future.result()
            account = account_by_id[account_id]

            if result == "banned":
                account.status = "banned"
                banned += 1
            elif result == "invalid_password":
                account.status = "invalid_password"
                invalid_password += 1
            elif result == "error":
                errors += 1

            results.append(
                BanCheckResult(
                    account_id=account_id,
                    email=email,
                    result=result,
                    reason=reason,
                )
            )

    db.commit()

    return BulkBanCheckResponse(
        checked=checked,
        banned=banned,
        invalid_password=invalid_password,
        errors=errors,
        results=results,
    )
