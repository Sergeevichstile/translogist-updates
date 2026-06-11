import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from .ui_helpers import *

TO_INTERVAL = 30000  # km


def km_until_to(current_km, last_to_km):
    try:
        return TO_INTERVAL - (int(current_km) - int(last_to_km))
    except Exception:
        return None


def to_color(km_left):
    if km_left is None: return MUTED
    if km_left <= 0:    return DANGER
    if km_left <= 3000: return DANGER
    if km_left <= 7000: return WARN
    return SUCCESS


def days_until(date_str):
    try:
        d = datetime.strptime(date_str, "%d.%m.%Y")
        return (d - datetime.now()).days
    except Exception:
        return None


class TrucksFrame(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=BG)
        self.db = db
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG, padx=24, pady=14)
        hdr.pack(fill="x")
        label(hdr, "🚛 Фуры / Транспорт", size=16, bold=True, bg=BG).pack(side="left")
        btn(hdr, "+ Добавить фуру", self._add).pack(side="right")
        btn(hdr, "🗑️ Удалить", self._delete, color=DANGER).pack(side="right", padx=(0,8))

        sf = tk.Frame(self, bg=BG, padx=24)
        sf.pack(fill="x", pady=(0, 6))
        label(sf, "🔍", bg=BG, size=12).pack(side="left", padx=(0, 6))
        se = entry(sf, width=30, textvariable=self.search_var)
        se.pack(side="left")
        se.insert(0, "Поиск по номеру, марке...")
        se.bind("<FocusIn>", lambda e: se.delete(0, "end") if "..." in se.get() else None)

        self.stats_frame = tk.Frame(self, bg=BG, padx=24)
        self.stats_frame.pack(fill="x", pady=(0, 6))

        self.alerts_frame = tk.Frame(self, bg=BG, padx=24)
        self.alerts_frame.pack(fill="x")

        wrap = tk.Frame(self, bg=BG, padx=24)
        wrap.pack(fill="both", expand=True, pady=(8, 0))

        cols   = ["Марка/Модель", "Гос. номер", "Год", "Пробег (км)", "До ТО (км)", "Последнее ТО", "Страховка (дн.)", "Статус", ""]
        widths = [150, 110, 55, 100, 100, 130, 120, 90, 50]
        tbl, self.tree = make_table(wrap, cols, widths)
        tbl.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._on_double)

        self.menu = tk.Menu(self, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT)
        self.menu.add_command(label="🔧  Записать ТО",       command=self._do_to)
        self.menu.add_command(label="📍  Обновить пробег",   command=self._update_mileage)
        self.menu.add_separator()
        self.menu.add_command(label="✏️  Редактировать",     command=self._edit)
        self.menu.add_command(label="🗑️  Удалить",           command=self._delete)
        self.tree.bind("<Button-3>", self._show_menu)

    def _add(self):
        TruckDialog(self, self.db, on_save=self.refresh)

    def _on_double(self, e=None):
        self._edit()

    def _edit(self):
        sel = self.tree.selection()
        if not sel: return
        plate = self.tree.item(sel[0])["values"][1]
        truck = next((t for t in self.db.get_all("trucks") if t.get("plate") == plate), None)
        if truck: TruckDialog(self, self.db, truck=truck, on_save=self.refresh)

    def _do_to(self):
        """Record a completed TO service."""
        sel = self.tree.selection()
        if not sel: return
        plate = self.tree.item(sel[0])["values"][1]
        truck = next((t for t in self.db.get_all("trucks") if t.get("plate") == plate), None)
        if truck: TODialog(self, self.db, truck=truck, on_save=self.refresh)

    def _update_mileage(self):
        sel = self.tree.selection()
        if not sel: return
        plate = self.tree.item(sel[0])["values"][1]
        truck = next((t for t in self.db.get_all("trucks") if t.get("plate") == plate), None)
        if not truck: return
        MileageDialog(self, self.db, truck=truck, on_save=self.refresh)

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        vals  = self.tree.item(sel[0])["values"]
        plate = vals[1]
        truck = next((t for t in self.db.get_all("trucks") if t.get("plate") == plate), None)
        if truck and messagebox.askyesno("Удалить", f"Удалить {vals[0]} ({plate})?"):
            self.db.delete("trucks", truck["id"])
            self.refresh()

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
        for w in self.alerts_frame.winfo_children(): w.destroy()

        trucks = self.db.get_all("trucks")
        active = sum(1 for t in trucks if t.get("status") == "Активна")
        repair = sum(1 for t in trucks if t.get("status") == "Ремонт")

        for title, val, color in [
            ("Всего фур",  str(len(trucks)), TEXT),
            ("Активные",   str(active),      SUCCESS),
            ("В ремонте",  str(repair),      DANGER),
        ]:
            metric_card(self.stats_frame, title, val, color).pack(side="left", padx=(0, 10))

        # Build alerts
        alerts = []
        for t in trucks:
            cur_km   = t.get("mileage", 0) or 0
            last_km  = t.get("last_to_km", 0) or 0
            km_left  = km_until_to(cur_km, last_km)
            if km_left is not None and km_left <= 5000:
                sign = "❌" if km_left <= 0 else "⚠️"
                msg  = f"{sign}  {t.get('plate','')} {t.get('model','')} — ТО {'просрочено' if km_left<=0 else f'через {km_left:,} км'}"
                alerts.append((msg, DANGER if km_left <= 0 else WARN))
            ins_days = days_until(t.get("insurance_date", ""))
            if ins_days is not None and ins_days <= 30:
                sign = "❌" if ins_days <= 0 else "⚠️"
                msg  = f"{sign}  {t.get('plate','')} {t.get('model','')} — Страховка {'просрочена' if ins_days<=0 else f'через {ins_days} дн.'}"
                alerts.append((msg, DANGER if ins_days <= 0 else WARN))

        if alerts:
            af = tk.Frame(self.alerts_frame, bg="#1c1a0a", padx=12, pady=8)
            af.pack(fill="x", pady=(0, 8))
            label(af, "⚠️  Требуют внимания:", bold=True, bg="#1c1a0a", color=WARN).pack(anchor="w")
            for msg, color in alerts:
                label(af, msg, bg="#1c1a0a", color=color, size=10).pack(anchor="w", pady=1)

        for row in self.tree.get_children(): self.tree.delete(row)

        for t in trucks:
            if q and q not in t.get("plate","").lower() and q not in t.get("model","").lower():
                continue

            cur_km   = t.get("mileage", 0) or 0
            last_km  = t.get("last_to_km", 0) or 0
            km_left  = km_until_to(cur_km, last_km)
            ins_days = days_until(t.get("insurance_date", ""))

            def fmt_km(k):
                if k is None: return "—"
                if k <= 0:    return f"❗ Просрочено {abs(k):,} км"
                return f"{k:,} км"

            def fmt_days(d):
                if d is None: return "—"
                if d < 0:     return f"❗ {abs(d)} дн. назад"
                return f"{d} дн."

            last_to_date = t.get("last_to_date", "—") or "—"
            last_to_info = f"{last_to_date} ({last_km:,} км)" if last_km else last_to_date

            iid = self.tree.insert("", "end", values=(
                t.get("model", ""),
                t.get("plate", ""),
                t.get("year", ""),
                f"{cur_km:,}",
                fmt_km(km_left),
                last_to_info,
                fmt_days(ins_days),
                t.get("status", "Активна"),
                "✏️"
            ))

            # Row color
            bad_to  = km_left  is not None and km_left  <= 0
            bad_ins = ins_days is not None and ins_days <= 0
            warn_to  = km_left  is not None and 0 < km_left  <= 5000
            warn_ins = ins_days is not None and 0 < ins_days <= 30

            if bad_to or bad_ins:
                self.tree.item(iid, tags=("expired",))
            elif warn_to or warn_ins:
                self.tree.item(iid, tags=("warning",))

        self.tree.tag_configure("expired", foreground=DANGER)
        self.tree.tag_configure("warning", foreground=WARN)


