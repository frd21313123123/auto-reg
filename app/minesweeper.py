# -*- coding: utf-8 -*-
"""
Игра "Сапер" (Minesweeper)
"""

import tkinter as tk
from tkinter import messagebox
import random


class Minesweeper:
    """Класс игры Сапер"""
    
    def __init__(self, parent, theme_name="dark"):
        self.window = tk.Toplevel(parent)
        self.window.title("💣 Сапер")
        self.window.geometry("400x480")
        self.window.resizable(False, False)
        
        self.theme_name = theme_name
        self.rows = 10
        self.cols = 10
        self.mines = 15
        self.buttons = []
        self.board = []
        self.revealed = []
        self.flagged = []
        self.game_over = False
        self.first_click = True
        
        self.setup_ui()
        self.setup_board()
        
    def setup_ui(self):
        """Создание интерфейса"""
        bg_color = "#1e293b"
        fg_color = "#e2e8f0"
        header_bg = "#111827"
        
        self.window.config(bg=bg_color)
        
        # Заголовок с информацией
        self.header = tk.Frame(self.window, bg=header_bg, height=60)
        self.header.pack(fill=tk.X, padx=5, pady=5)
        
        self.mines_label = tk.Label(
            self.header, 
            text=f"💣 Мины: {self.mines}", 
            font=("Segoe UI", 11, "bold"),
            bg=header_bg, 
            fg=fg_color
        )
        self.mines_label.pack(side=tk.LEFT, padx=10)
        
        self.new_game_btn = tk.Button(
            self.header,
            text="🔄 Новая игра",
            command=self.reset_game,
            font=("Segoe UI", 10),
            bg="#3b82f6",
            fg="white",
            relief=tk.FLAT,
            padx=10,
            cursor="hand2"
        )
        self.new_game_btn.pack(side=tk.RIGHT, padx=10)
        
        # Игровое поле
        self.game_frame = tk.Frame(self.window, bg=bg_color)
        self.game_frame.pack(padx=10, pady=10)
        
        # Подсказка
        help_text = "ЛКМ - открыть | ПКМ - флаг"
        self.help_label = tk.Label(
            self.window,
            text=help_text,
            font=("Segoe UI", 9),
            bg=bg_color,
            fg=fg_color
        )
        self.help_label.pack(pady=5)
        
    def setup_board(self):
        """Создание игрового поля"""
        # Очищаем старые кнопки
        for row in self.buttons:
            for btn in row:
                btn.destroy()
        
        self.buttons = []
        self.board = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.revealed = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        self.flagged = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        
        # Цвета для кнопок
        btn_bg = "#334155"
        btn_fg = "#e2e8f0"
        btn_active = "#475569"
        
        # Создаем кнопки
        for i in range(self.rows):
            button_row = []
            for j in range(self.cols):
                btn = tk.Button(
                    self.game_frame,
                    text="",
                    width=3,
                    height=1,
                    font=("Segoe UI", 10, "bold"),
                    bg=btn_bg,
                    fg=btn_fg,
                    activebackground=btn_active,
                    relief=tk.RAISED,
                    bd=2
                )
                btn.grid(row=i, column=j, padx=1, pady=1)
                btn.bind("<Button-1>", lambda e, r=i, c=j: self.on_left_click(r, c))
                btn.bind("<Button-3>", lambda e, r=i, c=j: self.on_right_click(r, c))
                button_row.append(btn)
            self.buttons.append(button_row)
        
        self.game_over = False
        self.first_click = True
        
    def place_mines(self, exclude_row, exclude_col):
        """Размещение мин (исключая первую клетку)"""
        mines_placed = 0
        while mines_placed < self.mines:
            row = random.randint(0, self.rows - 1)
            col = random.randint(0, self.cols - 1)
            
            # Не ставим мину на первую клетку и рядом с ней
            if abs(row - exclude_row) <= 1 and abs(col - exclude_col) <= 1:
                continue
            
            if self.board[row][col] != -1:
                self.board[row][col] = -1
                mines_placed += 1
        
        # Подсчет чисел вокруг мин
        for i in range(self.rows):
            for j in range(self.cols):
                if self.board[i][j] == -1:
                    continue
                count = 0
                for di in [-1, 0, 1]:
                    for dj in [-1, 0, 1]:
                        ni, nj = i + di, j + dj
                        if 0 <= ni < self.rows and 0 <= nj < self.cols:
                            if self.board[ni][nj] == -1:
                                count += 1
                self.board[i][j] = count
    
    def on_left_click(self, row, col):
        """Обработка левого клика"""
        if self.game_over or self.revealed[row][col] or self.flagged[row][col]:
            return
        
        # Первый клик - размещаем мины
        if self.first_click:
            self.place_mines(row, col)
            self.first_click = False
        
        # Попали на мину
        if self.board[row][col] == -1:
            self.game_over = True
            self.reveal_all()
            self.buttons[row][col].config(bg="#ef4444", text="💣")
            messagebox.showinfo("Сапер", "💥 БУМ! Вы проиграли!")
            return
        
        # Открываем клетку
        self.reveal_cell(row, col)
        
        # Проверяем победу
        if self.check_win():
            self.game_over = True
            messagebox.showinfo("Сапер", "🎉 Поздравляем! Вы выиграли!")
    
    def on_right_click(self, row, col):
        """Обработка правого клика (флаг)"""
        if self.game_over or self.revealed[row][col]:
            return
        
        if self.flagged[row][col]:
            self.flagged[row][col] = False
            self.buttons[row][col].config(text="")
        else:
            self.flagged[row][col] = True
            self.buttons[row][col].config(text="🚩", fg="#ef4444")
    
    def reveal_cell(self, row, col):
        """Открытие клетки"""
        if self.revealed[row][col] or self.flagged[row][col]:
            return
        
        self.revealed[row][col] = True
        
        # Цвета для чисел
        number_colors = {
            1: "#2563eb", 2: "#16a34a", 3: "#dc2626",
            4: "#7c3aed", 5: "#ea580c", 6: "#0891b2",
            7: "#000000", 8: "#6b7280"
        }
        
        bg_revealed = "#475569"
        
        value = self.board[row][col]
        
        if value == 0:
            self.buttons[row][col].config(
                text="",
                relief=tk.FLAT,
                bg=bg_revealed,
                state=tk.DISABLED
            )
            # Рекурсивно открываем соседние клетки
            for di in [-1, 0, 1]:
                for dj in [-1, 0, 1]:
                    ni, nj = row + di, col + dj
                    if 0 <= ni < self.rows and 0 <= nj < self.cols:
                        if not self.revealed[ni][nj]:
                            self.reveal_cell(ni, nj)
        else:
            color = number_colors.get(value, "#111827")
            self.buttons[row][col].config(
                text=str(value),
                fg=color,
                relief=tk.FLAT,
                bg=bg_revealed,
                state=tk.DISABLED
            )
    
    def reveal_all(self):
        """Открыть все клетки (конец игры)"""
        for i in range(self.rows):
            for j in range(self.cols):
                if self.board[i][j] == -1:
                    bg = "#ef4444" if self.revealed[i][j] else "#fca5a5"
                    self.buttons[i][j].config(text="💣", bg=bg)
                elif self.flagged[i][j] and self.board[i][j] != -1:
                    self.buttons[i][j].config(bg="#fbbf24", text="❌")
    
    def check_win(self):
        """Проверка победы"""
        for i in range(self.rows):
            for j in range(self.cols):
                if self.board[i][j] != -1 and not self.revealed[i][j]:
                    return False
        return True
    
    def reset_game(self):
        """Новая игра"""
        self.setup_board()


def show_minesweeper(parent, theme_name="dark"):
    """Открыть окно игры Сапер"""
    Minesweeper(parent, theme_name)
