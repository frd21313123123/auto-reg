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

from app.core.config import Settings


def _sqlite_url(path: Path) -> str:
    resolved = path.resolve().as_posix()
    if path.drive:
        return f"sqlite:///{resolved}"
    return f"sqlite:////{resolved}"


class BackendConfigTests(unittest.TestCase):
    def test_default_database_url_is_absolute_and_cwd_independent(self):
        expected = _sqlite_url(BACKEND_DIR / "web_app.db")

        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                settings = Settings()
            finally:
                os.chdir(original_cwd)

        self.assertEqual(settings.database_url, expected)

    def test_first_request_initializes_database_without_startup_context(self):
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

                client = TestClient(app)
                response = client.post(
                    "/api/auth/register",
                    json={{"username": "lazyinit", "password": "secret123"}},
                )
                print(response.status_code)
                print(response.text)
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
        self.assertGreaterEqual(len(stdout_lines), 2, msg=result.stdout)
        self.assertEqual(stdout_lines[0], "201", msg=result.stdout)
        self.assertIn('"username":"lazyinit"', stdout_lines[1], msg=result.stdout)


if __name__ == "__main__":
    unittest.main()
