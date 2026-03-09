import unittest

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

        self.assertIn("hello from sequence fetch", content)


if __name__ == "__main__":
    unittest.main()
