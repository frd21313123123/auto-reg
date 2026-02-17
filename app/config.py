# -*- coding: utf-8 -*-
"""
Конфигурация приложения Mail.tm
"""

import os
import sys

# --- ПУТИ И URL ---
def _can_write_to_dir(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe_file = os.path.join(path, ".auto_reg_write_test")
        with open(probe_file, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe_file)
        return True
    except Exception:
        return False


def _resolve_base_dir():
    # Source run: keep repo root behavior.
    if not getattr(sys, "frozen", False):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # PyInstaller/exe run: __file__ points to a temp folder in onefile mode,
    # so persist data near executable (or LocalAppData fallback).
    exe_dir = os.path.dirname(sys.executable)
    if _can_write_to_dir(exe_dir):
        return exe_dir

    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        fallback_dir = os.path.join(local_appdata, "Auto-reg")
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

    return exe_dir


BASE_DIR = _resolve_base_dir()
API_URL = "https://api.mail.tm"
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
EXCEL_FILE = os.path.join(BASE_DIR, "accounts.xlsx")

# --- ЦВЕТА СТАТУСОВ ---
STATUS_COLORS = {
    "not_registered": {"dark": "#17243f"},
    "registered": {"dark": "#1d3d6d"},
    "plus": {"dark": "#1a5247"},
    "banned": {"dark": "#5b2530"},
    "invalid_password": {"dark": "#3d355c"},
}

# --- ШРИФТЫ ---
FONT_BASE = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_SECTION = ("Segoe UI", 9, "bold")
