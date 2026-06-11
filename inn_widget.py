"""
Reusable INN lookup widget.
Shows INN field with 🔍 button that auto-fills company data.
"""
import tkinter as tk
from .ui_helpers import *
from .inn_lookup import lookup_inn, get_saved_token


class INNWidget(tk.Frame):
    """
    INN input with auto-lookup button.
    Usage:
        w = INNWidget(parent, db, on_found=callback)
        w.pack(fill="x")
        inn = w.get_inn()
    """
    def __init__(self, parent, db, on_found=None, **kw):
        super().__init__(parent, bg=parent["bg"], **kw)
        self.db = db
        self.on_found = on_found
        self._build()

    def _build(self):
        label(self, "ИНН:", bg=self["bg"], size=10).pack(side="left", padx=(0, 6))
        self.inn_e = entry(self, width=16)
        self.inn_e.pack(side="left", padx=(0, 4))
        self.inn_e.bind("<Return>", lambda e: self._lookup())
        self.inn_e.bind("<FocusOut>", lambda e: self._auto_lookup())

        self.btn = tk.Button(self, text="🔍 Найти по ИНН",
                             bg="#1e3a5f", fg="#60a5fa",
                             relief="flat", font=("Segoe UI", 9),
                             cursor="hand2", padx=8, pady=3,
                             command=self._lookup)
        self.btn.pack(side="left")

        self.status = tk.Label(self, text="", bg=self["bg"],
                               fg=MUTED, font=("Segoe UI", 9))
        self.status.pack(side="left", padx=6)

    def get_inn(self):
        return self.inn_e.get().strip()

    def set_inn(self, inn):
        self.inn_e.delete(0, "end")
        self.inn_e.insert(0, inn)

    def _auto_lookup(self):
        inn = self.get_inn()
        if len(inn) in (10, 12):  # Valid INN length
            self._lookup()

    def _lookup(self):
        inn = self.get_inn()
        if not inn:
            return

        token = get_saved_token(self.db)
        if not token:
            # Show token setup dialog
            TokenSetupDialog(self, self.db, on_save=lambda: self._lookup())
            return

        self.status.config(text="⏳ Поиск...", fg=WARN)
        self.btn.config(state="disabled")

        def _cb(result):
            self.after(0, lambda: self._on_result(result))

        lookup_inn(inn, token, _cb)

    def _on_result(self, result):
        self.btn.config(state="normal")
        if result is None:
            self.status.config(text="❌ Не найдено", fg=DANGER)
            return
        if "error" in result:
            self.status.config(text=f"❌ {result['error']}", fg=DANGER)
            return
        self.status.config(text=f"✅ {result.get('name','')[:30]}", fg=SUCCESS)
        if self.on_found:
            self.on_found(result)


class TokenSetupDialog(tk.Toplevel):
    """Dialog to enter DaData API token."""
    def __init__(self, parent, db, on_save=None):
        super().__init__(parent)
        self.db = db
        self.on_save = on_save
        self.title("Настройка поиска по ИНН")
        self.geometry("500x320")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        label(self, "🔑 Настройка автозаполнения по ИНН", bold=True,
              bg=BG, size=13).pack(padx=20, pady=(16, 8), anchor="w")

        # Info
        info = tk.Frame(self, bg="#0f2d1f", padx=14, pady=10)
        info.pack(fill="x", padx=20, pady=(0, 12))
        label(info, "Используется бесплатный сервис DaData (500 запросов/день).",
              bg="#0f2d1f", color="#86efac", size=10).pack(anchor="w")
        label(info, "1. Зарегистрируйтесь на dadata.ru", bg="#0f2d1f",
              color="#86efac", size=10).pack(anchor="w")
        label(info, "2. Скопируйте API ключ из личного кабинета", bg="#0f2d1f",
              color="#86efac", size=10).pack(anchor="w")
        label(info, "3. Вставьте ключ ниже и нажмите Сохранить", bg="#0f2d1f",
              color="#86efac", size=10).pack(anchor="w")

        label(self, "API ключ DaData:", bg=BG, size=10).pack(
            anchor="w", padx=20, pady=(0, 4))
        self.token_e = entry(self, width=44)
        self.token_e.pack(fill="x", padx=20)

        # Pre-fill if exists
        existing = get_saved_token(self.db)
        if existing:
            self.token_e.insert(0, existing)

        self.status = tk.Label(self, text="", bg=BG, fg=DANGER,
                               font=("Segoe UI", 9))
        self.status.pack(pady=4)

        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=10)
        btn(btn_row, "💾 Сохранить", self._save, color=SUCCESS).pack(side="left")
        btn(btn_row, "Открыть dadata.ru", self._open_dadata,
            color=CARD).pack(side="left", padx=8)
        btn(btn_row, "Отмена", self.destroy, color=CARD).pack(side="right")

    def _open_dadata(self):
        import subprocess
        subprocess.Popen(["start", "https://dadata.ru/profile/#info"], shell=True)

    def _save(self):
        token = self.token_e.get().strip()
        if not token:
            self.status.config(text="Введите API ключ")
            return
        from .inn_lookup import save_token
        save_token(self.db, token)
        self.status.config(text="✅ Сохранено!", fg=SUCCESS)
        if self.on_save:
            self.after(500, self.on_save)
        self.after(800, self.destroy)
