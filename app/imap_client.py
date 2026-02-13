# -*- coding: utf-8 -*-
"""
IMAP клиент для работы с почтой
"""

import imaplib
import email
from email.header import decode_header


class IMAPClient:
    """Клиент для работы с почтой через IMAP"""
    
    def __init__(self, host="imap.firstmail.ltd", timeout=8):
        self.host = host
        self.timeout = timeout
        self.mail = None
    
    def login(self, email_addr, password):
        """Авторизация на IMAP сервере"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.host, timeout=self.timeout)
            self.mail.login(email_addr, password)
            return True
        except Exception:
            return False
    
    def logout(self):
        """Выход из IMAP сессии"""
        try:
            if self.mail:
                self.mail.logout()
        except:
            pass
    
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
    
    def get_messages(self, limit=20):
        """Получение списка писем"""
        if not self.mail:
            return []
        try:
            self.mail.select("inbox")
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
                                "source": "imap"
                            })
                except Exception as e:
                    print(f"Error fetching msg {mid}: {e}")
            return res
        except Exception as e:
            print(f"IMAP Fetch Error: {e}")
            return []
    
    def get_message_content(self, msg_id):
        """Получение содержимого письма"""
        if not self.mail:
            return "Not connected"
        try:
            self.mail.select("inbox")
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
