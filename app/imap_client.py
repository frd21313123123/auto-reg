# -*- coding: utf-8 -*-
"""
IMAP клиент для работы с почтой
"""

import imaplib
import email
import re
from email.header import decode_header


class IMAPClient:
    """Клиент для работы с почтой через IMAP"""
    
    def __init__(self, host="imap.firstmail.ltd", timeout=8):
        self.host = host
        self.timeout = timeout
        self.mail = None
    
    def login(self, email_addr, password):
        """Авторизация на IMAP сервере.

        Returns True при успешном логине, False при неверных учётных данных.
        Raises OSError/ConnectionError/TimeoutError если сервер недоступен.
        """
        try:
            self.mail = imaplib.IMAP4_SSL(self.host, timeout=self.timeout)
        except (OSError, ConnectionError, TimeoutError):
            # Сервер недоступен — пробрасываем наверх для различения от auth fail
            raise
        except Exception:
            return False
        try:
            self.mail.login(email_addr, password)
            return True
        except imaplib.IMAP4.error:
            # Неверные учётные данные
            return False
        except Exception:
            return False
    
    def logout(self):
        """Выход из IMAP сессии"""
        try:
            if self.mail:
                self.mail.logout()
        except:
            pass

    @staticmethod
    def _normalize_folder_name(folder):
        if not folder:
            return "INBOX"
        return str(folder).strip().strip('"') or "INBOX"

    def _parse_folder_name(self, folder_info):
        """Извлекает имя папки из ответа IMAP LIST."""
        if isinstance(folder_info, bytes):
            raw = folder_info.decode("utf-8", errors="ignore")
        else:
            raw = str(folder_info)
        raw = raw.strip()
        if not raw:
            return None

        quoted_parts = re.findall(r'"([^"]+)"', raw)
        if quoted_parts:
            return self._normalize_folder_name(quoted_parts[-1])

        parts = raw.rsplit(" ", 1)
        if len(parts) == 2:
            return self._normalize_folder_name(parts[-1])
        return self._normalize_folder_name(raw)

    def _select_folder(self, folder="INBOX"):
        """Пытается выбрать папку, при ошибке откатывается на INBOX."""
        if not self.mail:
            return "NO", "INBOX"

        folder_name = self._normalize_folder_name(folder)
        candidates = [folder_name]
        if folder_name.upper() != "INBOX":
            candidates.append("INBOX")

        for candidate in candidates:
            try:
                status, _ = self.mail.select(f'"{candidate}"')
                if status == "OK":
                    return "OK", candidate
            except Exception:
                pass
        return "NO", folder_name

    def list_folders(self):
        """Возвращает список доступных папок IMAP."""
        if not self.mail:
            return ["INBOX"]
        try:
            status, folders = self.mail.list()
            if status != "OK":
                return ["INBOX"]

            result = []
            for folder_info in folders or []:
                folder_name = self._parse_folder_name(folder_info)
                if folder_name and folder_name not in result:
                    result.append(folder_name)

            inbox_index = None
            for i, folder_name in enumerate(result):
                if folder_name.upper() == "INBOX":
                    inbox_index = i
                    break

            if inbox_index is None:
                result.insert(0, "INBOX")
            elif inbox_index != 0:
                result.insert(0, result.pop(inbox_index))

            return result or ["INBOX"]
        except Exception as e:
            print(f"IMAP LIST Error: {e}")
            return ["INBOX"]
    
    def _decode_header_str(self, header_value):
        """Декодирование заголовка письма"""
        if not header_value:
            return "Unknown"
        try:
            decoded_list = decode_header(header_value)
            parts = []
            for content, encoding in decoded_list:
                if isinstance(content, bytes):
                    if encoding:
                        try:
                            parts.append(content.decode(encoding))
                        except:
                            parts.append(content.decode('utf-8', errors='ignore'))
                    else:
                        parts.append(content.decode('utf-8', errors='ignore'))
                elif isinstance(content, str):
                    parts.append(content)
            return "".join(parts)
        except Exception:
            return str(header_value)
    
    def get_messages(self, limit=20, folder="INBOX"):
        """Получение списка писем"""
        if not self.mail:
            return []
        try:
            status, selected_folder = self._select_folder(folder)
            if status != "OK":
                return []

            status, messages = self.mail.search(None, "ALL")
            if status != "OK":
                return []
            
            mail_ids = messages[0].split()
            latest_ids = mail_ids[-limit:] if len(mail_ids) > limit else mail_ids
            
            res = []
            for mid in reversed(latest_ids):
                try:
                    typ, data = self.mail.fetch(mid, "(RFC822.HEADER)")
                    for response_part in data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            
                            subject = self._decode_header_str(msg.get("Subject"))
                            sender = self._decode_header_str(msg.get("From"))
                            date_str = msg.get("Date")
                            
                            res.append({
                                "id": mid.decode(),
                                "from": {"address": sender},
                                "subject": subject,
                                "createdAt": date_str,
                                "folder": selected_folder,
                                "source": "imap"
                            })
                except Exception as e:
                    print(f"Error fetching msg {mid}: {e}")
            return res
        except Exception as e:
            print(f"IMAP Fetch Error: {e}")
            return []
    
    def get_message_content(self, msg_id, folder="INBOX"):
        """Получение содержимого письма"""
        if not self.mail:
            return "Not connected"
        try:
            status, _ = self._select_folder(folder)
            if status != "OK":
                return f"Error: cannot open folder {folder}"

            typ, data = self.mail.fetch(str(msg_id), "(RFC822)")
            
            raw_email = b""
            for part in data:
                if isinstance(part, tuple):
                    raw_email = part[1]
                    break
            
            if not raw_email:
                return "Error: Empty response from server."
            
            msg = email.message_from_bytes(raw_email)
            body = ""
            
            def decode_payload(payload):
                if isinstance(payload, str):
                    return payload
                if not isinstance(payload, bytes):
                    return str(payload)
                for enc in ['utf-8', 'latin-1', 'cp1252']:
                    try:
                        return payload.decode(enc)
                    except:
                        pass
                return payload.decode('utf-8', errors='ignore')
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if "attachment" not in content_disposition:
                        if content_type == "text/plain":
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = decode_payload(payload)
                                    break
                            except:
                                pass
                        elif content_type == "text/html" and not body:
                            try:
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = decode_payload(payload)
                            except:
                                pass
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = decode_payload(payload)
                except:
                    pass
            
            return body if body else "No text content found."
        except Exception as e:
            return f"Error reading body: {e}"
