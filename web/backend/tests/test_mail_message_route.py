import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _sqlite_url(path: Path) -> str:
    resolved = path.resolve().as_posix()
    if path.drive:
        return f"sqlite:///{resolved}"
    return f"sqlite:////{resolved}"


class MailMessageRouteTests(unittest.TestCase):
    def test_message_detail_route_accepts_uid_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "isolated.db"
            env = os.environ.copy()
            env["AUTO_REG_DATABASE_URL"] = _sqlite_url(db_path)

            script = textwrap.dedent(
                f"""
                import sys
                from pathlib import Path

                backend_dir = Path(r"{BACKEND_DIR}")
                if str(backend_dir) not in sys.path:
                    sys.path.insert(0, str(backend_dir))

                from fastapi.testclient import TestClient
                from app.main import app
                from app.routers.mail import mail_backend_service

                client = TestClient(app)
                register_response = client.post(
                    "/api/auth/register",
                    json={{"username": "uidroute", "password": "secret123"}},
                )
                print(register_response.status_code)

                login_response = client.post(
                    "/api/auth/login",
                    json={{"username": "uidroute", "password": "secret123"}},
                )
                print(login_response.status_code)
                token = login_response.json()["access_token"]
                headers = {{"Authorization": f"Bearer {{token}}"}}

                create_response = client.post(
                    "/api/accounts",
                    headers=headers,
                    json={{
                        "email": "uidroute@example.com",
                        "password_openai": "secret123",
                        "password_mail": "secret123",
                        "status": "not_registered",
                    }},
                )
                print(create_response.status_code)
                account_id = create_response.json()["id"]

                def fake_fetch_message(*args, **kwargs):
                    message_id = args[4]
                    if message_id != "uid:202":
                        raise AssertionError(message_id)
                    return {{
                        "id": "uid:202",
                        "sender": "test@example.com",
                        "subject": "Hello",
                        "text": "body",
                        "code": None,
                    }}

                mail_backend_service.fetch_message = fake_fetch_message

                detail_response = client.get(
                    f"/api/mail/accounts/{{account_id}}/messages/uid:202",
                    headers=headers,
                    params={{"sender": "test@example.com", "subject": "Hello"}},
                )
                print(detail_response.status_code)
                print(detail_response.text)
                """
            )

            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        stdout_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        self.assertGreaterEqual(len(stdout_lines), 5, msg=result.stdout)
        self.assertEqual(stdout_lines[0], "201", msg=result.stdout)
        self.assertEqual(stdout_lines[1], "200", msg=result.stdout)
        self.assertEqual(stdout_lines[2], "201", msg=result.stdout)
        self.assertEqual(stdout_lines[3], "200", msg=result.stdout)
        self.assertIn('"id":"uid:202"', stdout_lines[4], msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
