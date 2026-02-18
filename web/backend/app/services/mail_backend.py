import email
import imaplib
import random
import re
import string
import threading
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime

import requests

from app.core.config import settings

BAN_KEYWORDS = [
    "access deactivated",
    "deactivated",
    "account suspended",
    "account disabled",
    "account has been disabled",
    "account has been deactivated",
    "suspended",
    "violation",
]


class IMAPSimpleClient:
    def __init__(self, host: str, timeout: int = 8):
        self.host = host
        self.timeout = timeout
        self.mail: imaplib.IMAP4_SSL | None = None

    def login(self, email_addr: str, password: str) -> bool:
        try:
            self.mail = imaplib.IMAP4_SSL(self.host, timeout=self.timeout)
        except (OSError, ConnectionError, TimeoutError):
            raise
        except Exception:
            return False

        try:
            self.mail.login(email_addr, password)
            return True
        except imaplib.IMAP4.error:
            return False
        except Exception:
            return False

    def logout(self) -> None:
        try:
            if self.mail:
                self.mail.logout()
        except Exception:
            pass

    def _decode_header(self, value: str | None) -> str:
        if not value:
            return "Unknown"

        try:
            decoded_parts = decode_header(value)
            chunks: list[str] = []
            for raw, encoding in decoded_parts:
                if isinstance(raw, bytes):
                    enc = encoding or "utf-8"
                    try:
                        chunks.append(raw.decode(enc))
                    except Exception:
                        chunks.append(raw.decode("utf-8", errors="ignore"))
                else:
                    chunks.append(raw)
            return "".join(chunks)
        except Exception:
            return str(value)

    def get_messages(self, limit: int = 20) -> list[dict[str, str]]:
        if not self.mail:
            return []

        try:
            self.mail.select("inbox")
            status, messages = self.mail.search(None, "ALL")
            if status != "OK":
                return []

            ids = messages[0].split()
            latest_ids = ids[-limit:] if len(ids) > limit else ids

            result: list[dict[str, str]] = []
            for mid in reversed(latest_ids):
                try:
                    _, data = self.mail.fetch(mid, "(RFC822.HEADER)")
                    for part in data:
                        if not isinstance(part, tuple):
                            continue
                        msg = email.message_from_bytes(part[1])
                        sender = self._decode_header(msg.get("From"))
                        subject = self._decode_header(msg.get("Subject"))
                        created_at = msg.get("Date") or ""
                        result.append(
                            {
                                "id": mid.decode(),
                                "from": sender,
                                "subject": subject,
                                "createdAt": created_at,
                            }
                        )
                except Exception:
                    continue
            return result
        except Exception:
            return []

    def get_message_content(self, msg_id: str) -> str:
        if not self.mail:
            return "Not connected"

        try:
            self.mail.select("inbox")
            _, data = self.mail.fetch(str(msg_id), "(RFC822)")

            raw_email = b""
            for part in data:
                if isinstance(part, tuple):
                    raw_email = part[1]
                    break

            if not raw_email:
                return "Error: empty response from IMAP"

            msg = email.message_from_bytes(raw_email)
            body = ""

            def decode_payload(payload: object) -> str:
                if isinstance(payload, str):
                    return payload
                if not isinstance(payload, bytes):
                    return str(payload)
                for enc in ["utf-8", "latin-1", "cp1252"]:
                    try:
                        return payload.decode(enc)
                    except Exception:
                        continue
                return payload.decode("utf-8", errors="ignore")

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition") or "")
                    if "attachment" in content_disposition.lower():
                        continue

                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = decode_payload(payload)
                            break

                    if content_type == "text/html" and not body:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = decode_payload(payload)
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = decode_payload(payload)

            return body or "No text content found"
        except Exception as exc:
            return f"Error reading message: {exc}"


@dataclass
class ConnectionState:
    user_id: int
    account_id: int
    email: str
    password: str
    account_type: str
    token: str | None = None
    imap_client: IMAPSimpleClient | None = None
    imap_host: str | None = None


