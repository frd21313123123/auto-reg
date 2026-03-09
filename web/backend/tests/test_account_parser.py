import unittest
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.account_parser import parse_account_line


class ParseAccountLineTests(unittest.TestCase):
    def test_parse_single_password_with_status(self):
        account = parse_account_line(
            "henryjames1943@ttabcheney.com / jmyqqztqY!6014 / not_registered"
        )

        self.assertIsNotNone(account)
        self.assertEqual(account.email, "henryjames1943@ttabcheney.com")
        self.assertEqual(account.password_openai, "jmyqqztqY!6014")
        self.assertEqual(account.password_mail, "jmyqqztqY!6014")
        self.assertEqual(account.status, "not_registered")

    def test_parse_split_passwords_with_status(self):
        account = parse_account_line(
            "loisrangel1942@tukiunge.com / CR2tXdVKw7BjA;jnhmflqwS!8047 / not_registered"
        )

        self.assertIsNotNone(account)
        self.assertEqual(account.password_openai, "CR2tXdVKw7BjA")
        self.assertEqual(account.password_mail, "jnhmflqwS!8047")
        self.assertEqual(account.status, "not_registered")

    def test_parse_legacy_colon_format(self):
        account = parse_account_line("john@example.com:open123;mail456")

        self.assertIsNotNone(account)
        self.assertEqual(account.email, "john@example.com")
        self.assertEqual(account.password_openai, "open123")
        self.assertEqual(account.password_mail, "mail456")


if __name__ == "__main__":
    unittest.main()
