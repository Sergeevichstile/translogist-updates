import tkinter as tk
from tkinter import messagebox
from .ui_helpers import *


class CounterpartiesFrame(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=BG)
        self.db = db
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG, padx=24, pady=14)
        hdr.pack(fill="x")
        label(hdr, "🏢 Контрагенты и Перевозчики", size=16, bold=True, bg=BG).pack(side="left")

        tab_frame = tk.Frame(self, bg=BG, padx=24)
        tab_frame.pack(fill="x")
        self.active_tab = tk.StringVar(value="counterparties")

        self.tab_btns = {}
        for key, title in [("counterparties", "Контрагенты (Клиенты)"), ("carriers", "Перевозчики (Чужие фуры)")]:
            b = tk.Button(tab_frame, text=title,
                          bg=ACCENT if key == "counterparties" else CARD,
                          fg=WHITE, relief="flat", padx=16, pady=8,
                          font=("Arial", 10, "bold"), cursor="hand2",
                          command=lambda k=key: self._switch_tab(k))
            b.pack(side="left", padx=(0, 4))
            self.tab_btns[key] = b

        self.cp_frame = tk.Frame(self, bg=BG, padx=24)
        self._build_cp()

        self.car_frame = tk.Frame(self, bg=BG, padx=24)
        self._build_carriers()

        self.cp_frame.pack(fill="both", expand=True)

    def _switch_tab(self, key):
        self.active_tab.set(key)
        for k, b in self.tab_btns.items():
            b.configure(bg=ACCENT if k == key else CARD)
        if key == "counterparties":
            self.car_frame.pack_forget()
            self.cp_frame.pack(fill="both", expand=True)
        else:
            self.cp_frame.pack_forget()
            self.car_frame.pack(fill="both", expand=True)
        self.refresh()

    def _build_cp(self):
        add_btn = btn(self.cp_frame, "+ Добавить контрагента",
                      command=lambda: CounterpartyDialog(self, self.db, "counterparties", on_save=self.refresh))
        add_btn.pack(anchor="e", pady=(8, 8))

        tbl, self.cp_tree = make_table(
            self.cp_frame,
            ["Название", "ИНН", "КПП", "Контактное лицо", "Телефон", "Email", "НДС", ""],
            [200, 120, 90, 140, 130, 160, 60, 50]
        )
        tbl.pack(fill="both", expand=True)
        self.cp_tree.bind("<Double-1>", lambda e: self._edit("counterparties", self.cp_tree))
        self.cp_tree.bind("<Button-3>", lambda e: self._ctx(e, "counterparties", self.cp_tree))

    def _build_carriers(self):
        add_btn = btn(self.car_frame, "+ Добавить перевозчика",
                      command=lambda: CounterpartyDialog(self, self.db, "carriers", on_save=self.refresh))
        add_btn.pack(anchor="e", pady=(8, 8))

        tbl, self.car_tree = make_table(
            self.car_frame,
            ["Название", "ИНН", "Контакт", "Телефон", "Ставка ₽/рейс", "НДС", ""],
            [200, 120, 160, 130, 130, 60, 50]
        )
        tbl.pack(fill="both", expand=True)
        self.car_tree.bind("<Double-1>", lambda e: self._edit("carriers", self.car_tree))
        self.car_tree.bind("<Button-3>", lambda e: self._ctx(e, "carriers", self.car_tree))

    def _edit(self, table, tree):
        sel = tree.selection()
        if not sel: return
        name = tree.item(sel[0])["values"][0]
        rec = next((r for r in self.db.get_all(table) if r.get("name") == name), None)
        if rec:
            CounterpartyDialog(self, self.db, table, record=rec, on_save=self.refresh)

    def _ctx(self, event, table, tree):
        row = tree.identify_row(event.y)
        if row:
            tree.selection_set(row)
            m = tk.Menu(self, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT)
            m.add_command(label="✏️  Редактировать", command=lambda: self._edit(table, tree))
            m.add_command(label="🗑️  Удалить", command=lambda: self._delete(table, tree))
            m.post(event.x_root, event.y_root)

    def _delete(self, table, tree):
        sel = tree.selection()
        if not sel: return
        name = tree.item(sel[0])["values"][0]
        rec = next((r for r in self.db.get_all(table) if r.get("name") == name), None)
        if rec and messagebox.askyesno("Удалить", f"Удалить {name}?"):
            self.db.delete(table, rec["id"])
            self.refresh()

    def refresh(self):
        if not self.winfo_ismapped(): return
        for row in self.cp_tree.get_children():
            self.cp_tree.delete(row)
        for c in self.db.get_all("counterparties"):
            self.cp_tree.insert("", "end", values=(
                c.get("name", ""), c.get("inn", ""), c.get("kpp",""),
                c.get("contact", ""), c.get("phone", ""), c.get("email", ""),
                "Да" if c.get("vat") else "Нет", "✏️"
            ))
        for row in self.car_tree.get_children():
            self.car_tree.delete(row)
        for c in self.db.get_all("carriers"):
            self.car_tree.insert("", "end", values=(
                c.get("name", ""), c.get("inn", ""), c.get("contact", ""),
                c.get("phone", ""), f"{c.get('rate', 0):,.0f}",
                "Да" if c.get("vat") else "Нет", "✏️"
            ))