class MailBackendService:
    def __init__(self) -> None:
        self._connections: dict[tuple[int, int], ConnectionState] = {}
        self._connections_lock = threading.Lock()

        self._mail_tm_domains: list[str] = []
        self._domains_loaded = False
        self._domains_lock = threading.Lock()

        self._imap_host_cache: dict[str, str] = {}
        self._imap_host_lock = threading.Lock()

    @staticmethod
    def extract_sender_address(from_field: object) -> str:
        if isinstance(from_field, dict):
            return str(from_field.get("address", ""))

        value = str(from_field)
        if "<" in value and ">" in value:
            try:
                return value[value.index("<") + 1 : value.index(">")]
            except Exception:
                return value
        return value

    @staticmethod
    def is_openai_ban_message(sender: str, subject: str) -> bool:
        sender_lower = sender.lower()
        subject_lower = subject.lower()
        if "openai" not in sender_lower:
            return False
        return any(keyword in subject_lower for keyword in BAN_KEYWORDS)

    @staticmethod
    def _extract_code(text: str) -> str | None:
        match = re.search(r"\b(\d{6})\b", text)
        if not match:
            return None
        return match.group(1)

    @staticmethod
    def _format_date(value: str) -> str:
        if not value:
            return ""
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except Exception:
            pass
        try:
            dt = parsedate_to_datetime(value)
            return dt.strftime("%H:%M:%S")
        except Exception:
            return value

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        timeout = kwargs.pop("timeout", (5, 10))
        response = requests.request(method, url, timeout=timeout, **kwargs)
        return response

    @staticmethod
    def _normalize_credentials(email_addr: str, password: str) -> tuple[str, str]:
        """Trim accidental whitespace from credentials (common on mobile copy/paste)."""
        return email_addr.strip(), password.strip()

    def load_mail_tm_domains(self, force: bool = False) -> list[str]:
        with self._domains_lock:
            if self._domains_loaded and not force:
                return self._mail_tm_domains

        domains: list[str] = []
        try:
            res = self._request("GET", f"{settings.mail_tm_api_url}/domains")
            if res.status_code == 200:
                data = res.json().get("hydra:member", [])
                domains = [item.get("domain", "") for item in data if item.get("domain")]
        except Exception:
            domains = []

        with self._domains_lock:
            if domains:
                self._mail_tm_domains = domains
            self._domains_loaded = True
            return self._mail_tm_domains

    def _is_mail_tm(self, email_addr: str) -> bool:
        domain = email_addr.split("@")[-1].lower()
        if domain.endswith("mail.tm"):
            return True
        domains = self.load_mail_tm_domains()
        return domain in domains

    def _get_imap_hosts(self, domain: str) -> list[str]:
        with self._imap_host_lock:
            cached = self._imap_host_cache.get(domain)

        hosts = [cached, "imap.firstmail.ltd", f"imap.{domain}"]
        unique_hosts: list[str] = []
        for host in hosts:
            if host and host not in unique_hosts:
                unique_hosts.append(host)
        return unique_hosts

    def _remember_imap_host(self, domain: str, host: str) -> None:
        with self._imap_host_lock:
            self._imap_host_cache[domain] = host

    def _close_state(self, state: ConnectionState) -> None:
        if state.imap_client:
            state.imap_client.logout()

    def clear_connection(self, user_id: int, account_id: int) -> None:
        key = (user_id, account_id)
        with self._connections_lock:
            state = self._connections.pop(key, None)
        if state:
            self._close_state(state)

    def connect(self, user_id: int, account_id: int, email_addr: str, password: str) -> dict[str, object]:
        email_addr, password = self._normalize_credentials(email_addr, password)
        key = (user_id, account_id)
        old_state: ConnectionState | None = None
        with self._connections_lock:
            old_state = self._connections.pop(key, None)
        if old_state:
            self._close_state(old_state)

        state = ConnectionState(
            user_id=user_id,
            account_id=account_id,
            email=email_addr,
            password=password,
            account_type="",
        )

        domain = email_addr.split("@")[-1].lower()

        # Always try mail.tm API first — domains may not end with "mail.tm"
        # (e.g. dollicons.com) and the domain list may not be loaded yet.
        try:
            payload = {"address": email_addr, "password": password}
            res = self._request("POST", f"{settings.mail_tm_api_url}/token", json=payload)
            if res.status_code == 200:
                token = res.json().get("token")
                if token:
                    state.account_type = "api"
                    state.token = token
                    with self._connections_lock:
                        self._connections[key] = state
                    return {"connected": True, "account_type": state.account_type}
        except requests.RequestException:
            pass

        for host in self._get_imap_hosts(domain):
            client = IMAPSimpleClient(host=host, timeout=8)
            try:
                ok = client.login(email_addr, password)
            except (OSError, ConnectionError, TimeoutError):
                continue

            if ok:
                state.account_type = "imap"
                state.imap_client = client
                state.imap_host = host
                self._remember_imap_host(domain, host)
                with self._connections_lock:
                    self._connections[key] = state
                return {"connected": True, "account_type": state.account_type}

            client.logout()

        raise RuntimeError("Failed to login with API and IMAP")

    def _ensure_connection(
        self,
        user_id: int,
        account_id: int,
        email_addr: str,
        password: str,
    ) -> ConnectionState:
        email_addr, password = self._normalize_credentials(email_addr, password)
        key = (user_id, account_id)
        with self._connections_lock:
            state = self._connections.get(key)

        if state:
            return state

        self.connect(user_id, account_id, email_addr, password)
        with self._connections_lock:
            state = self._connections.get(key)
        if not state:
            raise RuntimeError("Connection state missing after connect")
        return state

    def fetch_messages(
        self,
        user_id: int,
        account_id: int,
        email_addr: str,
        password: str,
    ) -> list[dict[str, str]]:
        email_addr, password = self._normalize_credentials(email_addr, password)
        state = self._ensure_connection(user_id, account_id, email_addr, password)

        if state.account_type == "api":
            headers = {"Authorization": f"Bearer {state.token}"}
            res = self._request("GET", f"{settings.mail_tm_api_url}/messages", headers=headers)

            if res.status_code == 401:
                self.connect(user_id, account_id, email_addr, password)
                state = self._ensure_connection(user_id, account_id, email_addr, password)
                headers = {"Authorization": f"Bearer {state.token}"}
                res = self._request("GET", f"{settings.mail_tm_api_url}/messages", headers=headers)

            if res.status_code != 200:
                raise RuntimeError(f"mail.tm messages failed: {res.status_code}")

            items = res.json().get("hydra:member", [])
            result: list[dict[str, str]] = []
            for msg in items:
                sender = self.extract_sender_address(msg.get("from", {}))
                subject = msg.get("subject") or "(без темы)"
                created_at_raw = str(msg.get("createdAt") or "")
                result.append(
                    {
                        "id": str(msg.get("id") or ""),
                        "sender": sender,
                        "subject": subject,
                        "created_at": self._format_date(created_at_raw),
                    }
                )
            return result

        if not state.imap_client:
            raise RuntimeError("IMAP connection missing")

        imap_messages = state.imap_client.get_messages(limit=20)
        result = []
        for msg in imap_messages:
            sender = self.extract_sender_address(msg.get("from", ""))
            subject = msg.get("subject") or "(без темы)"
            created_at_raw = str(msg.get("createdAt") or "")
            result.append(
                {
                    "id": str(msg.get("id") or ""),
                    "sender": sender,
                    "subject": subject,
                    "created_at": self._format_date(created_at_raw),
                }
            )
        return result

    def fetch_message(
        self,
        user_id: int,
        account_id: int,
        email_addr: str,
        password: str,
        message_id: str,
        sender_hint: str | None = None,
        subject_hint: str | None = None,
    ) -> dict[str, str | None]:
        email_addr, password = self._normalize_credentials(email_addr, password)
        state = self._ensure_connection(user_id, account_id, email_addr, password)

        if state.account_type == "api":
            headers = {"Authorization": f"Bearer {state.token}"}
            res = self._request(
                "GET",
                f"{settings.mail_tm_api_url}/messages/{message_id}",
                headers=headers,
            )

            if res.status_code == 401:
                self.connect(user_id, account_id, email_addr, password)
                state = self._ensure_connection(user_id, account_id, email_addr, password)
                headers = {"Authorization": f"Bearer {state.token}"}
                res = self._request(
                    "GET",
                    f"{settings.mail_tm_api_url}/messages/{message_id}",
                    headers=headers,
                )

            if res.status_code != 200:
                raise RuntimeError(f"mail.tm message load failed: {res.status_code}")

            data = res.json()
            sender = self.extract_sender_address(data.get("from", {}))
            subject = data.get("subject") or "(без темы)"
            raw_text = data.get("text") or ""
            raw_html = data.get("html") or ""
            text = raw_text or raw_html or "Нет текстового содержимого"
            return {
                "id": str(message_id),
                "sender": sender,
                "subject": subject,
                "text": text,
                "html": raw_html or None,
                "code": self._extract_code(text),
            }

        if not state.imap_client:
            raise RuntimeError("IMAP connection missing")

        text = state.imap_client.get_message_content(message_id)
        sender = sender_hint or "IMAP Sender"
        subject = subject_hint or "IMAP Message"
        has_html = bool(text and "<html" in text.lower()[:200])
        return {
            "id": str(message_id),
            "sender": sender,
            "subject": subject,
            "text": text,
            "html": text if has_html else None,
            "code": self._extract_code(text),
        }

    def create_mail_tm_account(self, password_length: int = 12) -> tuple[str, str]:
        domains = self.load_mail_tm_domains(force=True)
        if not domains:
            raise RuntimeError("Could not load mail.tm domains")

        domain = random.choice(domains)
        username = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
        password_chars = string.ascii_letters + string.digits
        password = "".join(random.choice(password_chars) for _ in range(password_length))
        email_addr = f"{username}@{domain}"

        payload = {
            "address": email_addr,
            "password": password,
        }
        res = self._request("POST", f"{settings.mail_tm_api_url}/accounts", json=payload)
        if res.status_code != 201:
            raise RuntimeError(f"mail.tm create account failed: {res.status_code}")

        return email_addr, password

    def delete_mail_tm_account(self, email_addr: str, password: str) -> None:
        email_addr, password = self._normalize_credentials(email_addr, password)
        if not self._is_mail_tm(email_addr):
            raise RuntimeError("mailbox delete is supported only for mail.tm accounts")

        payload = {"address": email_addr, "password": password}
        auth_res = self._request("POST", f"{settings.mail_tm_api_url}/token", json=payload)
        if auth_res.status_code == 401:
            raise RuntimeError("wrong mailbox credentials")
        if auth_res.status_code != 200:
            raise RuntimeError(f"mail.tm auth failed: {auth_res.status_code}")

        token = auth_res.json().get("token")
        if not token:
            raise RuntimeError("mail.tm token missing")

        headers = {"Authorization": f"Bearer {token}"}
        me_res = self._request("GET", f"{settings.mail_tm_api_url}/me", headers=headers)
        if me_res.status_code != 200:
            raise RuntimeError(f"mail.tm me failed: {me_res.status_code}")

        account_id = me_res.json().get("id")
        if not account_id:
            raise RuntimeError("mail.tm account id missing")

        delete_res = self._request(
            "DELETE",
            f"{settings.mail_tm_api_url}/accounts/{account_id}",
            headers=headers,
        )
        if delete_res.status_code not in (200, 204):
            raise RuntimeError(f"mail.tm delete failed: {delete_res.status_code}")

    def check_account_for_ban(self, email_addr: str, password: str) -> tuple[str, str]:
        email_addr, password = self._normalize_credentials(email_addr, password)
        domain = email_addr.split("@")[-1].lower()
        is_mail_tm = self._is_mail_tm(email_addr)

        if is_mail_tm:
            try:
                payload = {"address": email_addr, "password": password}
                res = self._request("POST", f"{settings.mail_tm_api_url}/token", json=payload)

                if res.status_code == 401:
                    return "invalid_password", "wrong_credentials"
                if res.status_code != 200:
                    return "error", f"auth_failed_{res.status_code}"

                token = res.json().get("token")
                if not token:
                    return "error", "no_token"

                headers = {"Authorization": f"Bearer {token}"}
                res = self._request("GET", f"{settings.mail_tm_api_url}/messages", headers=headers)
                if res.status_code != 200:
                    return "error", "messages_failed"

                messages = res.json().get("hydra:member", [])
                for msg in messages:
                    sender = self.extract_sender_address(msg.get("from", {}))
                    subject = str(msg.get("subject") or "")
                    if self.is_openai_ban_message(sender, subject):
                        return "banned", "access_deactivated"
                return "ok", "no_ban_found"
            except requests.RequestException as exc:
                return "error", str(exc)

        imap_client: IMAPSimpleClient | None = None
        any_host_reached = False

        try:
            for host in self._get_imap_hosts(domain):
                client = IMAPSimpleClient(host=host, timeout=5)
                try:
                    if client.login(email_addr, password):
                        imap_client = client
                        self._remember_imap_host(domain, host)
                        break
                    any_host_reached = True
                    client.logout()
                except (OSError, ConnectionError, TimeoutError):
                    continue

            if not imap_client:
                if any_host_reached:
                    return "invalid_password", "imap_login_failed"
                return "error", "imap_connection_failed"

            messages = imap_client.get_messages(limit=15)
            for msg in messages:
                sender = self.extract_sender_address(msg.get("from", ""))
                subject = str(msg.get("subject") or "")
                if self.is_openai_ban_message(sender, subject):
                    return "banned", "access_deactivated"

            return "ok", "no_ban_found"
        except Exception as exc:
            return "error", str(exc)
        finally:
            if imap_client:
                imap_client.logout()


mail_backend_service = MailBackendService()
