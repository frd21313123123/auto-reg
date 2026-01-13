# -*- coding: utf-8 -*-
"""
Генератор данных Южной Кореи
"""

import tkinter as tk
import random
import pyperclip
from datetime import datetime
from faker import Faker

from .themes import THEMES


def show_sk_window(parent, theme_name="light"):
    """Открывает окно с генератором данных Южной Кореи"""
    win = tk.Toplevel(parent)
    win.title("🇰🇷 South Korea Data Generator")
    win.geometry("500x550")
    
    colors = THEMES[theme_name]
    win.config(bg=colors["bg"])
    
    fake_kr = Faker('ko_KR')
    
    # Стили
    lbl_font = ("Arial", 10, "bold")
    val_font = ("Arial", 10)
    
    win.columnconfigure(1, weight=1)
    
    def generate_card():
        """Генерация номера карты с BIN 6258142602"""
        prefix = "6258142602"
        temp_digits = [int(d) for d in prefix]
        for _ in range(5):
            temp_digits.append(random.randint(0, 9))
        
        checksum = 0
        for i, d in enumerate(temp_digits):
            if i % 2 == 0:
                val = d * 2
                if val > 9:
                    val -= 9
                checksum += val
            else:
                checksum += d
        
        check_digit = (10 - (checksum % 10)) % 10
        card_num = "".join(map(str, temp_digits)) + str(check_digit)
        
        month = random.randint(1, 12)
        year = datetime.now().year + random.randint(1, 5)
        exp_date = f"{month:02d}/{str(year)[-2:]}"
        cvv = f"{random.randint(100, 999)}"
        
        return card_num, exp_date, cvv
    
    def generate_eng_address():
        """Генерация адреса на английском"""
        districts = ["Gangnam-gu", "Mapo-gu", "Yongsan-gu", "Seocho-gu", "Songpa-gu", "Jongno-gu", "Jung-gu"]
        streets = ["Teheran-ro", "Hakdong-ro", "Olympic-ro", "Hangang-daero", "Sejong-daero", "Saimdang-ro"]
        
        district = random.choice(districts)
        street = random.choice(streets)
        bldg = random.randint(1, 999)
        
        return f"{bldg}, {street}, {district}, Seoul, Republic of Korea"
    
    def refresh_data():
        """Обновление всех данных"""
        name_val.set(fake_kr.name())
        
        c_num, c_exp, c_cvv = generate_card()
        card_val.set(c_num)
        card_extra_val.set(f"Exp: {c_exp}  CVV: {c_cvv}")
        
        city_val.set("서울")
        street_val.set(f"{fake_kr.street_name()} {fake_kr.building_number()}")
        postcode_val.set(fake_kr.postcode())
        addr_en_val.set(generate_eng_address())
    
    def create_row(parent_frame, label_text, variable, row, copy_func=None):
        """Создание строки с полем и кнопкой копирования"""
        tk.Label(parent_frame, text=label_text, font=lbl_font, anchor="w",
                 bg=colors["bg"], fg=colors["fg"]).grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")
        
        e = tk.Entry(parent_frame, textvariable=variable, font=val_font, state="readonly",
                     readonlybackground=colors["entry_bg"], fg=colors["entry_fg"])
        e.grid(row=row + 1, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")
        
        btn_bg = colors["btn_bg"]
        btn_fg = colors["btn_fg"]
        
        if copy_func:
            tk.Button(parent_frame, text="📋", command=copy_func, width=4,
                      bg=btn_bg, fg=btn_fg).grid(row=row + 1, column=2, padx=5, pady=(0, 5))
        else:
            tk.Button(parent_frame, text="📋", command=lambda: copy_to_clipboard(variable.get()),
                      width=4, bg=btn_bg, fg=btn_fg).grid(row=row + 1, column=2, padx=5, pady=(0, 5))
    
    def copy_to_clipboard(text):
        """Копирование в буфер обмена"""
        pyperclip.copy(text)
    
    # Переменные
    name_val = tk.StringVar()
    card_val = tk.StringVar()
    card_extra_val = tk.StringVar()
    city_val = tk.StringVar()
    street_val = tk.StringVar()
    postcode_val = tk.StringVar()
    addr_en_val = tk.StringVar()
    
    # Создание строк
    r = 0
    create_row(win, "👤 Имя (Name):", name_val, r)
    r += 2
    
    create_row(win, "💳 Номер карты:", card_val, r)
    r += 2
    
    extra_color = "#aaa" if theme_name == "dark" else "#555"
    tk.Label(win, textvariable=card_extra_val, font=("Arial", 9),
             fg=extra_color, bg=colors["bg"]).grid(row=r, column=0, columnspan=2, padx=10, sticky="w")
    r += 1
    
    create_row(win, "🏙️ Город (City):", city_val, r)
    r += 2
    
    create_row(win, "🛣️ Улица (Street):", street_val, r)
    r += 2
    
    create_row(win, "📮 Индекс (Postcode):", postcode_val, r)
    r += 2
    
    create_row(win, "🌍 Address (English):", addr_en_val, r)
    r += 2
    
    # Кнопка генерации
    btn_frame_win = tk.Frame(win, bg=colors["bg"])
    btn_frame_win.grid(row=r, column=0, columnspan=3, pady=20)
    
    tk.Button(btn_frame_win, text="🔄 Сгенерировать", command=refresh_data,
              bg="#2196F3", fg="white", font=("Arial", 10, "bold"), padx=10).pack(side=tk.LEFT, padx=5)
    
    # Начальная генерация
    refresh_data()
