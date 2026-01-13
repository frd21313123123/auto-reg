# -*- coding: utf-8 -*-
"""
Generator window for South Korea data.
"""

import tkinter as tk
import random
import pyperclip
from datetime import datetime
from faker import Faker

from .themes import THEMES


def show_sk_window(parent, theme_name="light"):
    """Открывает окно с генератором данных для Южной Кореи."""
    win = tk.Toplevel(parent)
    win.title("South Korea Data Generator")
    win.geometry("500x550")
    win.overrideredirect(True)

    colors = THEMES[theme_name]
    accent_bg = colors.get("accent", "#2563eb")
    accent_fg = colors.get("accent_fg", colors["fg"])
    win.config(bg=colors["bg"])

    # Container + title bar
    root_container = tk.Frame(win, bg=colors["bg"], highlightthickness=1, highlightbackground=colors["header_bg"])
    root_container.pack(fill=tk.BOTH, expand=True)

    title_bar = tk.Frame(root_container, height=34, bg=colors["header_bg"])
    title_bar.pack(side=tk.TOP, fill=tk.X)

    title_label = tk.Label(title_bar, text="South Korea Data Generator", bg=colors["header_bg"], fg=colors["fg"])
    title_label.pack(side=tk.LEFT, padx=10)

    _is_maximized = {"value": False}
    _normal_geometry = {"value": None}

    def toggle_maximize():
        if not _is_maximized["value"]:
            _normal_geometry["value"] = win.geometry()
            w = win.winfo_screenwidth()
            h = win.winfo_screenheight()
            win.geometry(f"{w}x{h}+0+0")
            _is_maximized["value"] = True
        else:
            if _normal_geometry["value"]:
                win.geometry(_normal_geometry["value"])
            _is_maximized["value"] = False

    btn_maximize = tk.Button(title_bar, text="□", width=3, bd=0, command=toggle_maximize, font=("Segoe UI", 10, "bold"))
    btn_maximize.pack(side=tk.RIGHT, padx=(2, 0), pady=4)

    btn_close = tk.Button(title_bar, text="✕", width=3, bd=0, command=win.destroy, font=("Segoe UI", 10, "bold"))
    btn_close.pack(side=tk.RIGHT, padx=(2, 0), pady=4)

    btn_maximize.config(bg=colors["header_bg"], fg=colors["fg"], activebackground=accent_bg, activeforeground=accent_fg)
    btn_close.config(bg=colors["header_bg"], fg=colors["fg"], activebackground="#b91c1c", activeforeground="#ffffff")
    btn_maximize.bind("<Enter>", lambda e: btn_maximize.config(bg=accent_bg, fg=accent_fg))
    btn_maximize.bind("<Leave>", lambda e: btn_maximize.config(bg=colors["header_bg"], fg=colors["fg"]))
    btn_close.bind("<Enter>", lambda e: btn_close.config(bg="#b91c1c", fg="#ffffff"))
    btn_close.bind("<Leave>", lambda e: btn_close.config(bg=colors["header_bg"], fg=colors["fg"]))

    def start_move(event):
        win._drag_start_x = event.x
        win._drag_start_y = event.y

    def do_move(event):
        x = event.x_root - win._drag_start_x
        y = event.y_root - win._drag_start_y
        win.geometry(f"+{x}+{y}")

    title_bar.bind("<ButtonPress-1>", start_move)
    title_bar.bind("<B1-Motion>", do_move)
    title_bar.bind("<Double-Button-1>", lambda e: toggle_maximize())
    title_label.bind("<ButtonPress-1>", start_move)
    title_label.bind("<B1-Motion>", do_move)
    title_label.bind("<Double-Button-1>", lambda e: toggle_maximize())

    content_frame = tk.Frame(root_container, bg=colors["bg"])
    content_frame.pack(fill=tk.BOTH, expand=True)

    fake_kr = Faker("ko_KR")
    lbl_font = ("Arial", 10, "bold")
    val_font = ("Arial", 10)

    content_frame.columnconfigure(1, weight=1)

    def generate_card():
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
        districts = ["Gangnam-gu", "Mapo-gu", "Yongsan-gu", "Seocho-gu", "Songpa-gu", "Jongno-gu", "Jung-gu"]
        streets = ["Teheran-ro", "Hakdong-ro", "Olympic-ro", "Hangang-daero", "Sejong-daero", "Saimdang-ro"]
        district = random.choice(districts)
        street = random.choice(streets)
        bldg = random.randint(1, 999)
        return f"{bldg}, {street}, {district}, Seoul, Republic of Korea"

    def refresh_data():
        name_val.set(fake_kr.name())
        c_num, c_exp, c_cvv = generate_card()
        card_val.set(c_num)
        card_extra_val.set(f"Exp: {c_exp}  CVV: {c_cvv}")
        city_val.set("Сеул")
        street_val.set(f"{fake_kr.street_name()} {fake_kr.building_number()}")
        postcode_val.set(fake_kr.postcode())
        addr_en_val.set(generate_eng_address())

    def create_row(parent_frame, label_text, variable, row, copy_func=None):
        tk.Label(parent_frame, text=label_text, font=lbl_font, anchor="w",
                 bg=colors["bg"], fg=colors["fg"]).grid(row=row, column=0, padx=10, pady=(10, 0), sticky="w")

        e = tk.Entry(parent_frame, textvariable=variable, font=val_font, state="readonly",
                     readonlybackground=colors["entry_bg"], fg=colors["entry_fg"])
        e.grid(row=row + 1, column=0, columnspan=2, padx=10, pady=(0, 5), sticky="ew")

        btn_bg = colors["btn_bg"]
        btn_fg = colors["btn_fg"]
        if copy_func:
            tk.Button(parent_frame, text="Copy", command=copy_func, width=6,
                      bg=btn_bg, fg=btn_fg).grid(row=row + 1, column=2, padx=5, pady=(0, 5))
        else:
            tk.Button(parent_frame, text="Copy", command=lambda: copy_to_clipboard(variable.get()),
                      width=6, bg=btn_bg, fg=btn_fg).grid(row=row + 1, column=2, padx=5, pady=(0, 5))

    def copy_to_clipboard(text):
        pyperclip.copy(text)

    name_val = tk.StringVar()
    card_val = tk.StringVar()
    card_extra_val = tk.StringVar()
    city_val = tk.StringVar()
    street_val = tk.StringVar()
    postcode_val = tk.StringVar()
    addr_en_val = tk.StringVar()

    r = 0
    create_row(content_frame, "Имя (Name):", name_val, r)
    r += 2

    create_row(content_frame, "Номер карты:", card_val, r)
    r += 2

    extra_color = "#aaa" if theme_name == "dark" else "#555"
    tk.Label(content_frame, textvariable=card_extra_val, font=("Arial", 9),
             fg=extra_color, bg=colors["bg"]).grid(row=r, column=0, columnspan=2, padx=10, sticky="w")
    r += 1

    create_row(content_frame, "Город (City):", city_val, r)
    r += 2

    create_row(content_frame, "Улица (Street):", street_val, r)
    r += 2

    create_row(content_frame, "Индекс (Postcode):", postcode_val, r)
    r += 2

    create_row(content_frame, "Address (English):", addr_en_val, r)
    r += 2

    btn_frame_win = tk.Frame(content_frame, bg=colors["bg"])
    btn_frame_win.grid(row=r, column=0, columnspan=3, pady=20)

    tk.Button(btn_frame_win, text="Сгенерировать", command=refresh_data,
              bg=accent_bg, fg=accent_fg, font=("Arial", 10, "bold"), padx=10).pack(side=tk.LEFT, padx=5)

    refresh_data()
