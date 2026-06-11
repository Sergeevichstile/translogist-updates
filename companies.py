import tkinter as tk
from tkinter import messagebox
from .ui_helpers import *


class CompaniesFrame(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=BG)
        self.db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG, padx=24, pady=14)
        hdr.pack(fill="x")
        label(hdr, "🏦 Реквизиты компаний", size=16, bold=True, bg=BG).pack(side="left")
        btn(hdr, "+ Добавить компанию", self._add, color=ACCENT).pack(side="right")

        # Active company banner
        self.banner = tk.Frame(self, bg="#1e3a1e", padx=20, pady=10)
        self.banner.pack(fill="x", padx=24, pady=(0,8))
        self.banner_label = label(self.banner, "Активная компания: —",
                                   bg="#1e3a1e", color="#86efac", size=11)
        self.banner_label.pack(side="left")
        btn(self.banner, "✏️  Сменить активную", self._set_active,
            color="#166534", fg="#86efac").pack(side="right")

        wrap = tk.Frame(self, bg=BG, padx=24)
        wrap.pack(fill="both", expand=True)

        tbl, self.tree = make_table(wrap,
            ["✓", "Название", "ИНН", "КПП", "ОГРН", "Директор", "Банк", "Р/С", ""],
            [30, 200, 110, 90, 120, 160, 160, 160, 50])
        tbl.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._edit)

        self.menu = tk.Menu(self, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT)
        self.menu.add_command(label="✅  Сделать активной", command=self._set_active)
        self.menu.add_command(label="✏️  Редактировать",    command=self._edit)
        self.menu.add_command(label="🗑️  Удалить",          command=self._delete)
        self.tree.bind("<Button-3>", self._ctx)

    def _add(self):
        CompanyDialog(self, self.db, on_save=self.refresh)

    def _edit(self, e=None):
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0])["values"][1]
        co = next((c for c in self.db.get_all("companies") if c.get("name") == name), None)
        if co:
            CompanyDialog(self, self.db, company=co, on_save=self.refresh)

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0])["values"][1]
        co = next((c for c in self.db.get_all("companies") if c.get("name") == name), None)
        if not co: return
        if co.get("active"):
            messagebox.showwarning("Нельзя", "Нельзя удалить активную компанию.\nСначала выберите другую активной.")
            return
        if messagebox.askyesno("Удалить", f"Удалить {name}?"):
            self.db.delete("companies", co["id"])
            self.refresh()

    def _set_active(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Выберите", "Кликните на компанию в таблице")
            return
        name = self.tree.item(sel[0])["values"][1]
        self.db.set_active_company_by_name(name)
        self.refresh()

    def _ctx(self, e):
        row = self.tree.identify_row(e.y)
        if row:
            self.tree.selection_set(row)
            self.menu.post(e.x_root, e.y_root)

    def refresh(self):
        if not self.winfo_ismapped(): return
        active = self.db.get_active_company()
        name = active.get("name", "—") if active else "—"
        self.banner_label.config(text=f"Активная компания: {name}  |  ИНН: {active.get('inn','') if active else ''}")

        for row in self.tree.get_children():
            self.tree.delete(row)
        for co in self.db.get_all("companies"):
            mark = "✅" if co.get("active") else ""
            self.tree.insert("", "end", values=(
                mark,
                co.get("name", ""),
                co.get("inn", ""),
                co.get("kpp", ""),
                co.get("ogrn", ""),
                co.get("director", ""),
                co.get("bank", ""),
                co.get("rs", ""),
                "✏️"
            ))


class CompanyDialog(tk.Toplevel):
    def __init__(self, parent, db, company=None, on_save=None):
        super().__init__(parent)
        self.db = db
        self.company = company
        self.on_save = on_save
        self.title("Компания")
        self.geometry("540x600")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        from .inn_widget import INNWidget
        ci = self.company or {}

        # INN search at top
        inn_row = tk.Frame(self, bg=BG)
        inn_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(12,4))
        self.inn_widget = INNWidget(inn_row, self.db, on_found=self._fill_from_inn)
        self.inn_widget.pack(side="left")
        if ci.get("inn"):
            self.inn_widget.set_inn(ci["inn"])
        tk.Frame(self, bg=BORDER, height=1).grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=4)
        self._row_offset = 2
        fields = [
            ("Название организации:", "name"),
            ("ИНН:", "inn"),
            ("КПП:", "kpp"),
            ("ОГРН:", "ogrn"),
            ("Юридический адрес:", "address"),
            ("Фактический адрес:", "address_fact"),
            ("Директор (ФИО):", "director"),
            ("Телефон:", "phone"),
            ("Email:", "email"),
            ("Банк:", "bank"),
            ("Расчётный счёт:", "rs"),
            ("БИК:", "bik"),
            ("Корр. счёт:", "ks"),
        ]
        self.entries = {}

        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))

        for i, (lbl_text, key) in enumerate(fields):
            label(inner, lbl_text, bg=BG, size=10).grid(
                row=i, column=0, sticky="w", padx=20, pady=5)
            e = entry(inner, width=30)
            e.insert(0, ci.get(key, ""))
            e.grid(row=i, column=1, padx=20, pady=5)
            self.entries[key] = e

        n = len(fields)
        self.make_active_var = tk.BooleanVar(value=ci.get("active", False))
        tk.Checkbutton(inner, text="Сделать активной (используется в документах)",
                       variable=self.make_active_var,
                       bg=BG, fg=TEXT, selectcolor=CARD,
                       activebackground=BG, font=("Arial", 10)).grid(
            row=n, column=0, columnspan=2, sticky="w", padx=20, pady=8)

        btn(inner, "💾 Сохранить", self._save, color=SUCCESS).grid(
            row=n+1, column=0, columnspan=2, pady=12)

    def _fill_from_inn(self, info):
        """Auto-fill company fields from INN lookup."""
        for info_key, field_key in [
            ("name","name"), ("inn","inn"), ("kpp","kpp"),
            ("ogrn","ogrn"), ("address","address"), ("director","director")
        ]:
            if info.get(info_key) and field_key in self.entries:
                self.entries[field_key].delete(0, "end")
                self.entries[field_key].insert(0, info[info_key])
        if info.get("inn"):
            self.inn_widget.set_inn(info["inn"])

    def _save(self):
        data = {k: e.get().strip() for k, e in self.entries.items()}
        if not data.get("name"):
            messagebox.showerror("Ошибка", "Введите название компании")
            return
        make_active = self.make_active_var.get()

        if self.company:
            data["active"] = self.company.get("active", False)
            self.db.update("companies", self.company["id"], data)
            if make_active:
                self.db.set_active_company_by_name(data["name"])
        else:
            data["active"] = False
            co = self.db.add("companies", data)
            if make_active:
                self.db.set_active_company_by_name(data["name"])

        if self.on_save:
            self.on_save()
        self.destroy()
