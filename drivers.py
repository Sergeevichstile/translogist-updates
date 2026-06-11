import tkinter as tk
from tkinter import messagebox
from .ui_helpers import *


class DriversFrame(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=BG)
        self.db = db
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG, padx=24, pady=14)
        hdr.pack(fill="x")
        label(hdr, "👤 Водители", size=16, bold=True, bg=BG).pack(side="left")
        btn(hdr, "+ Добавить водителя", self._add).pack(side="right")
        btn(hdr, "🗑️ Удалить", self._delete, color=DANGER).pack(side="right", padx=(0,8))

        sf = tk.Frame(self, bg=BG, padx=24)
        sf.pack(fill="x", pady=(0,8))
        label(sf, "🔍", bg=BG, size=12).pack(side="left", padx=(0,6))
        se = entry(sf, width=30, textvariable=self.search_var)
        se.pack(side="left")
        se.insert(0, "Поиск по имени, телефону...")
        se.bind("<FocusIn>", lambda e: se.delete(0,"end") if "..." in se.get() else None)

        self.stats_frame = tk.Frame(self, bg=BG, padx=24)
        self.stats_frame.pack(fill="x", pady=(0,8))

        wrap = tk.Frame(self, bg=BG, padx=24)
        wrap.pack(fill="both", expand=True)

        tbl, self.tree = make_table(wrap,
            ["ФИО","Телефон","Вод. удост.","Ставка (₽/км)","Категория","Фура","Статус","Рейсов",""],
            [180,130,120,110,80,110,90,70,50])
        tbl.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._edit)

        self.menu = tk.Menu(self, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT)
        self.menu.add_command(label="✏️  Редактировать",       command=self._edit)
        self.menu.add_command(label="🚛  Привязать фуру",      command=self._assign_truck)
        self.menu.add_command(label="💰  Выплатить зарплату",  command=self._pay_salary)
        self.menu.add_command(label="🗑️  Удалить",             command=self._delete)
        self.tree.bind("<Button-3>", self._show_menu)

    def _add(self):  DriverDialog(self, self.db, on_save=self.refresh)

    def _edit(self, e=None):
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0])["values"][0]
        drv = next((d for d in self.db.get_all("drivers") if d.get("name")==name), None)
        if drv: DriverDialog(self, self.db, driver=drv, on_save=self.refresh)

    def _assign_truck(self):
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0])["values"][0]
        drv = next((d for d in self.db.get_all("drivers") if d.get("name")==name), None)
        if drv: AssignTruckDialog(self, self.db, drv, on_save=self.refresh)

    def _pay_salary(self):
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0])["values"][0]
        drv = next((d for d in self.db.get_all("drivers") if d.get("name")==name), None)
        if drv: SalaryDialog(self, self.db, drv, on_save=self.refresh)

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        name = self.tree.item(sel[0])["values"][0]
        drv = next((d for d in self.db.get_all("drivers") if d.get("name")==name), None)
        if drv and messagebox.askyesno("Удалить",f"Удалить {name}?"):
            self.db.delete("drivers", drv["id"]); self.refresh()

    def _show_menu(self, e):
        row = self.tree.identify_row(e.y)
        if row:
            self.tree.selection_set(row)
            self.menu.post(e.x_root, e.y_root)

    def refresh(self):
        if not self.winfo_ismapped(): return
        q = self.search_var.get().lower()
        if "..." in q: q = ""

        for w in self.stats_frame.winfo_children(): w.destroy()
        drivers = self.db.get_all("drivers")
        active  = sum(1 for d in drivers if d.get("status") == "Активен")
        trips   = self.db.get_all("trips")

        # Trip count per driver
        trip_count_map = {}
        for t in trips:
            did = t.get("driver_id","")
            if did: trip_count_map[did] = trip_count_map.get(did,0)+1

        # Salary fund calculation
        salary_fund = 0
        for d in drivers:
            d_trips = [t for t in trips if t.get("driver_id") == d["id"]]
            if d.get("rate_type","km") == "km" and d.get("rate",0):
                km_total = sum(t.get("distance",0) or 0 for t in d_trips)
                salary_fund += km_total * d["rate"]
            else:
                salary_fund += len(d_trips) * (d.get("rate",0) or 0)

        for title, val, color in [
            ("Всего водителей", str(len(drivers)),        TEXT),
            ("Активных",        str(active),              SUCCESS),
            ("ФЗП (рейсы)",     f"{salary_fund:,.0f} ₽", WARN),
        ]:
            metric_card(self.stats_frame, title, val, color).pack(side="left", padx=(0,10))

        trk_map = {t["id"]: t.get("plate","") for t in self.db.get_all("trucks")}

        for row in self.tree.get_children(): self.tree.delete(row)
        for d in drivers:
            if q and q not in d.get("name","").lower() and q not in d.get("phone","").lower():
                continue
            cnt         = trip_count_map.get(d["id"], 0)
            truck_plate = trk_map.get(d.get("truck_id",""), "—")
            rate_label  = (f"{d.get('rate',0):,.2f} ₽/км"
                           if d.get("rate_type","km") == "km"
                           else f"{d.get('rate',0):,.0f} ₽/рейс")
            self.tree.insert("","end", values=(
                d.get("name",""), d.get("phone",""), d.get("license",""),
                rate_label, d.get("category",""),
                truck_plate, d.get("status","Активен"), cnt, "✏️"
            ))


