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


class AccountFolderRouteTests(unittest.TestCase):
    def test_folder_workflow_bulk_actions_and_delete_all(self):
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

                register_response = client.post(
                    "/api/auth/register",
                    json={{"username": "folderuser", "password": "secret123"}},
                )
                assert register_response.status_code == 201, register_response.text

                login_response = client.post(
                    "/api/auth/login",
                    json={{"username": "folderuser", "password": "secret123"}},
                )
                assert login_response.status_code == 200, login_response.text
                token = login_response.json()["access_token"]
                headers = {{"Authorization": f"Bearer {{token}}"}}

                folder_a = client.post(
                    "/api/accounts/folders",
                    headers=headers,
                    json={{"name": "Folder A"}},
                )
                assert folder_a.status_code == 201, folder_a.text

                folder_b = client.post(
                    "/api/accounts/folders",
                    headers=headers,
                    json={{"name": "Folder B"}},
                )
                assert folder_b.status_code == 201, folder_b.text

                folder_a_id = folder_a.json()["id"]
                folder_b_id = folder_b.json()["id"]

                create_alpha = client.post(
                    "/api/accounts",
                    headers=headers,
                    json={{
                        "email": "alpha@example.com",
                        "password_openai": "open-alpha",
                        "password_mail": "mail-alpha",
                        "status": "not_registered",
                        "folder_id": folder_a_id,
                    }},
                )
                assert create_alpha.status_code == 201, create_alpha.text

                create_beta = client.post(
                    "/api/accounts",
                    headers=headers,
                    json={{
                        "email": "beta@example.com",
                        "password_openai": "open-beta",
                        "password_mail": "mail-beta",
                        "status": "registered",
                    }},
                )
                assert create_beta.status_code == 201, create_beta.text

                accounts_response = client.get("/api/accounts", headers=headers)
                assert accounts_response.status_code == 200, accounts_response.text
                accounts = accounts_response.json()
                alpha = next(account for account in accounts if account["email"] == "alpha@example.com")
                beta = next(account for account in accounts if account["email"] == "beta@example.com")
                assert alpha["folder_id"] == folder_a_id, accounts
                assert alpha["folder_name"] == "Folder A", accounts
                assert beta["folder_id"] is None, accounts

                move_beta = client.post(
                    "/api/accounts/bulk-move",
                    headers=headers,
                    json={{
                        "account_ids": [beta["id"]],
                        "folder_id": folder_b_id,
                    }},
                )
                assert move_beta.status_code == 200, move_beta.text
                assert move_beta.json()["affected"] == 1, move_beta.text

                delete_folder_a = client.post(
                    "/api/accounts/delete-all",
                    headers=headers,
                    json={{
                        "scope": "folder",
                        "folder_id": folder_a_id,
                    }},
                )
                assert delete_folder_a.status_code == 200, delete_folder_a.text
                assert delete_folder_a.json()["affected"] == 1, delete_folder_a.text

                delete_beta = client.post(
                    "/api/accounts/bulk-delete",
                    headers=headers,
                    json={{"account_ids": [beta["id"]]}},
                )
                assert delete_beta.status_code == 200, delete_beta.text
                assert delete_beta.json()["affected"] == 1, delete_beta.text

                folders_response = client.get("/api/accounts/folders", headers=headers)
                assert folders_response.status_code == 200, folders_response.text
                folders = {{
                    folder["name"]: folder["account_count"]
                    for folder in folders_response.json()
                }}
                assert folders["Folder A"] == 0, folders
                assert folders["Folder B"] == 0, folders

                final_accounts = client.get("/api/accounts", headers=headers)
                assert final_accounts.status_code == 200, final_accounts.text
                assert final_accounts.json() == [], final_accounts.text
                print("folder-workflow-ok")
                """
            )

            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertIn("folder-workflow-ok", result.stdout)

    def test_existing_sqlite_schema_is_migrated_with_folder_column(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "legacy.db"
            env = os.environ.copy()
            env["AUTO_REG_DATABASE_URL"] = _sqlite_url(db_path)

            script = textwrap.dedent(
                f"""
                import sqlite3
                import sys
                from pathlib import Path

                db_path = Path(r"{db_path}")
                connection = sqlite3.connect(db_path)
                connection.executescript(
                    '''
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY,
                        username VARCHAR(64) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);
                    CREATE TABLE managed_accounts (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        password_openai VARCHAR(255) NOT NULL,
                        password_mail VARCHAR(255) NOT NULL,
                        status VARCHAR(32) NOT NULL DEFAULT 'not_registered',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_user_email ON managed_accounts (user_id, email);
                    '''
                )
                connection.commit()
                connection.close()

                backend_dir = Path(r"{BACKEND_DIR}")
                if str(backend_dir) not in sys.path:
                    sys.path.insert(0, str(backend_dir))

                from fastapi.testclient import TestClient
                from app.main import app

                client = TestClient(app)

                register_response = client.post(
                    "/api/auth/register",
                    json={{"username": "legacyuser", "password": "secret123"}},
                )
                assert register_response.status_code == 201, register_response.text

                login_response = client.post(
                    "/api/auth/login",
                    json={{"username": "legacyuser", "password": "secret123"}},
                )
                assert login_response.status_code == 200, login_response.text
                token = login_response.json()["access_token"]
                headers = {{"Authorization": f"Bearer {{token}}"}}

                folder_response = client.post(
                    "/api/accounts/folders",
                    headers=headers,
                    json={{"name": "Legacy Folder"}},
                )
                assert folder_response.status_code == 201, folder_response.text
                folder_id = folder_response.json()["id"]

                account_response = client.post(
                    "/api/accounts",
                    headers=headers,
                    json={{
                        "email": "legacy@example.com",
                        "password_openai": "secret123",
                        "password_mail": "secret123",
                        "status": "not_registered",
                        "folder_id": folder_id,
                    }},
                )
                assert account_response.status_code == 201, account_response.text
                assert account_response.json()["folder_id"] == folder_id, account_response.text

                connection = sqlite3.connect(db_path)
                columns = [row[1] for row in connection.execute("PRAGMA table_info(managed_accounts)")]
                tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                connection.close()

                assert "folder_id" in columns, columns
                assert "account_folders" in tables, tables
                print("legacy-migration-ok")
                """
            )

            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
        self.assertIn("legacy-migration-ok", result.stdout)


if __name__ == "__main__":
    unittest.main()