# ── Dialogs ────────────────────────────────────────────────────────────────

class TruckDialog(tk.Toplevel):
    def __init__(self, parent, db, truck=None, on_save=None):
        super().__init__(parent)
        self.db = db; self.truck = truck; self.on_save = on_save
        self.title("Фура")
        self.geometry("520x520")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        t = self.truck or {}
        fields = [
            ("Марка и модель:",           "model"),
            ("Гос. номер:",               "plate"),
            ("Год выпуска:",              "year"),
            ("Текущий пробег (км):",      "mileage"),
            ("Пробег на последнем ТО:",   "last_to_km"),
            ("Дата последнего ТО:",       "last_to_date"),
            ("Страховка до (дд.мм.гггг):","insurance_date"),
        ]
        self.entries = {}
        for i, (lbl, key) in enumerate(fields):
            label(self, lbl, bg=BG).grid(row=i, column=0, sticky="w", padx=20, pady=5)
            e = entry(self, width=26)
            e.grid(row=i, column=1, padx=20, pady=5)
            if t: e.insert(0, str(t.get(key, "") or ""))
            self.entries[key] = e

        # TO interval info
        n = len(fields)
        info = tk.Frame(self, bg="#0f2027", padx=12, pady=8)
        info.grid(row=n, column=0, columnspan=2, sticky="ew", padx=20, pady=6)
        label(info, f"🔧  ТО каждые {TO_INTERVAL:,} км. Записать ТО можно через правую кнопку в таблице.",
              bg="#0f2027", color="#7dd3fc", size=9).pack(anchor="w")

        label(self, "Статус:", bg=BG).grid(row=n+1, column=0, sticky="w", padx=20, pady=5)
        self.status_var = tk.StringVar(value=t.get("status", "Активна"))
        combo(self, ["Активна","В рейсе","Ремонт","Простой"],
              textvariable=self.status_var).grid(row=n+1, column=1, padx=20)

        btn(self, "💾 Сохранить", self._save, color=SUCCESS).grid(
            row=n+2, column=0, columnspan=2, pady=14)

    def _save(self):
        data = {k: e.get().strip() for k, e in self.entries.items()}
        data["status"] = self.status_var.get()
        for km_field in ["mileage", "last_to_km"]:
            try: data[km_field] = int(data[km_field].replace(" ", "").replace(",", ""))
            except: data[km_field] = 0
        if not data["model"] or not data["plate"]:
            messagebox.showerror("Ошибка", "Заполните марку и номер"); return
        if self.truck: self.db.update("trucks", self.truck["id"], data)
        else:          self.db.add("trucks", data)
        if self.on_save: self.on_save()
        self.destroy()


