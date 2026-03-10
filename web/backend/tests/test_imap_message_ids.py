import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.mail_backend import IMAPSimpleClient


class _FakeUidMailbox:
    def select(self, mailbox):
        return "OK", [b""]

    def uid(self, command, *args):
        if command == "search":
            return "OK", [b"101 202"]
        if command == "fetch" and args[0] == "202":
            return "OK", [(b"202", b"From: test@example.com\r\nSubject: Hello\r\nDate: Tue, 10 Mar 2026 12:00:00 +0000\r\n\r\n")]
        if command == "fetch" and args[0] == "101":
            return "OK", [(b"101", b"From: old@example.com\r\nSubject: World\r\nDate: Tue, 10 Mar 2026 11:00:00 +0000\r\n\r\n")]
        return "NO", []

    def fetch(self, *_args):
        raise AssertionError("sequence fetch should not be used when UID search is available")


class _FakeFallbackMailbox:
    def select(self, mailbox):
        return "OK", [b""]

    def uid(self, command, *args):
        if command == "fetch":
            return "NO", []
        return "NO", []

    def fetch(self, message_id, query):
        if str(message_id) != "42":
            return "NO", []
        raw_email = (
            b"From: test@example.com\r\n"
            b"Subject: Fallback\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"hello from sequence fetch"
        )
        return "OK", [(b"42", raw_email)]


class _FakeMultipartMailbox:
    def select(self, mailbox):
        return "OK", [b""]

    def uid(self, command, *args):
        if command == "fetch" and args[0] == "700":
            raw_email = (
                b"From: test@example.com\r\n"
                b"Subject: HTML mail\r\n"
                b"MIME-Version: 1.0\r\n"
                b"Content-Type: multipart/alternative; boundary=abc\r\n"
                b"\r\n"
                b"--abc\r\n"
                b"Content-Type: text/plain; charset=utf-8\r\n"
                b"\r\n"
                b"Plain text fallback with code 123456\r\n"
                b"--abc\r\n"
                b"Content-Type: text/html; charset=utf-8\r\n"
                b"\r\n"
                b"<html><body><h1>Hello</h1><p>HTML body</p></body></html>\r\n"
                b"--abc--\r\n"
            )
            return "OK", [(b"700", raw_email)]
        return "NO", []

    def fetch(self, *_args):
        return "NO", []


class IMAPMessageIdTests(unittest.TestCase):
    def test_get_messages_prefers_uid_ids(self):
        client = IMAPSimpleClient(host="example.com")
        client.mail = _FakeUidMailbox()

        messages = client.get_messages()

        self.assertEqual(messages[0]["id"], "uid:202")
        self.assertEqual(messages[1]["id"], "uid:101")
        self.assertEqual(messages[0]["subject"], "Hello")

    def test_get_message_content_falls_back_for_legacy_numeric_ids(self):
        client = IMAPSimpleClient(host="example.com")
        client.mail = _FakeFallbackMailbox()

        content = client.get_message_content("42")

        self.assertIn("hello from sequence fetch", content.text)
        self.assertIsNone(content.html)

    def test_get_message_content_returns_html_and_plain_text(self):
        client = IMAPSimpleClient(host="example.com")
        client.mail = _FakeMultipartMailbox()

        content = client.get_message_content("uid:700")

        self.assertIn("Plain text fallback", content.text)
        self.assertEqual(content.html, "<html><body><h1>Hello</h1><p>HTML body</p></body></html>")


if __name__ == "__main__":
    unittest.main()
