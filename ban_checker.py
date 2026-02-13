# -*- coding: utf-8 -*-
"""
Автоматическая проверка аккаунтов на бан OpenAI.
Консольный скрипт без GUI, работает в бесконечном цикле.
Использует многопоточность для ускорения проверки.

Использование:
    python ban_checker.py [--interval МИНУТЫ] [--once] [--threads N] [--recheck-known]

Аргументы:
    --interval  Интервал между проверками в минутах (по умолчанию: 30)
    --once      Выполнить только одну проверку и выйти
    --threads   Количество потоков для параллельной проверки (по умолчанию: 8)
    --recheck-known Перепроверять аккаунты со статусом banned/invalid_password
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

# Принудительно включаем UTF-8 для стабильного вывода Unicode в Windows консоли.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
    
    def __init__(self, num_threads=5, skip_known_status=True):
        self.accounts_data = []
        self.mail_tm_domains = []
        self.num_threads = num_threads
        self.skip_known_status = skip_known_status
        self.lock = threading.Lock()  # Для потокобезопасного вывода и обновления
        self._thread_local = threading.local()
        self._thread_sessions = []
        self._thread_sessions_lock = threading.Lock()
        self._imap_host_cache = {}
        self._imap_host_lock = threading.Lock()
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

    def _get_thread_session(self):
        """Возвращает HTTP сессию текущего потока (реиспользуется между аккаунтами)."""
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = self._create_http_session()
            self._thread_local.session = session
            with self._thread_sessions_lock:
                self._thread_sessions.append(session)
        return session

    def _close_thread_sessions(self):
        """Закрывает все HTTP сессии, созданные потоками проверки."""
        with self._thread_sessions_lock:
            sessions = self._thread_sessions[:]
            self._thread_sessions = []
        for session in sessions:
            try:
                session.close()
            except Exception:
                pass

    def _imap_hosts_for_domain(self, domain):
        """Список IMAP хостов в порядке приоритета (с учётом кеша успешного хоста)."""
        with self._imap_host_lock:
            cached = self._imap_host_cache.get(domain)
        candidates = [cached, "imap.firstmail.ltd", f"imap.{domain}"]
        hosts = []
        for host in candidates:
            if host and host not in hosts:
                hosts.append(host)
        return hosts

    def _remember_imap_host(self, domain, host):
        """Запоминает рабочий IMAP хост для домена."""
        with self._imap_host_lock:
            self._imap_host_cache[domain] = host
    
    def _make_request(self, session, method, url, **kwargs):
        """Выполнить HTTP запрос с обработкой ошибок"""
        try:
            timeout = kwargs.pop("timeout", (4, 10))
            response = getattr(session, method)(url, timeout=timeout, **kwargs)
            return response
        except Exception:
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
                password_openai = ""
                password_mail = ""
                status = "not_registered"
                
                if " / " in line:
                    parts = line.split(" / ")
                    if len(parts) >= 2:
                        email = parts[0].strip()
                        passwords = parts[1].strip()
                        if ";" in passwords:
                            pwd_parts = passwords.split(";", 1)
                            password_openai = pwd_parts[0].strip()
                            password_mail = pwd_parts[1].strip()
                        else:
                            password_openai = passwords
                            password_mail = passwords
                        if len(parts) >= 3:
                            status = parts[2].strip()
                elif ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        email = parts[0].strip()
                        passwords = parts[1].strip()
                        if ";" in passwords:
                            pwd_parts = passwords.split(";", 1)
                            password_openai = pwd_parts[0].strip()
                            password_mail = pwd_parts[1].strip()
                        else:
                            password_openai = passwords
                            password_mail = passwords
                
                password = password_mail or password_openai
                if email and password:
                    self.accounts_data.append({
                        "email": email,
                        "password": password,
                        "password_openai": password_openai,
                        "password_mail": password_mail,
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
                    password_openai = item.get("password_openai", item.get("password", ""))
                    password_mail = item.get("password_mail", item.get("password", ""))
                    if (
                        password_openai
                        and password_mail
                        and password_openai != password_mail
                    ):
                        passwords = f"{password_openai};{password_mail}"
                    else:
                        passwords = password_mail or password_openai
                    line = f"{item['email']} / {passwords} / {item['status']}\n"
                    f.write(line)
            return True
        except Exception as e:
            print(f"{Colors.RED}[ERROR] Ошибка сохранения: {e}{Colors.END}")
            return False
    
    def check_account(self, email_addr, password):
        """
        Проверка одного аккаунта на бан OpenAI.
        Использует HTTP сессию текущего потока (реиспользование для ускорения).
        
        Returns:
            tuple: (result, reason)
        """
        session = self._get_thread_session()
        
        domain = email_addr.split("@")[-1]
        is_mail_tm = domain in self.mail_tm_domains or domain.endswith("mail.tm")
        
        if is_mail_tm:
            try:
                payload = {"address": email_addr, "password": password}
                res = self._make_request(
                    session,
                    "post",
                    f"{API_URL}/token",
                    json=payload,
                    timeout=(4, 8),
                )
                
                if not res:
                    return ("error", "network_error")
                
                if res.status_code == 401:
                    return ("invalid_password", "wrong_credentials")
                
                if res.status_code != 200:
                    return ("error", f"auth_failed_{res.status_code}")
                
                token = res.json().get("token")
                if not token:
                    return ("error", "no_token")
                
                headers = {"Authorization": f"Bearer {token}"}
                res = self._make_request(
                    session,
                    "get",
                    f"{API_URL}/messages",
                    headers=headers,
                    timeout=(4, 8),
                )
                
                if not res or res.status_code != 200:
                    return ("error", "messages_failed")
                
                messages = res.json().get("hydra:member", [])
                
                for msg in messages:
                    sender = msg.get("from", {}).get("address", "").lower()
                    subject = msg.get("subject", "").lower()
                    
                    if "openai" in sender or "noreply@tm.openai.com" in sender:
                        if "access deactivated" in subject or "deactivated" in subject:
                            return ("banned", "access_deactivated")
                    
                    if "access deactivated" in subject and "openai" in sender:
                        return ("banned", "access_deactivated")
                
                return ("ok", "no_ban_found")
            except Exception as e:
                return ("error", str(e))

        # IMAP проверка
        imap_client = None
        try:
            for host in self._imap_hosts_for_domain(domain):
                client = IMAPClient(host=host, timeout=8)
                if client.login(email_addr, password):
                    imap_client = client
                    self._remember_imap_host(domain, host)
                    break
                client.logout()

            if not imap_client:
                return ("invalid_password", "imap_login_failed")

            messages = imap_client.get_messages(limit=30)
            
            for msg in messages:
                sender = msg.get("from", {}).get("address", "").lower()
                subject = msg.get("subject", "").lower()
                
                if "openai" in sender:
                    if "access deactivated" in subject or "deactivated" in subject:
                        return ("banned", "access_deactivated")
            
            return ("ok", "no_ban_found")
        except Exception as e:
            return ("error", str(e))
        finally:
            if imap_client:
                imap_client.logout()
    
    def _check_account_wrapper(self, idx, account):
        """Обёртка для проверки аккаунта с индексом"""
        email = account.get("email", "")
        password = account.get("password_mail", account.get("password", ""))
        status = account.get("status", "not_registered")
        
        if not email or not password:
            return (idx, None, None, None)
        if self.skip_known_status and status in ("banned", "invalid_password"):
            return (idx, email, "skipped", status)
        
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
        skipped_count = 0
        checked_count = 0
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        workers = max(1, min(self.num_threads, total or 1))
        print(f"{Colors.BOLD}Начинаю проверку {total} аккаунтов ({workers} потоков)...{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        
        start_time = time.time()
        
        # Используем ThreadPoolExecutor для параллельной проверки
        with ThreadPoolExecutor(max_workers=workers) as executor:
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
                        elif result == "skipped":
                            skipped_count += 1
                            print(f"{Colors.CYAN}{progress}{Colors.END} {email[:35]:35} {Colors.BLUE}⏭ SKIP ({reason}){Colors.END}")
                        else:
                            error_count += 1
                            print(f"{Colors.CYAN}{progress}{Colors.END} {email[:35]:35} {Colors.YELLOW}⚠ ОШИБКА: {reason}{Colors.END}")
                            
                except Exception as e:
                    with self.lock:
                        error_count += 1
                        print(f"{Colors.RED}[ERROR] Ошибка обработки: {e}{Colors.END}")
        
        elapsed_time = time.time() - start_time
        self._close_thread_sessions()
        
        # Сохраняем результаты
        self.save_accounts()
        
        # Выводим итоги
        print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}РЕЗУЛЬТАТЫ ПРОВЕРКИ{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}")
        print(f"  Потоков:            {workers}")
        print(f"  Время выполнения:   {elapsed_time:.1f} сек ({elapsed_time/60:.1f} мин)")
        print(f"  Скорость:           {total/max(elapsed_time, 0.1):.1f} акк/сек")
        print(f"  {Colors.BOLD}---{Colors.END}")
        print(f"  Всего проверено:    {total}")
        print(f"  {Colors.GREEN}✓ OK:               {ok_count}{Colors.END}")
        print(f"  {Colors.RED}🚫 Забанено:        {banned_count}{Colors.END}")
        print(f"  {Colors.PURPLE}🔒 Неверный пароль: {invalid_pass_count}{Colors.END}")
        print(f"  {Colors.BLUE}⏭ Пропущено:        {skipped_count}{Colors.END}")
        print(f"  {Colors.YELLOW}⚠ Ошибки:          {error_count}{Colors.END}")
        print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        
        return {
            "total": total,
            "ok": ok_count,
            "banned": banned_count,
            "invalid_password": invalid_pass_count,
            "skipped": skipped_count,
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
        default=8,
        help="Количество потоков для параллельной проверки (по умолчанию: 8)"
    )
    parser.add_argument(
        "--recheck-known",
        action="store_true",
        help="Перепроверять аккаунты со статусом banned/invalid_password"
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
    
    print(f"{Colors.WHITE}Потоков: {args.threads}{Colors.END}")
    if args.recheck_known:
        print(f"{Colors.WHITE}Режим статусов: перепроверять все{Colors.END}\n")
    else:
        print(f"{Colors.WHITE}Режим статусов: пропускать banned/invalid_password{Colors.END}\n")
    
    checker = BanChecker(
        num_threads=args.threads,
        skip_known_status=not args.recheck_known,
    )
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
