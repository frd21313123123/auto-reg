# -*- coding: utf-8 -*-
"""
Кастомные виджеты — modern flat design
"""

import tkinter as tk


class HoverButton(tk.Button):
    """Кнопка с мягким переходом цветов при наведении."""

    def __init__(
        self,
        parent,
        hover_bg=None,
        hover_fg=None,
        animation_steps=6,
        animation_delay=16,
        **kwargs,
    ):
        kwargs.setdefault("relief", tk.FLAT)
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("cursor", "hand2")
        kwargs.setdefault("padx", 10)
        kwargs.setdefault("pady", 5)
        kwargs.setdefault("activebackground", hover_bg or kwargs.get("bg"))
        kwargs.setdefault("activeforeground", hover_fg or kwargs.get("fg"))
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self._normal_bg = kwargs.get("bg", self.cget("bg"))
        self._normal_fg = kwargs.get("fg", self.cget("fg"))
        self._hover_bg = hover_bg or self._normal_bg
        self._hover_fg = hover_fg or self._normal_fg
        self._hovered = False
        self._animation_job = None
        self._animation_steps = max(1, animation_steps)
        self._animation_delay = max(1, animation_delay)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _color_to_rgb(self, color):
        r, g, b = self.winfo_rgb(color)
        return r // 256, g // 256, b // 256

    @staticmethod
    def _rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*rgb)

    def _blend_color(self, start_color, end_color, progress):
        start_rgb = self._color_to_rgb(start_color)
        end_rgb = self._color_to_rgb(end_color)
        mixed = tuple(
            round(start + (end - start) * progress)
            for start, end in zip(start_rgb, end_rgb)
        )
        return self._rgb_to_hex(mixed)

    def _stop_animation(self):
        if self._animation_job is not None:
            try:
                self.after_cancel(self._animation_job)
            except Exception:
                pass
            self._animation_job = None

    def _animate_to(self, target_bg, target_fg):
        self._stop_animation()
        start_bg = self.cget("bg")
        start_fg = self.cget("fg")
        if start_bg == target_bg and start_fg == target_fg:
            self.config(
                bg=target_bg,
                fg=target_fg,
                activebackground=self._hover_bg,
                activeforeground=self._hover_fg,
            )
            return

        def run(frame):
            progress = frame / self._animation_steps
            eased = 1 - (1 - progress) ** 3
            self.config(
                bg=self._blend_color(start_bg, target_bg, eased),
                fg=self._blend_color(start_fg, target_fg, eased),
                activebackground=self._hover_bg,
                activeforeground=self._hover_fg,
            )
            if frame < self._animation_steps:
                self._animation_job = self.after(
                    self._animation_delay,
                    lambda: run(frame + 1),
                )
            else:
                self._animation_job = None

        run(0)

    def _on_enter(self, event):
        if self["state"] != tk.DISABLED:
            self._hovered = True
            self._animate_to(self._hover_bg, self._hover_fg)

    def _on_leave(self, event):
        if self["state"] != tk.DISABLED:
            self._hovered = False
            self._animate_to(self._normal_bg, self._normal_fg)

    def update_colors(self, bg=None, fg=None, hover_bg=None, hover_fg=None, immediate=True):
        """Обновить цвета кнопки для новой темы."""
        if bg is not None:
            self._normal_bg = bg
        if fg is not None:
            self._normal_fg = fg
        if hover_bg is not None:
            self._hover_bg = hover_bg
        if hover_fg is not None:
            self._hover_fg = hover_fg

        target_bg = self._hover_bg if self._hovered and self["state"] != tk.DISABLED else self._normal_bg
        target_fg = self._hover_fg if self._hovered and self["state"] != tk.DISABLED else self._normal_fg
        if immediate:
            self._stop_animation()
            self.config(
                bg=target_bg,
                fg=target_fg,
                activebackground=self._hover_bg,
                activeforeground=self._hover_fg,
            )
        else:
            self._animate_to(target_bg, target_fg)