class TODialog(tk.Toplevel):
    """Record a completed TO service."""
    def __init__(self, parent, db, truck, on_save=None):
        super().__init__(parent)
        self.db = db; self.truck = truck; self.on_save = on_save
        self.title(f"Записать ТО — {truck.get('plate','')}")
        self.geometry("460x360")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        t = self.truck
        cur_km   = t.get("mileage", 0) or 0
        last_km  = t.get("last_to_km", 0) or 0
        km_left  = km_until_to(cur_km, last_km)

        label(self, f"Фура: {t.get('model','')} ({t.get('plate','')})",
              bold=True, bg=BG).grid(row=0, column=0, columnspan=2, padx=20, pady=12, sticky="w")

        # Current info
        info = tk.Frame(self, bg=CARD, padx=12, pady=8)
        info.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(0,10))
        label(info, f"Текущий пробег: {cur_km:,} км", bg=CARD, size=10).pack(anchor="w")
        label(info, f"Последнее ТО:   {last_km:,} км  ({t.get('last_to_date','—')})", bg=CARD, size=10).pack(anchor="w")
        if km_left is not None:
            color = DANGER if km_left <= 0 else WARN if km_left <= 5000 else SUCCESS
            label(info, f"До следующего ТО: {km_left:,} км", bg=CARD, size=10, color=color).pack(anchor="w")

        label(self, "Пробег при ТО (км):", bg=BG).grid(row=2, column=0, sticky="w", padx=20, pady=6)
        self.km_e = entry(self, width=18)
        self.km_e.insert(0, str(cur_km))
        self.km_e.grid(row=2, column=1, padx=20, sticky="w")

        label(self, "Дата ТО:", bg=BG).grid(row=3, column=0, sticky="w", padx=20, pady=6)
        self.date_e = entry(self, width=18)
        self.date_e.insert(0, datetime.now().strftime("%d.%m.%Y"))
        self.date_e.grid(row=3, column=1, padx=20, sticky="w")

        label(self, "Описание работ:", bg=BG).grid(row=4, column=0, sticky="w", padx=20, pady=6)
        self.desc_e = entry(self, width=26)
        self.desc_e.insert(0, "Плановое ТО")
        self.desc_e.grid(row=4, column=1, padx=20, sticky="w")

        label(self, "Стоимость ТО (₽):", bg=BG).grid(row=5, column=0, sticky="w", padx=20, pady=6)
        self.cost_e = entry(self, width=18)
        self.cost_e.grid(row=5, column=1, padx=20, sticky="w")

        btn(self, "🔧 Записать ТО", self._save, color=SUCCESS).grid(
            row=6, column=0, columnspan=2, pady=14)

    def _save(self):
        try:
            km = int(self.km_e.get().replace(" ","").replace(",",""))
            assert km > 0
        except:
            messagebox.showerror("Ошибка","Введите пробег"); return

        date = self.date_e.get().strip()
        desc = self.desc_e.get().strip()
        try: cost = float(self.cost_e.get().replace(",","."))
        except: cost = 0

        # Update truck
        updates = {
            "last_to_km":   km,
            "last_to_date": date,
            "mileage":      max(km, self.truck.get("mileage",0) or 0),
        }
        self.db.update("trucks", self.truck["id"], updates)

        # Record as expense
        if cost > 0:
            self.db.add("expenses", {
                "category":    "ТО/Ремонт",
                "description": f"ТО {self.truck.get('plate','')} — {desc}",
                "amount":      cost,
                "date":        date,
            })

        if self.on_save: self.on_save()
        next_km = km + TO_INTERVAL
        messagebox.showinfo("ТО записано",
            f"✅ ТО выполнено на {km:,} км\n"
            f"Следующее ТО через {TO_INTERVAL:,} км\n"
            f"Примерно на пробеге: {next_km:,} км")
        self.destroy()


