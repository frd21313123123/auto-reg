from dataclasses import dataclass

from app.schemas import normalize_account_folder, normalize_account_status


@dataclass(slots=True)
class ParsedAccount:
    email: str
    password_openai: str
    password_mail: str
    status: str = "not_registered"
    folder: str | None = None


def parse_account_line(raw_line: str) -> ParsedAccount | None:
    line = raw_line.strip()
    if not line:
        return None

    email = ""
    password_openai = ""
    password_mail = ""
    status = "not_registered"
    folder = None

    if " / " in line:
        parts = [p.strip() for p in line.split(" / ")]
        if len(parts) >= 2:
            email = parts[0].lower()
            passwords = parts[1]
            if ";" in passwords:
                p1, p2 = passwords.split(";", 1)
                password_openai = p1.strip()
                password_mail = p2.strip()
            else:
                password_openai = passwords.strip()
                password_mail = passwords.strip()
            if len(parts) >= 3:
                try:
                    status = normalize_account_status(parts[2])
                except ValueError:
                    pass
            if len(parts) >= 4:
                try:
                    folder = normalize_account_folder(parts[3])
                except ValueError:
                    folder = None
    elif ":" in line:
        email, passwords = [p.strip() for p in line.split(":", 1)]
        email = email.lower()
        if ";" in passwords:
            p1, p2 = passwords.split(";", 1)
            password_openai = p1.strip()
            password_mail = p2.strip()
        else:
            password_openai = passwords.strip()
            password_mail = passwords.strip()
    elif "\t" in line:
        email, passwords = [p.strip() for p in line.split("\t", 1)]
        email = email.lower()
        if ";" in passwords:
            p1, p2 = passwords.split(";", 1)
            password_openai = p1.strip()
            password_mail = p2.strip()
        else:
            password_openai = passwords.strip()
            password_mail = passwords.strip()

    if "@" not in email:
        return None
    if not password_openai and not password_mail:
        return None

    if not password_openai:
        password_openai = password_mail
    if not password_mail:
        password_mail = password_openai

    return ParsedAccount(
        email=email,
        password_openai=password_openai,
        password_mail=password_mail,
        status=status,
        folder=folder,
    )


def parse_accounts_blob(text: str) -> list[ParsedAccount]:
    parsed: list[ParsedAccount] = []
    for line in text.splitlines():
        account = parse_account_line(line)
        if account:
            parsed.append(account)
    return parsed
