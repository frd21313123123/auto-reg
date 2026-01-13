# -*- coding: utf-8 -*-
"""
Mail.tm — регистрация и почтовый клиент
Точка входа приложения
"""

import tkinter as tk
from mail_app import MailApp


def main():
    """Запуск приложения"""
    root = tk.Tk()
    app = MailApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
