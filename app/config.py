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
    "not_registered": {"light": "#f8fafc", "dark": "#0f172a"},
    "registered": {"light": "#d9e1f2", "dark": "#1e3a8a"},
    "plus": {"light": "#46bdc6", "dark": "#134e4a"}
}

# --- ШРИФТЫ ---
FONT_BASE = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")