class DriverDialog(tk.Toplevel):
    def __init__(self, parent, db, driver=None, on_save=None):
        super().__init__(parent)
        self.db = db; self.driver = driver; self.on_save = on_save
        self.title("Водитель")
        self.geometry("520x480")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        fields = [
            ("ФИО:", "name"),
            ("Телефон:", "phone"),
            ("Вод. удостоверение №:", "license"),
            ("Паспорт (серия/номер):", "passport"),
        ]
        self.entries = {}
        for i, (lbl, key) in enumerate(fields):
            label(self, lbl, bg=BG).grid(row=i, column=0, sticky="w", padx=20, pady=6)
            e = entry(self, width=26)
            e.grid(row=i, column=1, padx=20, pady=6)
            if self.driver: e.insert(0, self.driver.get(key,""))
            self.entries[key] = e

        n = len(fields)

        # Rate type
        label(self, "Тип ставки:", bg=BG).grid(row=n, column=0, sticky="w", padx=20, pady=6)
        self.rate_type = tk.StringVar(value=self.driver.get("rate_type","km") if self.driver else "km")
        rf = tk.Frame(self, bg=BG)
        rf.grid(row=n, column=1, sticky="w", padx=20)
        for val, lbl_text in [("km","₽ за км"), ("trip","₽ за рейс")]:
            tk.Radiobutton(rf, text=lbl_text, variable=self.rate_type, value=val,
                          bg=BG, fg=TEXT, selectcolor=CARD, activebackground=BG).pack(side="left", padx=4)

        label(self, "Ставка:", bg=BG).grid(row=n+1, column=0, sticky="w", padx=20, pady=6)
        self.rate_e = entry(self, width=16)
        if self.driver: self.rate_e.insert(0, str(self.driver.get("rate","")))
        self.rate_e.grid(row=n+1, column=1, padx=20, sticky="w")

        label(self,"Категория:",bg=BG).grid(row=n+2,column=0,sticky="w",padx=20,pady=6)
        self.cat_var = tk.StringVar(value=self.driver.get("category","CE") if self.driver else "CE")
        combo(self,["C","CE","B","D"],textvariable=self.cat_var,width=10).grid(row=n+2,column=1,sticky="w",padx=20)

        label(self,"Статус:",bg=BG).grid(row=n+3,column=0,sticky="w",padx=20,pady=6)
        self.status_var = tk.StringVar(value=self.driver.get("status","Активен") if self.driver else "Активен")
        combo(self,["Активен","В рейсе","Отпуск","Уволен"],textvariable=self.status_var).grid(row=n+3,column=1,padx=20)

        btn(self,"💾 Сохранить",self._save,color=SUCCESS).grid(row=n+4,column=0,columnspan=2,pady=16)

    def _save(self):
        data = {k: e.get().strip() for k,e in self.entries.items()}
        data["category"]  = self.cat_var.get()
        data["status"]    = self.status_var.get()
        data["rate_type"] = self.rate_type.get()
        try: data["rate"] = float(self.rate_e.get().replace(",","."))
        except: data["rate"] = 0
        if not data["name"]:
            messagebox.showerror("Ошибка","Введите ФИО"); return
        if self.driver:
            data["truck_id"] = self.driver.get("truck_id","")
            self.db.update("drivers", self.driver["id"], data)
        else:
            self.db.add("drivers", data)
        if self.on_save: self.on_save()
        self.destroy()


