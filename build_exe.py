# -*- coding: utf-8 -*-
"""
Build one-file Windows executable using PyInstaller.
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
    if not ensure_pyinstaller():
        print("[build] PyInstaller is not installed. Install it with:")
        print("        python -m pip install pyinstaller")
        return 1

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", name,
        os.path.join(BASE_DIR, "main.py"),
    ]
    print("[build] Running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
