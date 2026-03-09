# -*- coding: utf-8 -*-
"""
Project launcher screen shown before opening the main app.
"""

import tkinter as tk

from .widgets import HoverButton


class Launcher(tk.Frame):
    def __init__(self, root, on_select=None):
        super().__init__(root, bg="#0f172c")
        self.root = root
        self.on_select = on_select
        self.pack(fill=tk.BOTH, expand=True)
        self._build()

    def _build(self):
        container = tk.Frame(self, bg="#0f172c")
        container.place(relx=0.5, rely=0.5, anchor="center")

        title = tk.Label(
            container,
            text="Выберите проект",
            font=("Segoe UI", 20, "bold"),
            bg="#0f172c",
            fg="#eaf1ff",
        )
        title.pack(pady=(0, 18))

        cards = tk.Frame(container, bg="#0f172c")
        cards.pack()

        self._make_card(
            cards,
            title="Mail.tm Auto-Reg",
            subtitle="Локальное Tkinter-приложение",
            button_text="Открыть",
            key="autoreg",
        ).pack(side=tk.LEFT, padx=8)
        self._make_card(
            cards,
            title="WAVE",
            subtitle="Открыть веб-интерфейс в браузере",
            button_text="Открыть",
            key="wave",
        ).pack(side=tk.LEFT, padx=8)

    def _make_card(self, parent, title, subtitle, button_text, key):
        card = tk.Frame(parent, bg="#16213a", bd=0, padx=16, pady=14, width=210, height=170)
        card.pack_propagate(False)

        tk.Label(
            card,
            text=title,
            font=("Segoe UI", 12, "bold"),
            bg="#16213a",
            fg="#eaf1ff",
            wraplength=180,
            justify="center",
        ).pack(pady=(2, 8))
        tk.Label(
            card,
            text=subtitle,
            font=("Segoe UI", 9),
            bg="#16213a",
            fg="#9db2d8",
            wraplength=180,
            justify="center",
        ).pack(pady=(0, 14))

        HoverButton(
            card,
            text=button_text,
            font=("Segoe UI", 10, "bold"),
            bg="#3a7bff",
            fg="#ffffff",
            hover_bg="#2e68de",
            hover_fg="#ffffff",
            command=lambda selected=key: self._select(selected),
            pady=6,
        ).pack(fill=tk.X)

        return card

    def _select(self, key):
        if self.on_select:
            self.on_select(key)
