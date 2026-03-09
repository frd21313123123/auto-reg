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
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIREMENTS_FILE = os.path.join(BASE_DIR, "requirements.txt")
PACKAGE_IMPORT_ALIASES = {
    "beautifulsoup4": "bs4",
}

WAVE_URL = "http://localhost:3000"


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
    candidates = []
    alias = PACKAGE_IMPORT_ALIASES.get(package_name.lower())
    if alias:
        candidates.append(alias)
    candidates.append(package_name)
    if "-" in package_name:
        candidates.append(package_name.replace("-", "_"))

    for candidate in dict.fromkeys(candidates):
        if importlib.util.find_spec(candidate) is not None:
            return True
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

    root = tk.Tk()
    app_instance = [None]  # mutable ref for MailApp

    def show_launcher():
        """Show the project selection screen."""
        from app.launcher import Launcher

        root.resizable(False, False)
        root.geometry("520x360")
        root.minsize(520, 360)

        # Centre on screen
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - 520) // 2
        y = (sh - 360) // 2
        root.geometry(f"520x360+{x}+{y}")

        launcher = Launcher(root, on_select=handle_select)
        app_instance[0] = launcher

    def handle_select(key):
        """Handle project card click."""
        if key == "autoreg":
            open_autoreg()
        elif key == "wave":
            webbrowser.open(WAVE_URL)

    def open_autoreg():
        """Switch from launcher to Auto-Reg app."""
        from app.mail_app import MailApp

        # Destroy launcher widgets
        if app_instance[0] is not None:
            app_instance[0].destroy()
            app_instance[0] = None

        root.resizable(True, True)
        root.geometry("1050x680")
        root.minsize(800, 500)

        # Centre on screen
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - 1050) // 2
        y = (sh - 680) // 2
        root.geometry(f"1050x680+{x}+{y}")

        mail_app = MailApp(root, on_back=show_launcher)
        app_instance[0] = mail_app

    show_launcher()
    root.mainloop()


if __name__ == "__main__":
    main()
