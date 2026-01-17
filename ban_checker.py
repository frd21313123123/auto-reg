# -*- coding: utf-8 -*-
"""
Автоматическая проверка аккаунтов на бан OpenAI.
Консольный скрипт без GUI, работает в бесконечном цикле.
Использует многопоточность для ускорения проверки.

Использование:
    python ban_checker.py [--interval МИНУТЫ] [--once] [--threads N]

Аргументы:
    --interval  Интервал между проверками в минутах (по умолчанию: 30)
    --once      Выполнить только одну проверку и выйти
    --threads   Количество потоков для параллельной проверки (по умолчанию: 5)
"""

import os
import sys
import time
import argparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Добавляем путь к модулям приложения
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from app.config import API_URL, ACCOUNTS_FILE, EXCEL_FILE
from app.imap_client import IMAPClient

# Цвета для консоли (ANSI)
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class BanChecker:
    """Класс для проверки аккаунтов на бан OpenAI с многопоточностью"""
    
    def __init__(self, num_threads=5):
        self.accounts_data = []
        self.mail_tm_domains = []
        self.num_threads = num_threads
        self.lock = threading.Lock()  # Для потокобезопасного вывода и обновления
        self._load_domains()
    
    def _create_http_session(self):
        """Создание HTTP сессии с настройками переподключения (для каждого потока)"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=1,
            pool_maxsize=1,
            pool_block=False
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(self, session, method, url, **kwargs):
        """Выполнить HTTP запрос с обработкой ошибок"""
        try:
            response = getattr(session, method)(url, timeout=15, **kwargs)
            return response
        except Exception as e:
            return None
    
    def _load_domains(self):
        """Загрузка доменов mail.tm"""
        try:
            session = self._create_http_session()
            res = self._make_request(session, 'get', f"{API_URL}/domains")
            if res and res.status_code == 200:
                data = res.json()['hydra:member']
                self.mail_tm_domains = [d['domain'] for d in data]
                print(f"{Colors.CYAN}[INFO] Загружено {len(self.mail_tm_domains)} доменов mail.tm{Colors.END}")
            session.close()
        except Exception as e:
            print(f"{Colors.YELLOW}[WARN] Не удалось загрузить домены: {e}{Colors.END}")
    
    def load_accounts(self):
        """Загрузка аккаунтов из файла"""
        self.accounts_data = []
        
        if not os.path.exists(ACCOUNTS_FILE):
            print(f"{Colors.RED}[ERROR] Файл {ACCOUNTS_FILE} не найден{Colors.END}")
            return False
        
        try:
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
                
                if email and password:
                    self.accounts_data.append({
                        "email": email,
                        "password": password,
                        "status": status
                    })
            
            print(f"{Colors.GREEN}[OK] Загружено {len(self.accounts_data)} аккаунтов{Colors.END}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}[ERROR] Ошибка чтения файла: {e}{Colors.END}")
            return False
    
    def save_accounts(self):
        """Сохранение аккаунтов в файл"""
        try:
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                for item in self.accounts_data:
                    line = f"{item['email']} / {item['password']} / {item['status']}\n"
                    f.write(line)
            return True
        except Exception as e:
            print(f"{Colors.RED}[ERROR] Ошибка сохранения: {e}{Colors.END}")
            return False
    
    def check_account(self, email_addr, password):
        """
        Проверка одного аккаунта на бан OpenAI.
        Создаёт собственную HTTP сессию для потокобезопасности.
        
        Returns:
            tuple: (result, reason)
        """
        session = self._create_http_session()
        
        try:
            domain = email_addr.split("@")[-1]
            is_mail_tm = domain in self.mail_tm_domains or domain.endswith("mail.tm")
            
            if is_mail_tm:
                try:
                    # Получаем токен
                    payload = {"address": email_addr, "password": password}
                    res = self._make_request(session, 'post', f"{API_URL}/token", json=payload)
                    
                    if not res:
                        return ("error", "network_error")
                    
                    if res.status_code == 401:
                        return ("invalid_password", "wrong_credentials")
                    
                    if res.status_code != 200:
                        return ("error", f"auth_failed_{res.status_code}")
                    
                    token = res.json().get('token')
                    if not token:
                        return ("error", "no_token")
                    
                    # Получаем список писем
                    headers = {"Authorization": f"Bearer {token}"}
                    res = self._make_request(session, 'get', f"{API_URL}/messages", headers=headers)
                    
                    if not res or res.status_code != 200:
                        return ("error", "messages_failed")
                    
                    messages = res.json().get('hydra:member', [])
                    
                    # Проверяем каждое письмо на признаки бана
                    for msg in messages:
                        sender = msg.get('from', {}).get('address', '').lower()
                        subject = msg.get('subject', '').lower()
                        
                        if 'openai' in sender or 'noreply@tm.openai.com' in sender:
                            if 'access deactivated' in subject or 'deactivated' in subject:
                                return ("banned", "access_deactivated")
                        
                        if 'access deactivated' in subject and 'openai' in sender:
                            return ("banned", "access_deactivated")
                    
                    return ("ok", "no_ban_found")
                    
                except Exception as e:
                    return ("error", str(e))
            else:
                # IMAP проверка
                try:
                    imap_client = IMAPClient(host=f"imap.{domain}")
                    login_success = imap_client.login(email_addr, password)
                    
                    if not login_success:
                        imap_client = IMAPClient(host="imap.firstmail.ltd")
                        login_success = imap_client.login(email_addr, password)
                        
                        if not login_success:
                            return ("invalid_password", "imap_login_failed")
                    
                    messages = imap_client.get_messages(limit=50)
                    imap_client.logout()
                    
                    for msg in messages:
                        sender = msg.get('from', {}).get('address', '').lower()
                        subject = msg.get('subject', '').lower()
                        
                        if 'openai' in sender:
                            if 'access deactivated' in subject or 'deactivated' in subject:
                                return ("banned", "access_deactivated")
                    
                    return ("ok", "no_ban_found")
                    
                except Exception as e:
                    return ("error", str(e))
        finally:
            session.close()
    
    def _check_account_wrapper(self, idx, account):
        """Обёртка для проверки аккаунта с индексом"""
        email = account.get("email", "")
        password = account.get("password", "")
        old_status = account.get("status", "not_registered")
        
        if not email or not password:
            return (idx, None, None, None)
        
        result, reason = self.check_account(email, password)
        return (idx, email, result, reason)
    
    def run_check(self):
        """Выполнить проверку всех аккаунтов с многопоточностью"""
        if not self.load_accounts():
            return
        
        total = len(self.accounts_data)
        banned_count = 0
        invalid_pass_count = 0
        ok_count = 0
        error_count = 0
        checked_count = 0
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}Начинаю проверку {total} аккаунтов ({self.num_threads} потоков)...{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        
        start_time = time.time()
        
        # Используем ThreadPoolExecutor для параллельной проверки
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            # Запускаем все задачи
            futures = {
                executor.submit(self._check_account_wrapper, idx, account): idx 
                for idx, account in enumerate(self.accounts_data)
            }
            
            # Обрабатываем результаты по мере завершения
            for future in as_completed(futures):
                try:
                    idx, email, result, reason = future.result()
                    
                    if email is None:
                        continue
                    
                    checked_count += 1
                    progress = f"[{checked_count}/{total}]"
                    
                    # Потокобезопасный вывод
                    with self.lock:
                        if result == "banned":
                            self.accounts_data[idx]["status"] = "banned"
                            banned_count += 1
                            print(f"{Colors.CYAN}{progress}{Colors.END} {email[:35]:35} {Colors.RED}🚫 BANNED{Colors.END}")
                        elif result == "invalid_password":
                            self.accounts_data[idx]["status"] = "invalid_password"
                            invalid_pass_count += 1
                            print(f"{Colors.CYAN}{progress}{Colors.END} {email[:35]:35} {Colors.PURPLE}🔒 НЕВЕРНЫЙ ПАРОЛЬ{Colors.END}")
                        elif result == "ok":
                            ok_count += 1
                            print(f"{Colors.CYAN}{progress}{Colors.END} {email[:35]:35} {Colors.GREEN}✓ OK{Colors.END}")
                        else:
                            error_count += 1
                            print(f"{Colors.CYAN}{progress}{Colors.END} {email[:35]:35} {Colors.YELLOW}⚠ ОШИБКА: {reason}{Colors.END}")
                            
                except Exception as e:
                    with self.lock:
                        error_count += 1
                        print(f"{Colors.RED}[ERROR] Ошибка обработки: {e}{Colors.END}")
        
        elapsed_time = time.time() - start_time
        
        # Сохраняем результаты
        self.save_accounts()
        
        # Выводим итоги
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}РЕЗУЛЬТАТЫ ПРОВЕРКИ{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"  Потоков:            {self.num_threads}")
        print(f"  Время выполнения:   {elapsed_time:.1f} сек ({elapsed_time/60:.1f} мин)")
        print(f"  Скорость:           {total/elapsed_time:.1f} акк/сек")
        print(f"  {Colors.BOLD}---{Colors.END}")
        print(f"  Всего проверено:    {total}")
        print(f"  {Colors.GREEN}✓ OK:               {ok_count}{Colors.END}")
        print(f"  {Colors.RED}🚫 Забанено:        {banned_count}{Colors.END}")
        print(f"  {Colors.PURPLE}🔒 Неверный пароль: {invalid_pass_count}{Colors.END}")
        print(f"  {Colors.YELLOW}⚠ Ошибки:          {error_count}{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        
        return {
            "total": total,
            "ok": ok_count,
            "banned": banned_count,
            "invalid_password": invalid_pass_count,
            "errors": error_count,
            "time": elapsed_time
        }


def main():
    parser = argparse.ArgumentParser(
        description="Автоматическая проверка аккаунтов на бан OpenAI (многопоточная)"
    )
    parser.add_argument(
        "--interval", 
        type=int, 
        default=30,
        help="Интервал между проверками в минутах (по умолчанию: 30)"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Выполнить только одну проверку и выйти"
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=5,
        help="Количество потоков для параллельной проверки (по умолчанию: 5)"
    )
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║     BAN CHECKER - Проверка аккаунтов OpenAI (MT)         ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    if args.once:
        print(f"{Colors.WHITE}Режим: Однократная проверка{Colors.END}")
    else:
        print(f"{Colors.WHITE}Режим: Бесконечный цикл (интервал: {args.interval} мин){Colors.END}")
        print(f"{Colors.WHITE}Для остановки нажмите Ctrl+C{Colors.END}")
    
    print(f"{Colors.WHITE}Потоков: {args.threads}{Colors.END}\n")
    
    checker = BanChecker(num_threads=args.threads)
    cycle = 0
    
    try:
        while True:
            cycle += 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{Colors.BLUE}[{now}] Цикл #{cycle}{Colors.END}")
            
            result = checker.run_check()
            
            if args.once:
                print(f"{Colors.GREEN}Проверка завершена.{Colors.END}")
                break
            
            # Ожидание до следующей проверки
            print(f"{Colors.CYAN}Следующая проверка через {args.interval} минут...{Colors.END}")
            print(f"{Colors.CYAN}Нажмите Ctrl+C для остановки{Colors.END}\n")
            
            time.sleep(args.interval * 60)
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[STOP] Остановлено пользователем{Colors.END}")
        sys.exit(0)


if __name__ == "__main__":
    main()
