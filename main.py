# -*- coding: utf-8 -*-
"""
Mail.tm registration and inbox client.
App entry point.
"""

import importlib.util
import os
import re
import subprocess
import sys
import tkinter as tk
import ctypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")


def set_app_id():
    """Register AppUserModelID so the app pins to taskbar like a normal program."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("AutoReg.MailTM")
    except Exception:
        pass


# Set AppUserModelID as early as possible, before any windows are created
set_app_id()


def _normalize_requirement(line):
    line = line.split("#", 1)[0].strip()
    if not line:
        return None
    line = line.split(";", 1)[0].strip()
    name = re.split(r"[\\[=<>!~ ]", line, maxsplit=1)[0].strip()
    return name or None


def _is_installed(package_name):
    if importlib.util.find_spec(package_name) is not None:
        return True
    if "-" in package_name:
        alt = package_name.replace("-", "_")
        return importlib.util.find_spec(alt) is not None
    return False


def ensure_dependencies():
    if getattr(sys, "frozen", False):
        return
    if not os.path.exists(REQUIREMENTS_FILE):
        return

    missing = []
    with open(REQUIREMENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            name = _normalize_requirement(line)
            if name and not _is_installed(name):
                missing.append(name)

    if not missing:
        return

    print(f"[deps] Missing: {', '.join(sorted(set(missing)))}. Installing...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE])
    except Exception as exc:
        print(f"[deps] Install failed: {exc}")


def main():
    """App entry point."""
    ensure_dependencies()
    from app.mail_app import MailApp

    root = tk.Tk()
    app = MailApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
