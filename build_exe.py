# -*- coding: utf-8 -*-
"""
Build one-file Windows executable using PyInstaller.
Creates a proper Windows app that pins to taskbar correctly.
"""

import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def ensure_pyinstaller():
    try:
        import PyInstaller  # noqa: F401
        return True
    except Exception:
        return False


def main():
    name = "Auto-reg"
    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    
    if not ensure_pyinstaller():
        print("[build] PyInstaller is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Build command with all necessary options for proper taskbar integration
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",  # No console window
        "--name", name,
        "--icon", icon_path,
        "--add-data", f"{os.path.join(BASE_DIR, 'assets')};assets",
        "--clean",
        os.path.join(BASE_DIR, "main.py"),
    ]
    
    print("[build] Running:", " ".join(cmd))
    result = subprocess.call(cmd)
    
    if result == 0:
        exe_path = os.path.join(BASE_DIR, "dist", f"{name}.exe")
        print(f"\n[build] SUCCESS! Executable created at:\n  {exe_path}")
        print("\nТеперь вы можете:")
        print("1. Запустить .exe файл из папки dist")
        print("2. Закрепить его в панели задач")
    
    return result


if __name__ == "__main__":
    raise SystemExit(main())
