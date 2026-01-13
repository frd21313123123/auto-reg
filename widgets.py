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