class AnimatedToggle(tk.Canvas):
    """Анимированный переключатель (toggle switch) — modern pill-style."""

    def __init__(self, parent, on_toggle=None, width=48, height=26,
                 bg_on="#4f6df5", bg_off="#cbd5e0",
                 handle_color="#ffffff", handle_outline="#e2e8f0",
                 shadow_color="#d4d4d4"):
        super().__init__(parent, width=width, height=height, bd=0,
                         highlightthickness=0, cursor="hand2")
        self.on_toggle = on_toggle
        self.is_on = False
        self.w = width
        self.h = height
        self.bg_on = bg_on
        self.bg_off = bg_off
        self.r = height // 2

        self.p = 3
        self.d = height - 2 * self.p

        self.rect = self.create_oval(0, 0, height, height, outline="", fill=bg_off)
        self.rect2 = self.create_oval(width - height, 0, width, height, outline="", fill=bg_off)
        self.rect3 = self.create_rectangle(height / 2, 0, width - height / 2, height,
                                           outline="", fill=bg_off)
        self.shadow = self.create_oval(self.p + 1, self.p + 1,
                                       self.p + self.d + 1, self.p + self.d + 1,
                                       fill=shadow_color, outline="")
        self.handle = self.create_oval(self.p, self.p,
                                       self.p + self.d, self.p + self.d,
                                       fill=handle_color, outline=handle_outline)

        self.bind("<Button-1>", self.toggle)

    def update_colors(self, bg_on=None, bg_off=None,
                      handle_color=None, handle_outline=None, shadow_color=None):
        """Обновить цвета переключателя (для смены темы)."""
        if bg_on is not None:
            self.bg_on = bg_on
        if bg_off is not None:
            self.bg_off = bg_off
        bg_color = self.bg_on if self.is_on else self.bg_off
        self.itemconfig(self.rect, fill=bg_color)
        self.itemconfig(self.rect2, fill=bg_color)
        self.itemconfig(self.rect3, fill=bg_color)
        if handle_color is not None:
            self.itemconfig(self.handle, fill=handle_color)
        if handle_outline is not None:
            self.itemconfig(self.handle, outline=handle_outline)
        if shadow_color is not None:
            self.itemconfig(self.shadow, fill=shadow_color)

    def toggle(self, event=None):
        self.is_on = not self.is_on
        self.animate()
        if self.on_toggle:
            self.on_toggle(self.is_on)

    def set_state(self, is_on):
        self.is_on = is_on
        target_x = self.w - self.d - self.p if self.is_on else self.p
        bg_color = self.bg_on if self.is_on else self.bg_off
        current_x = self.coords(self.handle)[0]
        dx = target_x - current_x
        self.move(self.handle, dx, 0)
        self.move(self.shadow, dx, 0)
        self.itemconfig(self.rect, fill=bg_color)
        self.itemconfig(self.rect2, fill=bg_color)
        self.itemconfig(self.rect3, fill=bg_color)

    def animate(self):
        target_x = self.w - self.d - self.p if self.is_on else self.p
        bg_color = self.bg_on if self.is_on else self.bg_off

        current_x = self.coords(self.handle)[0]
        dist = target_x - current_x
        step = dist * 0.35

        if abs(dist) < 1:
            self.move(self.handle, dist, 0)
            self.move(self.shadow, dist, 0)
            self.itemconfig(self.rect, fill=bg_color)
            self.itemconfig(self.rect2, fill=bg_color)
            self.itemconfig(self.rect3, fill=bg_color)
            return

        self.move(self.handle, step, 0)
        self.move(self.shadow, step, 0)
        self.itemconfig(self.rect, fill=bg_color)
        self.itemconfig(self.rect2, fill=bg_color)
        self.itemconfig(self.rect3, fill=bg_color)
        self.after(12, self.animate)


class ThemedCheckbox(tk.Canvas):
    """Крупная стилизованная галочка."""

    def __init__(self, parent, on_toggle=None, size=24, checked=False):
        super().__init__(parent, width=size, height=size, bd=0,
                         highlightthickness=0, cursor="hand2")
        self.on_toggle = on_toggle
        self.size = size
        self.checked = checked
        self.colors = {
            "bg": "#ffffff",
            "border": "#cbd5e0",
            "box_bg": "#ffffff",
            "check": "#ffffff",
            "accent": "#4f6df5"
        }
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def set_theme(self, colors, accent_bg):
        self.colors["bg"] = colors["panel_bg"]
        self.colors["border"] = colors.get("border", colors["status_fg"])
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
        r = 4

        if self.checked:
            fill = self.colors["accent"]
            outline = self.colors["accent"]
        else:
            fill = self.colors["box_bg"]
            outline = self.colors["border"]

        self._round_rect(x0, y0, x1, y1, r, fill=fill, outline=outline, width=2)

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

    def _round_rect(self, x0, y0, x1, y1, r, **kwargs):
        """Рисует скругленный прямоугольник."""
        points = [
            x0 + r, y0,
            x1 - r, y0,
            x1, y0,
            x1, y0 + r,
            x1, y1 - r,
            x1, y1,
            x1 - r, y1,
            x0 + r, y1,
            x0, y1,
            x0, y1 - r,
            x0, y0 + r,
            x0, y0,
            x0 + r, y0,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)


class SectionLabel(tk.Frame):
    """Метка-разделитель секции с горизонтальной линией."""

    def __init__(self, parent, text, font=None, bg="#ffffff", fg="#718096",
                 line_color="#e2e8f0"):
        super().__init__(parent, bg=bg)
        self._bg = bg
        self._fg = fg
        self._line_color = line_color

        self.label = tk.Label(self, text=text, font=font, bg=bg, fg=fg)
        self.label.pack(side=tk.LEFT, padx=(0, 8))

        self.line = tk.Frame(self, bg=line_color, height=1)
        self.line.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=1)

    def update_colors(self, bg, fg, line_color):
        self._bg = bg
        self._fg = fg
        self._line_color = line_color
        self.config(bg=bg)
        self.label.config(bg=bg, fg=fg)
        self.line.config(bg=line_color)
