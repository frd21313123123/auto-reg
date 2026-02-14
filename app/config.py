# -*- coding: utf-8 -*-
"""
Конфигурация приложения Mail.tm
"""

import os

# --- ПУТИ И URL ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://api.mail.tm"
ACCOUNTS_FILE = os.path.join(BASE_DIR, "accounts.txt")
EXCEL_FILE = os.path.join(BASE_DIR, "accounts.xlsx")

# --- ЦВЕТА СТАТУСОВ ---
STATUS_COLORS = {
    "not_registered": {"light": "#f7f8fa", "dark": "#1a202c"},
    "registered": {"light": "#dbeafe", "dark": "#1e3a5f"},
    "plus": {"light": "#c6f6d5", "dark": "#1c4532"},
    "banned": {"light": "#fed7d7", "dark": "#742a2a"},
    "invalid_password": {"light": "#e9d5ff", "dark": "#44337a"}
}

# --- ШРИФТЫ ---
FONT_BASE = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 13, "bold")
FONT_SECTION = ("Segoe UI", 9, "bold")
