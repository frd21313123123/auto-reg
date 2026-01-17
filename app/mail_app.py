# -*- coding: utf-8 -*-
"""
Основной класс приложения Mail.tm
"""

import tkinter as tk
from tkinter import ttk, messagebox
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import string
import os
import sys
import pyperclip
import threading
import re
import time
import platform
import winsound
import ctypes
from datetime import datetime, timedelta
from faker import Faker
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill

from .config import (
    API_URL, ACCOUNTS_FILE, EXCEL_FILE,
    STATUS_COLORS, FONT_BASE, FONT_SMALL, FONT_BOLD, FONT_TITLE
)
from .themes import THEMES
from .widgets import ThemedCheckbox
from .imap_client import IMAPClient
from .sk_generator import show_sk_window
from .minesweeper import show_minesweeper
from .hotkey_settings import HotkeySettings, show_settings_window


class MailApp:
    """Основной класс приложения Mail.tm"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Mail.tm — регистрация и почтовый клиент")
        self.root.geometry("1000x650")
        
        # Устанавливаем иконку окна
        try:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        # Переменные состояния
        self.accounts_data = []
        self.last_message_ids = set()
        self.refresh_interval_ms = 5000
        
        self.current_token = None
        self.account_type = "api"  # "api" or "imap"
        self.imap_client = None
        self.mail_tm_domains = []
        
        # Сохраняем учетные данные для переподключения при смене VPN
        self.current_email = None
        self.current_password = None
        
        # HTTP сессия с настройками повторного подключения
        self.http_session = self._create_http_session()
        
        self.is_refreshing = False
        self.auto_refresh_job = None
        self.stop_threads = False
        self.params = {"theme": "light"}
        self.is_pinned = False  # State for "Always on Top"
        
        # Загружаем домены mail.tm в фоне
        threading.Thread(target=self.load_mail_tm_domains, daemon=True).start()
        
        # Основной контейнер
        self.root_container = tk.Frame(root, bg="#f0f0f0")
        self.root_container.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        self.status_bar = tk.Label(self.root_container, textvariable=self.status_var, bd=1, relief=tk.FLAT, anchor=tk.W, font=FONT_SMALL)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Стили
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        available_themes = style.theme_names()
        default_design = "default" if "default" in available_themes else style.theme_use()
        try:
            style.theme_use(default_design)
        except Exception:
            default_design = style.theme_use()
        self.design_var = tk.StringVar(value=default_design)
        
        # --- Сплиттер (PanedWindow) ---
        self.paned = tk.PanedWindow(self.root_container, orient=tk.HORIZONTAL, sashwidth=4, bg="#dcdcdc")
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # --- ЛЕВАЯ ПАНЕЛЬ (аккаунты) ---
        self.left_panel = tk.Frame(self.paned, width=260, bg="#f0f0f0")
        self.paned.add(self.left_panel, minsize=200)
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(4, weight=1)
        
        # Заголовок левой панели (тема)
        self.left_header = tk.Frame(self.left_panel, bg="#f0f0f0")
        self.left_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        # Тема (светлая/темная)
        self.lbl_theme = tk.Label(self.left_header, text="Тема", bg="#f0f0f0", font=FONT_SMALL)
        self.lbl_theme.pack(side=tk.LEFT)
        self.theme_toggle = ThemedCheckbox(self.left_header, on_toggle=self.on_theme_toggle_click, size=28, checked=False)
        self.theme_toggle.pack(side=tk.LEFT, padx=(2, 10))
        
        # Кнопка создания
        self.btn_create = tk.Button(self.left_panel, text="Создать аккаунт", bg="#2563eb", fg="white", font=FONT_BOLD, command=self.start_create_account)
        self.btn_create.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        # Список аккаунтов
        self.lbl_saved = tk.Label(self.left_panel, text="Сохраненные аккаунты", bg="#f0f0f0", font=FONT_BOLD)
        self.lbl_saved.grid(row=2, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        # Панель кнопок файла
        self.file_btn_frame = tk.Frame(self.left_panel, bg="#f0f0f0")
        self.file_btn_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 5))
        
        # Кнопка обновления списка
        self.btn_reload = tk.Button(self.file_btn_frame, text="Обновить", font=FONT_SMALL, command=self.load_accounts_from_file)
        self.btn_reload.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        # Кнопка открытия файла
        self.btn_open_file = tk.Button(self.file_btn_frame, text="Файл", font=FONT_SMALL, command=self.open_accounts_file)
        self.btn_open_file.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Кнопка открытия Excel файла
        self.btn_open_excel = tk.Button(self.file_btn_frame, text="Excel", font=FONT_SMALL, command=self.open_excel_file)
        self.btn_open_excel.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Кнопка проверки бана OpenAI
        self.btn_check_ban = tk.Button(self.file_btn_frame, text="🚫 Бан", font=FONT_SMALL, command=self.start_ban_check, bg="#ef4444", fg="white")
        self.btn_check_ban.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))
        
        # Кнопки управления аккаунтом
        self.btn_frame = tk.Frame(self.left_panel, bg="#f0f0f0")
        self.btn_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=10)
        
        self.btn_copy_email = tk.Button(self.btn_frame, text="Email", command=self.copy_email, font=FONT_SMALL)
        self.btn_copy_email.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.btn_copy_pass = tk.Button(self.btn_frame, text="Пароль", command=self.copy_pass, font=FONT_SMALL)
        self.btn_copy_pass.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # Кнопка для генерации SK данных
        self.btn_sk = tk.Button(self.btn_frame, text="SK Info", command=self._show_sk_window, font=FONT_SMALL)
        self.btn_sk.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # Кнопка для игры в Сапер
        self.btn_minesweeper = tk.Button(self.btn_frame, text="💣", command=self._show_minesweeper, font=("Segoe UI", 12), width=3)
        self.btn_minesweeper.pack(side=tk.LEFT, padx=2)
        
        # Кнопка настроек горячих клавиш
        self.btn_hotkey_settings = tk.Button(self.btn_frame, text="⚙", command=self._show_hotkey_settings, font=("Segoe UI", 12), width=3)
        self.btn_hotkey_settings.pack(side=tk.LEFT, padx=2)
        
        # Список аккаунтов
        self.acc_listbox = tk.Listbox(self.left_panel, height=20, exportselection=False)
        self.acc_listbox.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        self.acc_listbox.bind('<<ListboxSelect>>', self.on_account_select)
        
        # Контекстное меню для аккаунтов
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="Статус: Не зарегистрирован", command=lambda: self.set_account_status("not_registered"))
        self.context_menu.add_command(label="Статус: Зарегистрирован", command=lambda: self.set_account_status("registered"))
        self.context_menu.add_command(label="Статус: Plus", command=lambda: self.set_account_status("plus"))
        self.context_menu.add_command(label="Статус: Banned 🚫", command=lambda: self.set_account_status("banned"))
        
        self.acc_listbox.bind("<Button-3>", self.show_context_menu)
        
        # Загружаем сохраненные аккаунты сразу
        self.load_accounts_from_file()
        
        # --- ПАНЕЛЬ СЛУЧАЙНЫХ ДАННЫХ ---
        self.person_frame = tk.LabelFrame(self.left_panel, text="👤 Случайные данные", font=FONT_BOLD, bg="#f0f0f0")
        self.person_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(5, 10))
        
        # Инициализация Faker (английский)
        self.fake = Faker("en_US")
        
        # Переменные для случайных данных
        self.random_name_var = tk.StringVar()
        self.random_birthdate_var = tk.StringVar()
        
        # Имя
        name_row = tk.Frame(self.person_frame, bg="#f0f0f0")
        name_row.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(name_row, text="Name:", font=FONT_SMALL, bg="#f0f0f0", width=8, anchor="w").pack(side=tk.LEFT)
        self.entry_random_name = tk.Entry(name_row, textvariable=self.random_name_var, font=FONT_SMALL, state="readonly", width=18)
        self.entry_random_name.pack(side=tk.LEFT, padx=2)
        self.btn_copy_random_name = tk.Button(name_row, text="📋", command=self.copy_random_name, font=FONT_SMALL, width=2)
        self.btn_copy_random_name.pack(side=tk.LEFT, padx=2)
        
        # Дата рождения
        bdate_row = tk.Frame(self.person_frame, bg="#f0f0f0")
        bdate_row.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(bdate_row, text="Дата:", font=FONT_SMALL, bg="#f0f0f0", width=8, anchor="w").pack(side=tk.LEFT)
        self.entry_random_bdate = tk.Entry(bdate_row, textvariable=self.random_birthdate_var, font=FONT_SMALL, state="readonly", width=18)
        self.entry_random_bdate.pack(side=tk.LEFT, padx=2)
        self.btn_copy_random_bdate = tk.Button(bdate_row, text="📋", command=self.copy_random_birthdate, font=FONT_SMALL, width=2)
        self.btn_copy_random_bdate.pack(side=tk.LEFT, padx=2)
        
        # Кнопка генерации
        self.btn_generate_person = tk.Button(self.person_frame, text="🔄 Новые данные", command=self.generate_random_person, font=FONT_SMALL)
        self.btn_generate_person.pack(fill=tk.X, padx=5, pady=5)
        
        # Генерируем случайные данные при старте
        self.generate_random_person()
        
        # --- ПРАВАЯ ПАНЕЛЬ (ПИСЬМА) ---
        self.right_panel = tk.Frame(self.paned)
        self.paned.add(self.right_panel, minsize=400)
        
        # Заголовок текущей почты
        self.header_frame = tk.Frame(self.right_panel, bg="#ddd")
        self.header_frame.pack(fill=tk.X)
        
        self.lbl_current_email = tk.Label(self.header_frame, text="Выберите аккаунт слева", font=FONT_TITLE, bg="#ddd", pady=10)
        self.lbl_current_email.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        self.btn_refresh = tk.Button(self.header_frame, text="Обновить", command=self.on_manual_refresh, bg="#2196F3", fg="white", font=FONT_SMALL)
        self.btn_refresh.pack(side=tk.RIGHT, padx=10)
        
        # Кнопки статуса
        self.status_frame = tk.Frame(self.header_frame, bg="#ddd")
        self.status_frame.pack(side=tk.RIGHT, padx=5)
        
        self.btn_nr = tk.Button(self.status_frame, text="Не рег", bg="white", font=FONT_SMALL, command=lambda: self.set_account_status("not_registered"))
        self.btn_nr.pack(side=tk.LEFT, padx=2)
        
        self.btn_reg = tk.Button(self.status_frame, text="Рег", bg="#d9e1f2", font=FONT_SMALL, command=lambda: self.set_account_status("registered"))
        self.btn_reg.pack(side=tk.LEFT, padx=2)
        
        self.btn_plus = tk.Button(self.status_frame, text="Plus", bg="#46bdc6", font=FONT_SMALL, command=lambda: self.set_account_status("plus"))
        self.btn_plus.pack(side=tk.LEFT, padx=2)
        
        # Список писем (Treeview)
        columns = ("sender", "subject", "date", "msg_id")
        self.tree = ttk.Treeview(self.right_panel, columns=columns, displaycolumns=("sender", "subject", "date"), show="headings", height=8)
        self.tree.heading("sender", text="От кого")
        self.tree.heading("subject", text="Тема")
        self.tree.heading("date", text="Время")
        self.tree.column("sender", width=150)
        self.tree.column("subject", width=300)
        self.tree.column("date", width=110, anchor="center")
        self.tree.column("msg_id", width=0, stretch=False)
        self.tree.pack(fill=tk.X, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_message_select)
        
        # Область просмотра письма
        self.lbl_msg_title = tk.Label(self.right_panel, text="Содержание письма:", anchor="w", font=FONT_BOLD)
        self.lbl_msg_title.pack(fill=tk.X, padx=10)
        
        # Кнопка копирования кода
        self.btn_copy_code = tk.Button(self.right_panel, text="Копировать код", bg="#FF9800", fg="white", font=FONT_BOLD)
        self.btn_copy_code.pack(fill=tk.X, padx=10, pady=5)
        self.btn_copy_code.pack_forget()
        
        self.msg_text = tk.Text(self.right_panel, wrap=tk.WORD, height=15, font=FONT_BASE)
        self.msg_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.msg_text.insert(tk.END, "Выберите письмо слева, чтобы увидеть содержимое.")
        
        print(f"[*] Используемый файл аккаунтов: {ACCOUNTS_FILE}")
        
        # Current theme
        self.set_theme("light")
        
        # Запуск цикла автообновления
        self.start_auto_refresh()
        
        # Регистрация горячих клавиш
        self._setup_hotkeys()
    
    def _create_http_session(self):
        """Создание HTTP сессии с настройками переподключения для устойчивости к смене VPN."""
        session = requests.Session()
        
        # Настройка повторных попыток при ошибках соединения
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,  # Минимальный пул для быстрого переподключения
            pool_maxsize=1,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _reset_http_session(self):
        """Сбросить HTTP сессию (полезно при смене VPN)."""
        try:
            if self.http_session:
                self.http_session.close()
        except Exception:
            pass
        self.http_session = self._create_http_session()
    
    def _make_request(self, method, url, retry_auth=True, **kwargs):
        """
        Выполнить HTTP запрос с обработкой ошибок сети и переподключением.
        
        Args:
            method: HTTP метод ('get', 'post')
            url: URL для запроса
            retry_auth: Если True, попытаться переавторизоваться при ошибке
            **kwargs: Дополнительные параметры для requests
            
        Returns:
            Response объект или None при ошибке
        """
        try:
            response = getattr(self.http_session, method)(url, timeout=10, **kwargs)
            return response
        except (requests.exceptions.ConnectionError, 
                requests.exceptions.Timeout,
                requests.exceptions.ChunkedEncodingError,
                OSError) as e:
            print(f"[Network] Connection error: {e}")
            
            # Сбрасываем сессию и пробуем снова
            self._reset_http_session()
            
            try:
                response = getattr(self.http_session, method)(url, timeout=10, **kwargs)
                return response
            except Exception as e2:
                print(f"[Network] Retry failed: {e2}")
                
                # Если есть сохранённые учётные данные и нужна переавторизация
                if retry_auth and self.current_email and self.current_password:
                    print("[Network] Attempting re-authentication...")
                    self._try_reauth()
                
                return None
        except Exception as e:
            print(f"[Network] Unexpected error: {e}")
            return None
    
    def _try_reauth(self):
        """Попытка переавторизации при потере соединения."""
        if not self.current_email or not self.current_password:
            return False
        
        try:
            # Сбрасываем текущее состояние
            self.current_token = None
            if self.imap_client:
                try:
                    self.imap_client.logout()
                except Exception:
                    pass
                self.imap_client = None
            
            # Запускаем переавторизацию в отдельном потоке
            self.root.after(0, lambda: self.update_status("Переподключение после смены сети..."))
            threading.Thread(
                target=self.login_thread, 
                args=(self.current_email, self.current_password), 
                daemon=True
            ).start()
            return True
        except Exception as e:
            print(f"[Reauth] Failed: {e}")
            return False
    
    def _setup_hotkeys(self):
        """Настройка глобальных горячих клавиш."""
        self.hotkey_settings = HotkeySettings.get_instance()
        self.hotkey_settings.set_callback("email", self.copy_email)
        self.hotkey_settings.set_callback("password", self.copy_pass)
        self.hotkey_settings.set_callback("paste_account", self.paste_accounts_from_clipboard)
        self.hotkey_settings.set_callback("copy_account", self.copy_full_account)
        self.hotkey_settings.set_callback("random_name", self.copy_random_name)
        self.hotkey_settings.set_callback("random_birthdate", self.copy_random_birthdate)
        self.hotkey_settings.register_all()
    
    def paste_accounts_from_clipboard(self):
        """Вставить аккаунты из буфера обмена."""
        try:
            clipboard_text = pyperclip.paste()
            if not clipboard_text:
                self.update_status("Буфер обмена пуст")
                return
            
            lines = clipboard_text.strip().split('\n')
            added_count = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                email = ""
                password = ""
                
                # Parse different formats
                if " / " in line:
                    parts = line.split(" / ", 1)
                    email = parts[0].strip()
                    password = parts[1].strip() if len(parts) > 1 else ""
                elif ":" in line:
                    parts = line.split(":", 1)
                    email = parts[0].strip()
                    password = parts[1].strip() if len(parts) > 1 else ""
                elif "\t" in line:
                    parts = line.split("\t", 1)
                    email = parts[0].strip()
                    password = parts[1].strip() if len(parts) > 1 else ""
                
                if email and password and "@" in email:
                    # Check if already exists
                    exists = any(acc["email"] == email for acc in self.accounts_data)
                    if not exists:
                        self.accounts_data.append({
                            "email": email,
                            "password": password,
                            "status": "not_registered"
                        })
                        display_text = f"{email} / {password}"
                        self.acc_listbox.insert(tk.END, display_text)
                        added_count += 1
            
            if added_count > 0:
                self.update_listbox_colors()
                self.save_accounts_to_file()
                self.update_status(f"Добавлено аккаунтов: {added_count}")
            else:
                self.update_status("Не найдено валидных аккаунтов для добавления")
                
        except Exception as e:
            self.update_status(f"Ошибка вставки: {e}")
    
    def copy_full_account(self):
        """Копировать полный аккаунт (email / password)."""
        selection = self.acc_listbox.curselection()
        if not selection:
            self.update_status("Выберите аккаунт для копирования")
            return
        
        idx = selection[0]
        if idx < len(self.accounts_data):
            acc = self.accounts_data[idx]
            full_text = f"{acc['email']} / {acc['password']}"
            pyperclip.copy(full_text)
            self.update_status(f"Скопировано: {acc['email']} / ***")
    
    def _show_hotkey_settings(self):
        """Открыть окно настроек горячих клавиш."""
        def on_save(new_hotkeys):
            self.hotkey_settings.register_all()
        
        theme_name = self.params.get("theme", "light")
        show_settings_window(self.root, theme_name, on_save=on_save)
    
    def generate_random_person(self):
        """Генерация случайных данных о человеке."""
        # Генерируем имя (только имя, без фамилии)
        name = self.fake.first_name()
        self.random_name_var.set(name)
        
        # Генерируем дату рождения (с 1975 по 2004 год)
        start_date = datetime(1975, 1, 1)
        end_date = datetime(2004, 12, 31)
        days_between = (end_date - start_date).days
        random_days = random.randint(0, days_between)
        birthdate = start_date + timedelta(days=random_days)
        self.random_birthdate_var.set(birthdate.strftime("%d.%m.%Y"))
        
        self.update_status(f"Сгенерировано: {name}")
    
    def copy_random_name(self):
        """Копировать случайное имя."""
        name = self.random_name_var.get()
        if name:
            pyperclip.copy(name)
            self.update_status(f"Скопировано имя: {name[:20]}...")
    
    def copy_random_birthdate(self):
        """Копировать случайную дату рождения."""
        bdate = self.random_birthdate_var.get()
        if bdate:
            pyperclip.copy(bdate)
            self.update_status(f"Скопирована дата: {bdate}")
    
    def copy_email(self):
        """Копировать email выбранного аккаунта."""
        selection = self.acc_listbox.curselection()
        if not selection:
            self.update_status("Выберите аккаунт для копирования")
            return
        
        idx = selection[0]
        if idx < len(self.accounts_data):
            acc = self.accounts_data[idx]
            pyperclip.copy(acc['email'])
            self.update_status(f"Скопирован email: {acc['email']}")
    
    def copy_pass(self):
        """Копировать пароль выбранного аккаунта."""
        selection = self.acc_listbox.curselection()
        if not selection:
            self.update_status("Выберите аккаунт для копирования")
            return
        
        idx = selection[0]
        if idx < len(self.accounts_data):
            acc = self.accounts_data[idx]
            pyperclip.copy(acc['password'])
            self.update_status(f"Скопирован пароль для: {acc['email']}")
    
    def toggle_pin(self):
        """Переключение режима 'Поверх всех окон'"""
        self.is_pinned = not self.is_pinned
        self.root.wm_attributes("-topmost", self.is_pinned)

    def load_mail_tm_domains(self):
        """Загрузка доменов mail.tm"""
        try:
            res = self._make_request('get', f"{API_URL}/domains", retry_auth=False)
            if res and res.status_code == 200:
                data = res.json()['hydra:member']
                self.mail_tm_domains = [d['domain'] for d in data]
                print(f"[*] Loaded {len(self.mail_tm_domains)} mail.tm domains")
        except:
            pass
    
    def _show_sk_window(self):
        """Открывает окно генератора данных Южной Кореи"""
        theme_name = self.params.get("theme", "light")
        show_sk_window(self.root, theme_name)
    
    def _show_minesweeper(self):
        """Открывает окно игры Сапер"""
        theme_name = self.params.get("theme", "light")
        show_minesweeper(self.root, theme_name)
    
    def play_notification_sound(self, count=1):
        """Проигрывает звук при появлении новых писем"""
        def _beep():
            for _ in range(max(1, count)):
                try:
                    if platform.system() == "Windows":
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    else:
                        print("\a", end="", flush=True)
                except Exception:
                    pass
                time.sleep(0.1)
        
        threading.Thread(target=_beep, daemon=True).start()
    
    def update_status(self, text):
        """Безопасное обновление статуса из другого потока"""
        self.root.after(0, lambda: self.status_var.set(text))
    
    def open_accounts_file(self):
        """Открывает файл аккаунтов в системном редакторе"""
        try:
            if not os.path.exists(ACCOUNTS_FILE):
                with open(ACCOUNTS_FILE, "w") as f:
                    pass
            os.startfile(ACCOUNTS_FILE)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл:\n{e}")
    
    def open_excel_file(self):
        """Открывает Excel файл аккаунтов"""
        try:
            if not os.path.exists(EXCEL_FILE):
                self.save_accounts_to_excel()
            os.startfile(EXCEL_FILE)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть Excel файл:\n{e}")
    
    def start_ban_check(self):
        """Запуск проверки всех аккаунтов на бан OpenAI"""
        if not self.accounts_data:
            messagebox.showwarning("Внимание", "Нет аккаунтов для проверки")
            return
        
        # Подтверждение
        total = len(self.accounts_data)
        if not messagebox.askyesno("Проверка бана", 
            f"Проверить {total} аккаунтов на бан OpenAI?\n\n"
            "Это может занять некоторое время.\n"
            "Аккаунты с письмом 'Access Deactivated' будут помечены как забаненные."):
            return
        
        self.btn_check_ban.config(state=tk.DISABLED, text="⏳ Проверка...")
        
        # Создаём окно прогресса
        self._create_progress_window(total)
        
        threading.Thread(target=self.ban_check_thread, daemon=True).start()
    
    def _create_progress_window(self, total):
        """Создание окна с прогресс баром"""
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("Проверка на бан OpenAI")
        self.progress_window.geometry("450x180")
        self.progress_window.resizable(False, False)
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()
        
        # Центрируем окно
        self.progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 450) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 180) // 2
        self.progress_window.geometry(f"+{x}+{y}")
        
        # Применяем тему
        theme = self.params.get("theme", "light")
        colors = THEMES[theme]
        self.progress_window.config(bg=colors["bg"])
        
        # Заголовок
        self.progress_title = tk.Label(
            self.progress_window, 
            text="🔍 Проверка аккаунтов на бан...", 
            font=FONT_BOLD,
            bg=colors["bg"],
            fg=colors["fg"]
        )
        self.progress_title.pack(pady=(15, 5))
        
        # Текущий аккаунт
        self.progress_label = tk.Label(
            self.progress_window,
            text=f"Подготовка... 0/{total}",
            font=FONT_SMALL,
            bg=colors["bg"],
            fg=colors["fg"]
        )
        self.progress_label.pack(pady=5)
        
        # Прогресс бар
        style = ttk.Style()
        style.configure("ban.Horizontal.TProgressbar", 
                       troughcolor=colors.get("list_bg", "#e5e7eb"),
                       background="#ef4444")
        
        self.progress_bar = ttk.Progressbar(
            self.progress_window,
            orient="horizontal",
            length=380,
            mode="determinate",
            maximum=total,
            style="ban.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(pady=10)
        
        # Статистика
        self.progress_stats = tk.Label(
            self.progress_window,
            text="Забанено: 0 | Проверено: 0",
            font=FONT_SMALL,
            bg=colors["bg"],
            fg=colors["fg"]
        )
        self.progress_stats.pack(pady=5)
        
        # Кнопка отмены
        self.ban_check_cancelled = False
        self.btn_cancel_ban = tk.Button(
            self.progress_window,
            text="Отмена",
            command=self._cancel_ban_check,
            font=FONT_SMALL,
            bg="#6b7280",
            fg="white"
        )
        self.btn_cancel_ban.pack(pady=10)
        
        # Обработка закрытия окна
        self.progress_window.protocol("WM_DELETE_WINDOW", self._cancel_ban_check)
    
    def _cancel_ban_check(self):
        """Отмена проверки бана"""
        self.ban_check_cancelled = True
        self.progress_label.config(text="Отмена...")
    
    def _update_progress(self, current, total, email, banned_count, checked_count):
        """Обновление прогресс бара"""
        if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
            self.progress_bar["value"] = current
            self.progress_label.config(text=f"Проверка: {email[:35]}... ({current}/{total})")
            self.progress_stats.config(text=f"Забанено: {banned_count} | Проверено: {checked_count}")
    
    def ban_check_thread(self):
        """Поток проверки всех аккаунтов на бан"""
        banned_count = 0
        checked_count = 0
        total = len(self.accounts_data)
        
        for idx, account in enumerate(self.accounts_data):
            # Проверяем отмену
            if hasattr(self, 'ban_check_cancelled') and self.ban_check_cancelled:
                break
            
            email = account.get("email", "")
            password = account.get("password", "")
            
            if not email or not password:
                continue
            
            # Пропускаем уже забаненные
            if account.get("status") == "banned":
                checked_count += 1
                self.root.after(0, lambda i=idx, e=email, b=banned_count, c=checked_count: 
                    self._update_progress(i+1, total, e, b, c))
                continue
            
            # Обновляем прогресс
            self.root.after(0, lambda i=idx, e=email, b=banned_count, c=checked_count: 
                self._update_progress(i+1, total, e, b, c))
            
            try:
                is_banned = self._check_account_for_ban(email, password)
                
                if is_banned:
                    # Помечаем как забаненный
                    self.accounts_data[idx]["status"] = "banned"
                    banned_count += 1
                    print(f"[BAN] Account banned: {email}")
                
            except Exception as e:
                print(f"[BAN] Error checking {email}: {e}")
            
            checked_count += 1
            
            # Небольшая пауза между запросами
            time.sleep(0.3)
        
        # Обновляем UI
        self.root.after(0, lambda: self._on_ban_check_complete(checked_count, banned_count))
    
    def _check_account_for_ban(self, email_addr, password):
        """Проверка одного аккаунта на бан OpenAI"""
        domain = email_addr.split("@")[-1]
        is_mail_tm = domain in self.mail_tm_domains or domain.endswith("mail.tm")
        
        # Проверяем через API mail.tm
        if is_mail_tm:
            try:
                # Получаем токен
                payload = {"address": email_addr, "password": password}
                res = self._make_request('post', f"{API_URL}/token", retry_auth=False, json=payload)
                
                if not res or res.status_code != 200:
                    return False
                
                token = res.json().get('token')
                if not token:
                    return False
                
                # Получаем список писем
                headers = {"Authorization": f"Bearer {token}"}
                res = self._make_request('get', f"{API_URL}/messages", retry_auth=False, headers=headers)
                
                if not res or res.status_code != 200:
                    return False
                
                messages = res.json().get('hydra:member', [])
                
                # Проверяем каждое письмо на признаки бана
                for msg in messages:
                    sender = msg.get('from', {}).get('address', '').lower()
                    subject = msg.get('subject', '').lower()
                    
                    # Проверяем отправителя и тему
                    if 'openai' in sender or 'noreply@tm.openai.com' in sender:
                        if 'access deactivated' in subject or 'deactivated' in subject:
                            return True
                    
                    # Альтернативные проверки
                    if 'access deactivated' in subject and 'openai' in sender:
                        return True
                
                return False
                
            except Exception as e:
                print(f"[BAN] API check error for {email_addr}: {e}")
                return False
        else:
            # Для не-mail.tm аккаунтов пробуем IMAP
            try:
                imap_client = IMAPClient(host=f"imap.{domain}")
                if not imap_client.login(email_addr, password):
                    # Пробуем стандартный хост
                    imap_client = IMAPClient(host="imap.firstmail.ltd")
                    if not imap_client.login(email_addr, password):
                        return False
                
                messages = imap_client.get_messages(limit=50)
                imap_client.logout()
                
                for msg in messages:
                    sender = msg.get('from', {}).get('address', '').lower()
                    subject = msg.get('subject', '').lower()
                    
                    if 'openai' in sender:
                        if 'access deactivated' in subject or 'deactivated' in subject:
                            return True
                
                return False
                
            except Exception as e:
                print(f"[BAN] IMAP check error for {email_addr}: {e}")
                return False
    
    def _on_ban_check_complete(self, checked, banned):
        """Завершение проверки бана"""
        # Закрываем окно прогресса
        if hasattr(self, 'progress_window') and self.progress_window.winfo_exists():
            self.progress_window.destroy()
        
        # Сбрасываем флаг отмены
        self.ban_check_cancelled = False
        
        self.btn_check_ban.config(state=tk.NORMAL, text="🚫 Бан")
        self.update_listbox_colors()
        self.save_accounts_to_file()
        
        msg = f"Проверка завершена!\n\nПроверено: {checked}\nЗабанено: {banned}"
        if banned > 0:
            messagebox.showwarning("Результаты проверки", msg)
        else:
            messagebox.showinfo("Результаты проверки", msg)
        
        self.update_status(f"Проверка завершена. Забаненных: {banned}")
    
    def save_accounts_to_excel(self):
        """Сохраняет данные аккаунтов в Excel файл"""
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Аккаунты"
            
            headers = ["Логин/Пароль", "Логин", "Пароль"]
            header_fill = PatternFill(start_color="4CAF50", end_color="4CAF50", fill_type="solid")
            header_font_white = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            data_font = Font(name="Arial", size=10)
            
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col, value=header)
                cell.font = header_font_white
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
            
            ws.column_dimensions['A'].width = 50
            ws.column_dimensions['B'].width = 35
            ws.column_dimensions['C'].width = 20
            
            
            status_fills = {
                "not_registered": PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"),
                "registered": PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"),
                "plus": PatternFill(start_color="46BDC6", end_color="46BDC6", fill_type="solid"),
                "banned": PatternFill(start_color="FECACA", end_color="FECACA", fill_type="solid")
            }
            
            for row, account in enumerate(self.accounts_data, 2):
                email = account.get("email", "")
                password = account.get("password", "")
                status = account.get("status", "not_registered")
                
                ws.cell(row=row, column=1, value=f"{email} / {password}")
                ws.cell(row=row, column=2, value=email)
                ws.cell(row=row, column=3, value=password)
                row_fill = status_fills.get(status, status_fills["not_registered"])
                for col in range(1, 4):
                    cell = ws.cell(row=row, column=col)
                    cell.fill = row_fill
                    cell.font = data_font
            
            wb.save(EXCEL_FILE)
            
        except Exception as e:
            print(f"Ошибка сохранения Excel: {e}")
    
    def load_accounts_from_file(self):
        """Загрузка аккаунтов из файла"""
        self.acc_listbox.delete(0, tk.END)
        self.accounts_data = []
        
        if os.path.exists(ACCOUNTS_FILE):
            try:
                needs_save = False
                
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    email = ""
                    password = ""
                    status = "not_registered"
                    
                    if " / " in line:
                        parts = line.split(" / ")
                        if len(parts) >= 2:
                            email = parts[0].strip()
                            password = parts[1].strip()
                            if len(parts) >= 3:
                                status = parts[2].strip()
                    elif ":" in line:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            email, password = parts[0].strip(), parts[1].strip()
                            needs_save = True
                    
                    if email and password:
                        self.accounts_data.append({
                            "email": email,
                            "password": password,
                            "status": status
                        })
                        
                        display_text = f"{email} / {password}"
                        self.acc_listbox.insert(tk.END, display_text)
                
                if needs_save:
                    self.save_accounts_to_file()
                    self.update_status(f"Аккаунты конвертированы и загружены: {len(self.accounts_data)}")
                else:
                    self.save_accounts_to_excel()
                    self.update_status(f"Загружено аккаунтов: {len(self.accounts_data)}")
                
                self.update_listbox_colors()
                
            except Exception as e:
                messagebox.showerror("Ошибка чтения файла", str(e))
        else:
            self.update_status("Файл accounts.txt не найден")
    
    def start_create_account(self):
        """Запуск создания аккаунта"""
        self.btn_create.config(state=tk.DISABLED)
        self.update_status("Регистрация... (Подождите)")
        threading.Thread(target=self.create_account_thread, daemon=True).start()
    
    def create_account_thread(self):
        """Поток создания аккаунта"""
        try:
            domain_res = self._make_request('get', f"{API_URL}/domains", retry_auth=False)
            if not domain_res or domain_res.status_code != 200:
                error_msg = "Сетевая ошибка" if not domain_res else f"Код: {domain_res.status_code}"
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось получить список доменов\n{error_msg}"))
                self.root.after(0, lambda: self.btn_create.config(state=tk.NORMAL))
                return
            
            domains = domain_res.json()['hydra:member']
            domain = random.choice(domains)['domain']
            
            username = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(10))
            chars = string.ascii_letters + string.digits
            password = ''.join(random.choice(chars) for _ in range(12))
            
            email = f"{username}@{domain}"
            
            payload = {"address": email, "password": password}
            res = self._make_request('post', f"{API_URL}/accounts", retry_auth=False, json=payload)
            
            if not res:
                self.update_status("Сетевая ошибка при регистрации")
                self.root.after(0, lambda: messagebox.showerror("Ошибка", "Сетевая ошибка при регистрации"))
            elif res.status_code == 201:
                self.root.after(0, lambda: self._on_account_created(email, password))
            else:
                self.update_status("Ошибка регистрации")
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Код: {res.status_code}\n{res.text}"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_create.config(state=tk.NORMAL))
    
    def _on_account_created(self, email, password):
        """Обработка созданного аккаунта"""
        self.accounts_data.append({
            "email": email,
            "password": password,
            "status": "not_registered"
        })
        
        display_text = f"{email} / {password}"
        self.acc_listbox.insert(tk.END, display_text)
        self.update_listbox_colors()
        
        self.acc_listbox.selection_clear(0, tk.END)
        self.acc_listbox.selection_set(tk.END)
        
        self.save_accounts_to_file()
        
        self.status_var.set(f"Создан: {email}")
        self.on_account_select(None)
    
    def on_theme_toggle_click(self, is_on):
        """Обработка переключения темы"""
        self.set_theme("dark" if is_on else "light")
    
    def set_theme(self, theme_name):
        """Установка темы оформления"""
        self.params["theme"] = theme_name
        colors = THEMES[theme_name]
        accent_bg = colors.get("accent", colors["btn_bg"])
        accent_fg = colors.get("accent_fg", colors["btn_fg"])
        if hasattr(self, "theme_toggle"):
            self.theme_toggle.set_checked(theme_name == "dark")
            self.theme_toggle.set_theme(colors, accent_bg)
        
        # Root
        self.root.config(bg=colors["bg"])
        self.paned.config(bg=colors["header_bg"])
        self.status_bar.config(bg=colors["status_bg"], fg=colors["status_fg"])
        if hasattr(self, "root_container"):
            self.root_container.config(bg=colors["bg"])
        
        # Left Panel Components
        self.left_panel.config(bg=colors["panel_bg"])
        self.left_header.config(bg=colors["panel_bg"])
        
        for widget in self.left_header.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(bg=colors["panel_bg"], fg=colors["fg"])
            elif isinstance(widget, tk.Checkbutton):
                widget.config(
                    bg=colors["panel_bg"],
                    fg=colors["fg"],
                    activebackground=colors["panel_bg"],
                    activeforeground=colors["fg"],
                    selectcolor=accent_bg
                )
        
        self.lbl_saved.config(bg=colors["panel_bg"], fg=colors["fg"])
        self.file_btn_frame.config(bg=colors["panel_bg"])
        self.btn_frame.config(bg=colors["panel_bg"])
        
        # Person frame (random data)
        if hasattr(self, "person_frame"):
            self.person_frame.config(bg=colors["panel_bg"], fg=colors["fg"])
            for child in self.person_frame.winfo_children():
                if isinstance(child, tk.Frame):
                    child.config(bg=colors["panel_bg"])
                    for subchild in child.winfo_children():
                        if isinstance(subchild, tk.Label):
                            subchild.config(bg=colors["panel_bg"], fg=colors["fg"])
                        elif isinstance(subchild, tk.Entry):
                            subchild.config(readonlybackground=colors["entry_bg"], fg=colors["entry_fg"])
                        elif isinstance(subchild, tk.Button):
                            subchild.config(bg=colors["btn_bg"], fg=colors["btn_fg"], activebackground=colors["btn_bg"], activeforeground=colors["btn_fg"])
                elif isinstance(child, tk.Button):
                    child.config(bg=colors["btn_bg"], fg=colors["btn_fg"], activebackground=colors["btn_bg"], activeforeground=colors["btn_fg"])
        
        # Buttons (Generic)
        generic_btns = [
            self.btn_reload, self.btn_open_file, self.btn_open_excel,
            self.btn_copy_email, self.btn_copy_pass, self.btn_sk, self.btn_minesweeper, self.btn_hotkey_settings
        ]
        for btn in generic_btns:
            btn.config(bg=colors["btn_bg"], fg=colors["btn_fg"], activebackground=colors["btn_bg"], activeforeground=colors["btn_fg"], relief=tk.FLAT, bd=0)
        
        # Primary buttons
        primary_btns = [self.btn_create, self.btn_refresh, self.btn_copy_code]
        for btn in primary_btns:
            btn.config(bg=accent_bg, fg=accent_fg, activebackground=accent_bg, activeforeground=accent_fg, relief=tk.FLAT, bd=0)
        
        # Listbox
        self.acc_listbox.config(bg=colors["list_bg"], fg=colors["list_fg"], selectbackground=accent_bg, selectforeground=accent_fg, relief=tk.FLAT, borderwidth=0, highlightthickness=0)
        self.update_listbox_colors()
        
        # Right Panel Components
        self.right_panel.config(bg=colors["bg"])
        self.header_frame.config(bg=colors["header_bg"])
        self.status_frame.config(bg=colors["header_bg"])
        
        self.lbl_current_email.config(bg=colors["header_bg"], fg=colors["fg"])
        self.lbl_msg_title.config(bg=colors["bg"], fg=colors["fg"])
        self.btn_refresh.config(bg=accent_bg, fg=accent_fg, activebackground=accent_bg, activeforeground=accent_fg)
        status_btn_fg = "#0b1220" if theme_name == "light" else "#e2e8f0"
        self.btn_nr.config(
            bg=STATUS_COLORS["not_registered"][theme_name],
            fg=status_btn_fg,
            activebackground=STATUS_COLORS["not_registered"][theme_name],
            activeforeground=status_btn_fg,
            relief=tk.FLAT,
            bd=0
        )
        self.btn_reg.config(
            bg=STATUS_COLORS["registered"][theme_name],
            fg=status_btn_fg,
            activebackground=STATUS_COLORS["registered"][theme_name],
            activeforeground=status_btn_fg,
            relief=tk.FLAT,
            bd=0
        )
        self.btn_plus.config(
            bg=STATUS_COLORS["plus"][theme_name],
            fg=status_btn_fg,
            activebackground=STATUS_COLORS["plus"][theme_name],
            activeforeground=status_btn_fg,
            relief=tk.FLAT,
            bd=0
        )
        
        # Text
        self.msg_text.config(bg=colors["text_bg"], fg=colors["text_fg"], insertbackground=colors["fg"], relief=tk.FLAT, borderwidth=1, highlightthickness=0)
        
        # Treeview Style
        style = ttk.Style()
        selected_design = self.design_var.get() if hasattr(self, 'design_var') else style.theme_use()
        if selected_design not in style.theme_names():
            selected_design = "default" if "default" in style.theme_names() else style.theme_use()
        try:
            style.theme_use(selected_design)
        except Exception:
            selected_design = style.theme_use()
        if hasattr(self, "design_var"):
            self.design_var.set(selected_design)
        
        style.configure("Treeview",
                        background=colors["list_bg"],
                        foreground=colors["list_fg"],
                        fieldbackground=colors["list_bg"],
                        rowheight=25,
                        borderwidth=0)
        style.configure("Treeview.Heading",
                        background=accent_bg,
                        foreground=accent_fg,
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", accent_bg)],
                  foreground=[("selected", accent_fg)])
        
        if hasattr(self, 'lbl_theme'):
            self.lbl_theme.config(bg=colors["panel_bg"], fg=colors["fg"])
    
    def on_design_change(self, event=None):
        """Изменение дизайна (ttk theme)"""
        selected = self.design_var.get()
        style = ttk.Style()
        try:
            style.theme_use(selected)
            self.update_status(f"Дизайн изменен: {selected}")
        except Exception as e:
            self.update_status(f"Ошибка смены дизайна: {e}")
        
        self.set_theme(self.params.get("theme", "light"))
    
    def update_listbox_colors(self):
        """Обновление цветов списка аккаунтов"""
        theme = self.params.get("theme", "light")
        for i in range(self.acc_listbox.size()):
            if i < len(self.accounts_data):
                status = self.accounts_data[i].get("status", "not_registered")
                color = STATUS_COLORS.get(status, {}).get(theme, "white")
                if theme == "dark":
                    fg_color = "#e2e8f0"
                else:
                    fg_color = "#111827"
                    if status in ("registered", "plus"):
                        fg_color = "#0b1220"
                
                self.acc_listbox.itemconfig(i, {'bg': color, 'fg': fg_color})
    
    def on_account_select(self, event):
        """Выбор аккаунта"""
        selection = self.acc_listbox.curselection()
        if not selection:
            return
        
        data = self.acc_listbox.get(selection[0])
        
        if " / " in data:
            email, password = data.split(" / ", 1)
        elif ":" in data:
            email, password = data.split(":", 1)
        else:
            return
        
        self.lbl_current_email.config(text=f"Аккаунт: {email}")
        self.last_message_ids = set()
        
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.msg_text.delete(1.0, tk.END)
        self.msg_text.insert(tk.END, "Загрузка...")
        
        self.update_status("Авторизация...")
        threading.Thread(target=self.login_thread, args=(email, password), daemon=True).start()
    
    def login_thread(self, email_addr, password):
        """Поток авторизации"""
        domain = email_addr.split("@")[-1]
        self.current_token = None
        if self.imap_client:
            try:
                self.imap_client.logout()
            except Exception:
                pass
            self.imap_client = None
        
        # Сохраняем учётные данные для переподключения при смене VPN
        self.current_email = email_addr
        self.current_password = password
        
        # Сбрасываем HTTP сессию для чистого подключения
        self._reset_http_session()
        
        is_mail_tm = domain in self.mail_tm_domains or domain.endswith("mail.tm")
        
        success = False
        
        if is_mail_tm:
            try:
                payload = {"address": email_addr, "password": password}
                res = self._make_request('post', f"{API_URL}/token", retry_auth=False, json=payload)
                if res and res.status_code == 200:
                    self.current_token = res.json()['token']
                    self.account_type = "api"
                    success = True
                elif res:
                    print(f"API Login failed: {res.status_code}")
                else:
                    print("API Login failed: network error")
            except Exception as e:
                print(f"API Error: {e}")
        
        if not success:
            if self.imap_client:
                self.imap_client.logout()
            
            self.imap_client = IMAPClient(host="imap.firstmail.ltd")
            if self.imap_client.login(email_addr, password):
                self.account_type = "imap"
                success = True
            else:
                fallback_host = f"imap.{domain}"
                print(f"Trying fallback IMAP: {fallback_host}")
                self.imap_client = IMAPClient(host=fallback_host)
                if self.imap_client.login(email_addr, password):
                    self.account_type = "imap"
                    success = True
        
        if success:
            self.last_message_ids = set()
            self.update_status(f"Вход выполнен ({self.account_type.upper()}). Получаю письма...")
            self.refresh_inbox_thread(show_loading=True)
        else:
            self.update_status("Ошибка входа (API и IMAP недоступны)")
            self.current_token = None
            self.imap_client = None
    
    def on_manual_refresh(self):
        """Ручное обновление писем"""
        self.update_status("Обновление писем...")
        threading.Thread(target=lambda: self.refresh_inbox_thread(show_loading=True), daemon=True).start()
    
    def start_auto_refresh(self):
        """Запускает таймер автообновления"""
        if self.stop_threads:
            return
        
        should_refresh = (
            (self.account_type == "api" and self.current_token) or
            (self.account_type == "imap" and self.imap_client)
        )
        if should_refresh and not self.is_refreshing:
            threading.Thread(target=self.refresh_inbox_thread, daemon=True).start()
        
        self.root.after(self.refresh_interval_ms, self.start_auto_refresh)
    
    def refresh_inbox_thread(self, show_loading=False):
        """Поток обновления писем"""
        if self.is_refreshing:
            return
        if self.account_type == "api" and not self.current_token:
            return
        if self.account_type == "imap" and not self.imap_client:
            return
        
        self.is_refreshing = True
        # Показываем загрузку только при ручном обновлении
        if show_loading:
            self.root.after(0, self.show_inbox_loading_state)
            self.root.after(0, self.show_loading_messages_text)
        try:
            messages = []
            if self.account_type == "api":
                headers = {"Authorization": f"Bearer {self.current_token}"}
                res = self._make_request('get', f"{API_URL}/messages", retry_auth=True, headers=headers)
                if res is None:
                    # Сетевая ошибка - переподключение будет запущено автоматически
                    self.root.after(0, lambda: self.update_status("Сетевая ошибка, переподключение..."))
                elif res.status_code == 200:
                    messages = res.json()['hydra:member']
                elif res.status_code == 401:
                    # Токен недействителен - переавторизуемся
                    self.root.after(0, lambda: self.update_status("Сессия истекла, переподключение..."))
                    self._try_reauth()
                else:
                    self.root.after(0, lambda: self.update_status(f"Ошибка загрузки писем: {res.status_code}"))
            elif self.account_type == "imap":
                try:
                    messages = self.imap_client.get_messages(limit=20)
                except Exception as imap_err:
                    print(f"IMAP error: {imap_err}")
                    # IMAP соединение разорвано - переподключаемся
                    self.root.after(0, lambda: self.update_status("IMAP соединение потеряно, переподключение..."))
                    self._try_reauth()
            
            if messages:
                self.root.after(0, lambda: self._update_inbox_ui(messages))
        except Exception as e:
            print(f"Background update error: {e}")
        finally:
            self.is_refreshing = False
    
    def _update_inbox_ui(self, messages):
        """Обновление таблицы писем"""
        # Сохраняем выбранное письмо
        selected = self.tree.selection()
        selected_id = None
        if selected:
            values = self.tree.item(selected[0]).get("values", [])
            if len(values) >= 4:
                selected_id = values[3]
        
        # Очищаем список
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        seen_ids = set()
        new_selection = None
        
        for msg in messages:
            sender = msg.get('from', {}).get('address', "Неизвестно")
            subject = msg.get('subject') or "(без темы)"
            date_raw = msg.get('createdAt') or ""
            msg_id = msg.get('id')
            try:
                dt = datetime.fromisoformat(str(date_raw).replace("Z", "+00:00"))
                date_str = dt.strftime("%H:%M:%S")
            except Exception:
                date_str = date_raw
            
            item_id = self.tree.insert("", 0, values=(sender, subject, date_str, msg_id))
            seen_ids.add(msg_id)
            
            # Восстанавливаем выделение
            if selected_id and msg_id == selected_id:
                new_selection = item_id
        
        # Восстанавливаем выделение и прокрутку
        if new_selection:
            self.tree.selection_set(new_selection)
            self.tree.see(new_selection)
        
        # Очищаем текст только если нет писем И не было выбрано письмо
        if not messages and not selected_id:
            self.msg_text.delete(1.0, tk.END)
            self.msg_text.insert(tk.END, "Нет новых писем.")
        
        new_ids = [mid for mid in seen_ids if mid and mid not in self.last_message_ids]
        if self.last_message_ids and new_ids:
            self.play_notification_sound(len(new_ids))
        self.last_message_ids = seen_ids
        
        self.status_var.set(f"Обновлено: {datetime.now().strftime('%H:%M:%S')} • писем: {len(messages)}")
    
    def show_inbox_loading_state(self):
        """Показываем индикатор загрузки"""
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.tree.insert("", 0, values=("Загрузка писем...", "", "", "loading"))
        except Exception:
            pass
    
    def show_loading_messages_text(self):
        """Показываем текст загрузки"""
        try:
            if self.tree.selection():
                return
            self.btn_copy_code.pack_forget()
            self.msg_text.delete(1.0, tk.END)
            self.msg_text.insert(tk.END, "Загрузка сообщений...")
        except Exception:
            pass
    
    def on_message_select(self, event):
        """Выбор письма"""
        selected_item = self.tree.selection()
        if not selected_item:
            return
        
        item = self.tree.item(selected_item)
        values = item.get('values', [])
        if len(values) < 4:
            return
        msg_id = values[3]
        sender = values[0]
        subject = values[1]
        
        self.btn_copy_code.pack_forget()
        
        self.msg_text.delete(1.0, tk.END)
        self.msg_text.insert(tk.END, "Загрузка...")
        
        threading.Thread(target=self.load_message_thread, args=(msg_id, sender, subject), daemon=True).start()
    
    def load_message_thread(self, msg_id, sender=None, subject=None):
        """Поток загрузки письма"""
        if self.account_type == "api" and not self.current_token:
            return
        if self.account_type == "imap" and not self.imap_client:
            return
        
        try:
            if self.account_type == "api":
                headers = {"Authorization": f"Bearer {self.current_token}"}
                res = self._make_request('get', f"{API_URL}/messages/{msg_id}", retry_auth=True, headers=headers)
                if res is None:
                    self.root.after(0, lambda: self.msg_text.insert(tk.END, "\nСетевая ошибка при загрузке письма"))
                elif res.status_code == 200:
                    data = res.json()
                    text = data.get('text') or data.get('html') or "Нет текстового содержимого"
                    self.root.after(0, lambda: self._show_message_content(data, text))
                elif res.status_code == 401:
                    self.root.after(0, lambda: self.msg_text.insert(tk.END, "\nСессия истекла, переподключение..."))
                    self._try_reauth()
                else:
                    self.root.after(0, lambda: self.msg_text.insert(tk.END, f"\nОшибка загрузки письма: {res.status_code}"))
            elif self.account_type == "imap":
                try:
                    text = self.imap_client.get_message_content(msg_id)
                    data = {
                        "from": {"address": sender or "IMAP Sender"},
                        "subject": subject or "IMAP Message"
                    }
                    self.root.after(0, lambda: self._show_message_content(data, text, is_imap=True))
                except Exception as imap_err:
                    print(f"IMAP error loading message: {imap_err}")
                    self.root.after(0, lambda: self.msg_text.insert(tk.END, "\nIMAP соединение потеряно, переподключение..."))
                    self._try_reauth()
        except Exception as e:
            self.root.after(0, lambda: self.msg_text.insert(tk.END, f"\nError: {e}"))
    
    def _show_message_content(self, data, text, is_imap=False):
        """Отображение содержимого письма"""
        self.btn_copy_code.pack_forget()
        
        self.msg_text.delete(1.0, tk.END)
        sender = data.get('from', {}).get('address', 'Неизвестно')
        subject = data.get('subject', '(без темы)')
        self.msg_text.insert(tk.END, f"От: {sender}\n")
        self.msg_text.insert(tk.END, f"Тема: {subject}\n")
        
        self.msg_text.insert(tk.END, "-" * 50 + "\n\n")
        self.msg_text.insert(tk.END, text)
        
        match = re.search(r'\b(\d{6})\b', text)
        if match:
            code = match.group(1)
            self.btn_copy_code.config(text=f"📋 Скопировать код: {code}", command=lambda: self.copy_code_to_clipboard(code))
            self.btn_copy_code.pack(before=self.msg_text, fill=tk.X, padx=10, pady=5)
    
    def copy_code_to_clipboard(self, code):
        """Копирование кода в буфер"""
        pyperclip.copy(code)
        self.status_var.set(f"Код {code} скопирован в буфер!")
    
    def copy_email(self):
        """Копирование email"""
        selection = self.acc_listbox.curselection()
        if selection:
            data = self.acc_listbox.get(selection[0])
            if " / " in data:
                email = data.split(" / ")[0]
            elif ":" in data:
                email = data.split(":")[0]
            else:
                return
            pyperclip.copy(email)
            self.status_var.set("Email скопирован в буфер")
    
    def copy_pass(self):
        """Копирование пароля"""
        selection = self.acc_listbox.curselection()
        if selection:
            data = self.acc_listbox.get(selection[0])
            if " / " in data:
                password = data.split(" / ")[1]
            elif ":" in data:
                password = data.split(":")[1]
            else:
                return
            pyperclip.copy(password)
            self.status_var.set("Пароль скопирован в буфер")
    
    def show_context_menu(self, event):
        """Показ контекстного меню"""
        try:
            self.acc_listbox.selection_clear(0, tk.END)
            self.acc_listbox.selection_set(self.acc_listbox.nearest(event.y))
            self.acc_listbox.activate(self.acc_listbox.nearest(event.y))
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def set_account_status(self, status):
        """Установка статуса аккаунта"""
        selection = self.acc_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        
        if idx < len(self.accounts_data):
            self.accounts_data[idx]['status'] = status
            self.update_listbox_colors()
            self.save_accounts_to_file()
            self.update_status(f"Статус обновлен: {status}")
    
    def save_accounts_to_file(self):
        """Сохранение аккаунтов в файл"""
        try:
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                for item in self.accounts_data:
                    line = f"{item['email']} / {item['password']} / {item['status']}\n"
                    f.write(line)
            self.save_accounts_to_excel()
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e))