class CounterpartyDialog(tk.Toplevel):
    def __init__(self, parent, db, table, record=None, on_save=None):
        super().__init__(parent)
        self.db = db
        self.table = table
        self.record = record
        self.on_save = on_save
        title = "Перевозчик" if table == "carriers" else "Контрагент"
        self.title(title)
        self.geometry("540x600")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        from .inn_widget import INNWidget
        ci = self.record or {}

        # INN search row at top
        label(self, "🔍 Автозаполнение по ИНН:", bold=True, bg=BG, size=11).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(14,4))

        inn_row = tk.Frame(self, bg=BG)
        inn_row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0,6))
        self.inn_widget = INNWidget(inn_row, self.db, on_found=self._fill_from_inn)
        self.inn_widget.pack(side="left")
        if ci.get("inn"):
            self.inn_widget.set_inn(ci["inn"])

        tk.Frame(self, bg=BORDER, height=1).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=4)

        fields = [
            ("Название организации:", "name"),
            ("ИНН:", "inn"),
            ("КПП:", "kpp"),
            ("Контактное лицо:", "contact"),
            ("Телефон:", "phone"),
            ("Email:", "email"),
            ("Адрес:", "address"),
        ]
        if self.table == "carriers":
            fields.append(("Ставка ₽/рейс:", "rate"))

        self.entries = {}
        for i, (lbl_text, key) in enumerate(fields):
            label(self, lbl_text, bg=BG, size=10).grid(
                row=i+3, column=0, sticky="w", padx=20, pady=4)
            e = entry(self, width=28)
            e.grid(row=i+3, column=1, padx=20, pady=4)
            if self.record:
                e.insert(0, str(self.record.get(key, "")))
            self.entries[key] = e

        n = len(fields) + 3
        label(self, "Плательщик НДС:", bg=BG).grid(row=n, column=0, sticky="w", padx=20, pady=5)
        self.vat_var = tk.BooleanVar(value=self.record.get("vat", False) if self.record else False)
        tk.Checkbutton(self, variable=self.vat_var, bg=BG, fg=TEXT,
                       selectcolor=CARD, activebackground=BG).grid(row=n, column=1, sticky="w", padx=20)

        btn(self, "💾 Сохранить", self._save, color=SUCCESS).grid(
            row=n+1, column=0, columnspan=2, pady=16)

    def _fill_from_inn(self, info):
        for info_key, field_key in [
            ("name","name"), ("inn","inn"), ("kpp","kpp"), ("address","address")
        ]:
            if info.get(info_key) and field_key in self.entries:
                self.entries[field_key].delete(0, "end")
                self.entries[field_key].insert(0, info[info_key])
        if info.get("inn"):
            self.inn_widget.set_inn(info["inn"])

    def _save(self):
        data = {k: e.get().strip() for k, e in self.entries.items()}
        data["vat"] = self.vat_var.get()
        if "rate" in data:
            try:
                data["rate"] = float(data["rate"].replace(",", "."))
            except Exception:
                data["rate"] = 0
        if not data.get("name"):
            messagebox.showerror("Ошибка", "Введите название")
            return
        if self.record:
            self.db.update(self.table, self.record["id"], data)
        else:
            self.db.add(self.table, data)
        if self.on_save:
            self.on_save()
        self.destroy()