class MileageDialog(tk.Toplevel):
    """Quick mileage update."""
    def __init__(self, parent, db, truck, on_save=None):
        super().__init__(parent)
        self.db = db; self.truck = truck; self.on_save = on_save
        self.title(f"Пробег — {truck.get('plate','')}")
        self.geometry("400x220")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        t = self.truck
        label(self, f"{t.get('model','')} ({t.get('plate','')})",
              bold=True, bg=BG).grid(row=0, column=0, columnspan=2, padx=20, pady=12, sticky="w")
        label(self, f"Текущий пробег: {t.get('mileage',0):,} км",
              bg=BG, color=MUTED, size=10).grid(row=1, column=0, columnspan=2, padx=20, sticky="w")
        label(self, "Новый пробег (км):", bg=BG).grid(row=2, column=0, sticky="w", padx=20, pady=10)
        self.km_e = entry(self, width=16)
        self.km_e.insert(0, str(t.get("mileage", 0) or 0))
        self.km_e.grid(row=2, column=1, padx=20)
        btn(self, "💾 Сохранить", self._save, color=SUCCESS).grid(
            row=3, column=0, columnspan=2, pady=14)

    def _save(self):
        try:
            km = int(self.km_e.get().replace(" ","").replace(",",""))
            assert km >= 0
        except:
            messagebox.showerror("Ошибка","Введите пробег"); return
        self.db.update("trucks", self.truck["id"], {"mileage": km})
        if self.on_save: self.on_save()
        self.destroy()