class AssignTruckDialog(tk.Toplevel):
    def __init__(self, parent, db, driver, on_save=None):
        super().__init__(parent)
        self.db = db; self.driver = driver; self.on_save = on_save
        self.title(f"Привязать фуру — {driver.get('name','')}")
        self.geometry("440x240")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        label(self, f"Водитель: {self.driver.get('name','')}", bold=True, bg=BG).grid(
            row=0, column=0, columnspan=2, padx=20, pady=14, sticky="w")

        trucks = self.db.get_all("trucks")
        self.truck_ids = [""] + [t["id"] for t in trucks]
        truck_names = ["— Без фуры —"] + [f"{t.get('plate','')} {t.get('model','')}" for t in trucks]

        label(self, "Фура:", bg=BG).grid(row=1, column=0, sticky="w", padx=20, pady=8)
        self.truck_var = tk.StringVar()
        self.truck_cb = combo(self, truck_names, textvariable=self.truck_var, width=26)
        self.truck_cb.grid(row=1, column=1, padx=20)

        # Set current
        cur = self.driver.get("truck_id","")
        if cur and cur in self.truck_ids:
            self.truck_cb.current(self.truck_ids.index(cur))
        else:
            self.truck_cb.current(0)

        btn(self, "💾 Сохранить", self._save, color=SUCCESS).grid(
            row=2, column=0, columnspan=2, pady=16)

    def _save(self):
        idx = self.truck_cb.current()
        truck_id = self.truck_ids[idx] if idx >= 0 else ""
        self.db.update("drivers", self.driver["id"], {"truck_id": truck_id})
        if truck_id:
            self.db.update("trucks", truck_id, {"driver_id": self.driver["id"]})
        if self.on_save: self.on_save()
        self.destroy()


class SalaryDialog(tk.Toplevel):
    def __init__(self, parent, db, driver, on_save=None):
        super().__init__(parent)
        self.db = db; self.driver = driver; self.on_save = on_save
        self.title(f"Зарплата — {driver.get('name','')}")
        self.geometry("420x280")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        from datetime import datetime
        label(self, f"Водитель: {self.driver.get('name','')}", bold=True, bg=BG).grid(
            row=0,column=0,columnspan=2,padx=20,pady=12,sticky="w")
        label(self,"Сумма ₽:",bg=BG).grid(row=1,column=0,sticky="w",padx=20,pady=6)
        self.amt_e = entry(self, width=20)
        self.amt_e.insert(0, str(self.driver.get("rate","")))
        self.amt_e.grid(row=1,column=1,padx=20)
        label(self,"Период:",bg=BG).grid(row=2,column=0,sticky="w",padx=20,pady=6)
        self.period_e = entry(self,width=20)
        self.period_e.insert(0, datetime.now().strftime("%m.%Y"))
        self.period_e.grid(row=2,column=1,padx=20)
        label(self,"Дата выплаты:",bg=BG).grid(row=3,column=0,sticky="w",padx=20,pady=6)
        self.date_e = entry(self,width=20)
        self.date_e.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.date_e.grid(row=3,column=1,padx=20)
        btn(self,"💰 Выплатить",self._save,color=SUCCESS).grid(row=4,column=0,columnspan=2,pady=16)

    def _save(self):
        try:
            amt = float(self.amt_e.get().replace(",","."))
            assert amt > 0
        except: messagebox.showerror("Ошибка","Введите сумму"); return
        self.db.add("salary_payments",{
            "driver_id":   self.driver["id"],
            "driver_name": self.driver.get("name",""),
            "amount":      amt,
            "period":      self.period_e.get().strip(),
            "date":        self.date_e.get().strip()
        })
        if self.on_save: self.on_save()
        messagebox.showinfo("Готово",f"Выплата {amt:,.0f} ₽ записана!")
        self.destroy()
