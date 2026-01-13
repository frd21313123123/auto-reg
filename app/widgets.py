# -*- coding: utf-8 -*-
"""
Кастомные виджеты
"""

import tkinter as tk


class AnimatedToggle(tk.Canvas):
    """Анимированный переключатель (toggle switch)"""
    
    def __init__(self, parent, on_toggle=None, width=50, height=24, bg_on="#4CAF50", bg_off="#ccc"):
        super().__init__(parent, width=width, height=height, bd=0, highlightthickness=0, cursor="hand2")
        self.on_toggle = on_toggle
        self.is_on = False
        self.width = width
        self.height = height
        self.bg_on = bg_on
        self.bg_off = bg_off
        
        # Размеры
        self.p = 2
        self.d = height - 2 * self.p
        
        # Рисуем фон (капсула)
        self.rect = self.create_oval(0, 0, height, height, outline="", fill=bg_off)
        self.rect2 = self.create_oval(width - height, 0, width, height, outline="", fill=bg_off)
        self.rect3 = self.create_rectangle(height / 2, 0, width - height / 2, height, outline="", fill=bg_off)
        
        # Рисуем ручку
        self.handle = self.create_oval(self.p, self.p, self.p + self.d, self.p + self.d, fill="white", outline="")
        
        self.bind("<Button-1>", self.toggle)
    
    def toggle(self, event=None):
        self.is_on = not self.is_on
        self.animate()
        if self.on_toggle:
            self.on_toggle(self.is_on)
    
    def animate(self):
        target_x = self.width - self.d - self.p if self.is_on else self.p
        bg_color = self.bg_on if self.is_on else self.bg_off
        
        current_x = self.coords(self.handle)[0]
        
        # Шаг анимации
        dist = target_x - current_x
        step = dist * 0.4  # Плавный переход
        
        if abs(dist) < 1:
            self.move(self.handle, dist, 0)
            self.itemconfig(self.rect, fill=bg_color)
            self.itemconfig(self.rect2, fill=bg_color)
            self.itemconfig(self.rect3, fill=bg_color)
            return
        
        self.move(self.handle, step, 0)
        self.itemconfig(self.rect, fill=bg_color)
        self.itemconfig(self.rect2, fill=bg_color)
        self.itemconfig(self.rect3, fill=bg_color)
        self.after(10, self.animate)


class ThemedCheckbox(tk.Canvas):
    """Крупная стилизованная галочка."""

    def __init__(self, parent, on_toggle=None, size=24, checked=False):
        super().__init__(parent, width=size, height=size, bd=0, highlightthickness=0, cursor="hand2")
        self.on_toggle = on_toggle
        self.size = size
        self.checked = checked
        self.colors = {
            "bg": "#ffffff",
            "border": "#cbd5f5",
            "box_bg": "#ffffff",
            "check": "#111827",
            "accent": "#2563eb"
        }
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def set_theme(self, colors, accent_bg):
        self.colors["bg"] = colors["panel_bg"]
        self.colors["border"] = colors["status_fg"]
        self.colors["box_bg"] = colors["panel_bg"]
        self.colors["check"] = colors.get("accent_fg", colors["fg"])
        self.colors["accent"] = accent_bg
        self.config(bg=colors["panel_bg"])
        self.draw()

    def set_checked(self, checked):
        self.checked = bool(checked)
        self.draw()

    def toggle(self, event=None):
        self.checked = not self.checked
        self.draw()
        if self.on_toggle:
            self.on_toggle(self.checked)

    def draw(self):
        self.delete("all")
        pad = 3
        x0 = pad
        y0 = pad
        x1 = self.size - pad
        y1 = self.size - pad

        if self.checked:
            fill = self.colors["accent"]
            outline = self.colors["accent"]
        else:
            fill = self.colors["box_bg"]
            outline = self.colors["border"]

        self.create_rectangle(x0, y0, x1, y1, outline=outline, width=2, fill=fill)

        if self.checked:
            self.create_line(
                x0 + 3, y0 + 7,
                x0 + 7, y1 - 4,
                x1 - 3, y0 + 4,
                fill=self.colors["check"],
                width=2,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND
            )
