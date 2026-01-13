# -*- coding: utf-8 -*-
"""
Settings window for hotkeys configuration.
"""

import tkinter as tk
from tkinter import messagebox
import json
import os
import keyboard

from .themes import THEMES

# Path for settings file
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hotkeys.json")

# Default hotkeys
DEFAULT_HOTKEYS = {
    "card": "ctrl+1",
    "name": "ctrl+2", 
    "city": "ctrl+3",
    "street": "ctrl+4",
    "postcode": "ctrl+5"
}

# Labels for hotkeys
HOTKEY_LABELS = {
    "card": "Номер карты",
    "name": "Имя",
    "city": "Город",
    "street": "Улица",
    "postcode": "Индекс"
}


class HotkeySettings:
    """Manager for hotkey settings."""
    
    _instance = None
    _hotkeys = None
    _callbacks = {}
    _registered = False
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self._hotkeys = self.load_hotkeys()
    
    def load_hotkeys(self):
        """Load hotkeys from file."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return DEFAULT_HOTKEYS.copy()
    
    def save_hotkeys(self, hotkeys):
        """Save hotkeys to file."""
        self._hotkeys = hotkeys
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(hotkeys, f, indent=2)
        except Exception as e:
            print(f"Error saving hotkeys: {e}")
    
    def get_hotkeys(self):
        """Get current hotkeys."""
        return self._hotkeys.copy()
    
    def set_callback(self, key, callback):
        """Set callback for a hotkey."""
        self._callbacks[key] = callback
    
    def register_all(self):
        """Register all hotkeys."""
        if self._registered:
            self.unregister_all()
        
        for key, hotkey in self._hotkeys.items():
            if hotkey and key in self._callbacks:
                try:
                    keyboard.add_hotkey(hotkey, self._callbacks[key], suppress=True)
                except Exception as e:
                    print(f"Error registering hotkey {hotkey}: {e}")
        
        self._registered = True
    
    def unregister_all(self):
        """Unregister all hotkeys."""
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        self._registered = False


def show_settings_window(parent, theme_name="light", on_save=None):
    """Open hotkey settings window."""
    win = tk.Toplevel(parent)
    win.title("⚙ Настройки горячих клавиш")
    win.geometry("400x350")
    win.resizable(False, False)
    
    colors = THEMES[theme_name]
    accent_bg = colors.get("accent", "#2563eb")
    accent_fg = colors.get("accent_fg", "#ffffff")
    win.config(bg=colors["bg"])
    
    settings = HotkeySettings.get_instance()
    current_hotkeys = settings.get_hotkeys()
    
    # Title
    title_lbl = tk.Label(
        win, 
        text="Настройки горячих клавиш",
        font=("Segoe UI", 12, "bold"),
        bg=colors["bg"],
        fg=colors["fg"]
    )
    title_lbl.pack(pady=(15, 5))
    
    hint_lbl = tk.Label(
        win,
        text="Нажмите на поле и введите комбинацию клавиш",
        font=("Segoe UI", 9),
        bg=colors["bg"],
        fg=colors.get("status_fg", "#888")
    )
    hint_lbl.pack(pady=(0, 10))
    
    # Frame for hotkey entries
    frame = tk.Frame(win, bg=colors["bg"])
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    entries = {}
    recording_entry = {"current": None, "key": None}
    
    def start_recording(entry, key):
        """Start recording hotkey when entry is clicked."""
        if recording_entry["current"]:
            # Stop previous recording
            try:
                keyboard.unhook_all()
            except Exception:
                pass
        
        recording_entry["current"] = entry
        recording_entry["key"] = key
        entry.delete(0, tk.END)
        entry.insert(0, "Нажмите...")
        entry.config(fg="#888")
        
        def on_hotkey(event):
            hotkey_str = keyboard.read_hotkey(suppress=False)
            if hotkey_str:
                entry.delete(0, tk.END)
                entry.insert(0, hotkey_str)
                entry.config(fg=colors.get("entry_fg", "#000000"))
            recording_entry["current"] = None
            recording_entry["key"] = None
            try:
                keyboard.unhook_all()
            except Exception:
                pass
        
        # Use keyboard library to capture the hotkey
        win.after(100, lambda: capture_with_keyboard(entry))
    
    def capture_with_keyboard(entry):
        """Capture hotkey using keyboard library."""
        try:
            hotkey = keyboard.read_hotkey(suppress=False)
            if hotkey:
                entry.delete(0, tk.END)
                entry.insert(0, hotkey)
                entry.config(fg=colors.get("entry_fg", "#000000"))
        except Exception as e:
            print(f"Error capturing hotkey: {e}")
        finally:
            recording_entry["current"] = None
            win.focus_set()
    
    row = 0
    for key, label in HOTKEY_LABELS.items():
        lbl = tk.Label(frame, text=f"{label}:", font=("Segoe UI", 10), bg=colors["bg"], fg=colors["fg"])
        lbl.grid(row=row, column=0, sticky="w", pady=5)
        
        entry = tk.Entry(
            frame, 
            font=("Segoe UI", 10), 
            width=20,
            bg=colors.get("entry_bg", "#ffffff"),
            fg=colors.get("entry_fg", "#000000")
        )
        entry.insert(0, current_hotkeys.get(key, ""))
        entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
        
        # Button to record hotkey
        btn_record = tk.Button(
            frame,
            text="🎤",
            command=lambda e=entry, k=key: start_recording(e, k),
            bg=colors.get("btn_bg", "#e0e0e0"),
            fg=colors.get("btn_fg", "#000000"),
            width=3
        )
        btn_record.grid(row=row, column=2, padx=2, pady=5)
        
        entries[key] = entry
        row += 1
    
    frame.columnconfigure(1, weight=1)
    
    # Buttons frame
    btn_frame = tk.Frame(win, bg=colors["bg"])
    btn_frame.pack(pady=20)
    
    def save_settings():
        new_hotkeys = {}
        for key, entry in entries.items():
            value = entry.get().strip()
            if value and value != "Нажмите клавиши...":
                new_hotkeys[key] = value
            else:
                new_hotkeys[key] = ""
        
        settings.save_hotkeys(new_hotkeys)
        
        if on_save:
            on_save(new_hotkeys)
        
        messagebox.showinfo("Сохранено", "Настройки горячих клавиш сохранены!")
        win.destroy()
    
    def reset_defaults():
        for key, entry in entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, DEFAULT_HOTKEYS.get(key, ""))
    
    btn_save = tk.Button(
        btn_frame,
        text="💾 Сохранить",
        command=save_settings,
        bg=accent_bg,
        fg=accent_fg,
        font=("Segoe UI", 10, "bold"),
        padx=15,
        relief=tk.FLAT
    )
    btn_save.pack(side=tk.LEFT, padx=5)
    
    btn_reset = tk.Button(
        btn_frame,
        text="↺ По умолчанию",
        command=reset_defaults,
        bg=colors.get("btn_bg", "#e0e0e0"),
        fg=colors.get("btn_fg", "#000000"),
        font=("Segoe UI", 10),
        padx=15,
        relief=tk.FLAT
    )
    btn_reset.pack(side=tk.LEFT, padx=5)
    
    btn_cancel = tk.Button(
        btn_frame,
        text="Отмена",
        command=win.destroy,
        bg=colors.get("btn_bg", "#e0e0e0"),
        fg=colors.get("btn_fg", "#000000"),
        font=("Segoe UI", 10),
        padx=15,
        relief=tk.FLAT
    )
    btn_cancel.pack(side=tk.LEFT, padx=5)
