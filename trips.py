import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from .ui_helpers import *


def calc_vat(total: float, rate: float):
    """Calculate VAT from total amount (VAT included).
    Example: total=315000, rate=5 → no_vat=300000, vat=15000
    """
    if rate == 0:
        return round(total, 2), 0.0, round(total, 2)
    no_vat = round(total / (1 + rate / 100), 2)
    vat    = round(total - no_vat, 2)
    return no_vat, vat, round(total, 2)


class TripsFrame(tk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent, bg=BG)
        self.db = db
        self.search_var    = tk.StringVar()
        self.filter_status = tk.StringVar(value="Все")
        self.filter_vat    = tk.StringVar(value="Все")
        self.search_var.trace_add("write",    lambda *a: self.refresh())
        self.filter_status.trace_add("write", lambda *a: self.refresh())
        self.filter_vat.trace_add("write",    lambda *a: self.refresh())
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG, padx=24, pady=14)
        hdr.pack(fill="x")
        label(hdr, "🗺️ Рейсы", size=16, bold=True, bg=BG).pack(side="left")
        btn(hdr, "📋 Вставить рейс", self._paste_trip, color=CARD).pack(side="right", padx=(0,8))
        btn(hdr, "+ Добавить рейс", self._add).pack(side="right")
        btn(hdr, "🗑️ Удалить", self._delete, color=DANGER).pack(side="right", padx=(0,8))

        ff = tk.Frame(self, bg=BG, padx=24)
        ff.pack(fill="x", pady=(0,8))
        label(ff, "🔍", bg=BG, size=12).pack(side="left", padx=(0,4))
        se = entry(ff, width=26, textvariable=self.search_var)
        se.pack(side="left", padx=(0,12))
        se.insert(0, "Маршрут, контрагент...")
        se.bind("<FocusIn>", lambda e: se.delete(0,"end") if "..." in se.get() else None)

        label(ff, "Статус:", bg=BG, size=10).pack(side="left", padx=(0,4))
        combo(ff, ["Все","Запланирован","В пути","Выполнен","Отменён"],
              textvariable=self.filter_status, width=12).pack(side="left", padx=(0,12))

        label(ff, "НДС:", bg=BG, size=10).pack(side="left", padx=(0,4))
        combo(ff, ["Все","С НДС","Без НДС"],
              textvariable=self.filter_vat, width=9).pack(side="left")

        self.stats = tk.Frame(self, bg=BG, padx=24)
        self.stats.pack(fill="x", pady=(0,8))

        wrap = tk.Frame(self, bg=BG, padx=24)
        wrap.pack(fill="both", expand=True)

        cols   = ["№ Акта","Дата","Маршрут","Контрагент","Водитель","Фура",
                  "Без НДС","НДС","Итого","Ставка экспед.","Статус"]
        widths = [80,90,200,130,140,100,110,80,100,110,100]
        tbl, self.tree = make_table(wrap, cols, widths)
        tbl.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._edit)

        self.menu = tk.Menu(self, tearoff=0, bg=CARD, fg=TEXT, activebackground=ACCENT)
        self.menu.add_command(label="✏️  Редактировать", command=self._edit)
        self.menu.add_command(label="🗑️  Удалить",       command=self._delete)
        self.tree.bind("<Button-3>", self._ctx)

    def _add(self):    TripDialog(self, self.db, on_save=self.refresh)

    def _paste_trip(self):
        """Parse trip data from clipboard text."""
        try:
            text = self.clipboard_get().strip()
        except Exception:
            messagebox.showinfo("Буфер пуст", "Скопируйте данные рейса и попробуйте снова.")
            return
        if not text:
            messagebox.showinfo("Буфер пуст", "Скопируйте данные рейса и попробуйте снова.")
            return
        PasteTripDialog(self, self.db, text, on_save=self.refresh)
    def _edit(self, e=None):
        sel = self.tree.selection()
        if not sel: return
        tid = self.tree.item(sel[0]).get("tags",[None])[0]
        trip = self.db.get_by_id("trips", tid) if tid else None
        if trip: TripDialog(self, self.db, trip=trip, on_save=self.refresh)

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        tid = self.tree.item(sel[0]).get("tags",[None])[0]
        if tid and messagebox.askyesno("Удалить","Удалить рейс?"):
            self.db.delete("trips", tid); self.refresh()

    def _ctx(self, e):
        row = self.tree.identify_row(e.y)
        if row:
            self.tree.selection_set(row)
            self.menu.post(e.x_root, e.y_root)

    def refresh(self):
        if not self.winfo_ismapped():
            return  # Skip if not visible
        for w in self.stats.winfo_children(): w.destroy()

        trips   = self.db.get_all("trips")
        cp_map  = {c["id"]: c.get("name","") for c in self.db.get_all("counterparties")}
        drv_map = {d["id"]: d.get("name","") for d in self.db.get_all("drivers")}
        car_map = {c["id"]: c.get("name","") for c in self.db.get_all("carriers")}
        trk_map = {t["id"]: t.get("plate","") for t in self.db.get_all("trucks")}

        q       = self.search_var.get().lower()
        if "..." in q: q = ""
        st_flt  = self.filter_status.get()
        vat_flt = self.filter_vat.get()

        filtered = []
        for t in trips:
            cp_name = cp_map.get(t.get("counterparty_id",""),"")
            if q and q not in t.get("route","").lower() and q not in cp_name.lower(): continue
            if st_flt != "Все" and t.get("status","") != st_flt: continue
            if vat_flt == "С НДС"   and t.get("vat_rate",0) == 0: continue
            if vat_flt == "Без НДС" and t.get("vat_rate",0) >  0: continue
            filtered.append(t)

        total_inc = sum(t.get("income_total",0) for t in filtered)
        total_vat = sum(t.get("vat_amount",0)   for t in filtered)
        done      = sum(1 for t in filtered if t.get("status")=="Выполнен")

        for title, val, color in [
            ("Рейсов (фильтр)", str(len(filtered)), TEXT),
            ("Выполнено",       str(done),           SUCCESS),
            ("Доход итого",     f"{total_inc:,.0f} ₽", SUCCESS),
            ("НДС начислен",    f"{total_vat:,.0f} ₽", WARN),
        ]:
            metric_card(self.stats, title, val, color).pack(side="left", padx=(0,10))

        for row in self.tree.get_children(): self.tree.delete(row)

        for t in reversed(filtered):
            drv_name = drv_map.get(t.get("driver_id",""), "")
            if not drv_name and t.get("carrier_id"):
                drv_name = car_map.get(t.get("carrier_id",""),"—")
            truck_plate = trk_map.get(t.get("truck_id",""), "—")
            vat_lbl = f"{t.get('vat_amount',0):,.0f} ₽" if t.get("vat_rate",0)>0 else "Без НДС"
            exp_rate = f"{t.get('expeditor_rate',0):,.0f} ₽" if t.get("expeditor_rate") else "—"

            iid = self.tree.insert("","end", tags=(t["id"],), values=(
                t.get("act_number","—"),
                t.get("date",""),
                t.get("route",""),
                cp_map.get(t.get("counterparty_id",""),"—"),
                drv_name or "—",
                truck_plate,
                f"{t.get('income_no_vat',0):,.0f} ₽",
                vat_lbl,
                f"{t.get('income_total',0):,.0f} ₽",
                exp_rate,
                t.get("status","")
            ))
            st = t.get("status","")
            if st == "Выполнен":    self.tree.item(iid, tags=(t["id"],"done"))
            elif st == "Отменён":   self.tree.item(iid, tags=(t["id"],"cancelled"))
            elif st == "Запланирован": self.tree.item(iid, tags=(t["id"],"planned"))

        self.tree.tag_configure("done",      foreground=SUCCESS)
        self.tree.tag_configure("cancelled", foreground=MUTED)
        self.tree.tag_configure("planned",   foreground=WARN)


class TripDialog(tk.Toplevel):
    def __init__(self, parent, db, trip=None, on_save=None):
        super().__init__(parent)
        self.db = db; self.trip = trip; self.on_save = on_save
        self.title("Рейс")
        self.geometry("680x700")
        self.minsize(600, 600)
        self.configure(bg=BG)
        self.grab_set()
        from .ui_helpers import _bind_clipboard
        _bind_clipboard(self)
        self._build()

    def _build(self):
        # Scrollable
        canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.f = tk.Frame(canvas, bg=BG)
        win = canvas.create_window((0,0), window=self.f, anchor="nw")
        self.f.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(
            int(-1*(e.delta/120)), "units"))

        f = self.trip or {}
        self._row = 0

        def lbl_entry(label_text, key, default="", width=40, multiline=False):
            r = self._row
            label(self.f, label_text, bg=BG, size=10).grid(
                row=r, column=0, sticky="w", padx=20, pady=5)
            if multiline:
                e = tk.Text(self.f, width=width, height=2,
                           bg="#2a2d45", fg=TEXT, insertbackground=TEXT,
                           relief="flat", font=("Segoe UI", 11),
                           highlightthickness=1, highlightbackground=BORDER,
                           highlightcolor=ACCENT)
                e.grid(row=r, column=1, padx=20, pady=5, sticky="ew")
                if f.get(key): e.insert("1.0", f.get(key, ""))
            else:
                e = entry(self.f, width=width)
                e.grid(row=r, column=1, padx=20, pady=5, sticky="ew")
                e.insert(0, str(f.get(key, default)))
            self._row += 1
            return e

        # Grid config
        self.f.columnconfigure(1, weight=1)

        # ── Basic info ──────────────────────────────────────────
        label(self.f, "── Основное ──", bg=BG, bold=True, color=MUTED).grid(
            row=self._row, column=0, columnspan=2, padx=20, pady=(14,4), sticky="w")
        self._row += 1

        self.act_e    = lbl_entry("№ Акта:", "act_number")
        self.date_e   = lbl_entry("Дата:", "date",
                                   default=datetime.now().strftime("%d.%m.%Y"), width=18)
        self.route_e  = lbl_entry("Маршрут (откуда → куда):", "route",
                                   width=48, multiline=True)

        # Counterparty
        label(self.f, "Контрагент:", bg=BG, size=10).grid(
            row=self._row, column=0, sticky="w", padx=20, pady=5)
        cps = self.db.get_all("counterparties")
        self.cp_ids = [c["id"] for c in cps]
        self.cp_var = tk.StringVar()
        self.cp_cb  = combo(self.f, [c.get("name","") for c in cps] or ["—"],
                            textvariable=self.cp_var, width=38)
        if f.get("counterparty_id") and f["counterparty_id"] in self.cp_ids:
            self.cp_cb.current(self.cp_ids.index(f["counterparty_id"]))
        elif cps: self.cp_cb.current(0)
        self.cp_cb.grid(row=self._row, column=1, padx=20, pady=5, sticky="w")
        self._row += 1

        # ── Transport ───────────────────────────────────────────
        label(self.f, "── Транспорт ──", bg=BG, bold=True, color=MUTED).grid(
            row=self._row, column=0, columnspan=2, padx=20, pady=(10,4), sticky="w")
        self._row += 1

        label(self.f, "Тип транспорта:", bg=BG, size=10).grid(
            row=self._row, column=0, sticky="w", padx=20, pady=5)
        self.transport_type = tk.StringVar(value=f.get("transport_type","Своя"))
        tf = tk.Frame(self.f, bg=BG)
        tf.grid(row=self._row, column=1, sticky="w", padx=20)
        for val in ["Своя","Чужая"]:
            tk.Radiobutton(tf, text=val, variable=self.transport_type, value=val,
                          bg=BG, fg=TEXT, selectcolor=CARD, activebackground=BG,
                          command=self._toggle_transport).pack(side="left", padx=6)
        self._row += 1

        # Own truck + driver
        self.own_frame = tk.Frame(self.f, bg=BG)
        self.own_frame.grid(row=self._row, column=0, columnspan=2, sticky="ew", padx=20)

        label(self.own_frame, "Фура:", bg=BG, size=10).grid(row=0,column=0,sticky="w",pady=4)
        trucks = self.db.get_all("trucks")
        self.trk_ids = [t["id"] for t in trucks]
        self.trk_var = tk.StringVar()
        self.trk_cb  = combo(self.own_frame,
                             [f"{t.get('plate','')} {t.get('model','')}" for t in trucks] or ["—"],
                             textvariable=self.trk_var, width=30)
        if f.get("truck_id") and f["truck_id"] in self.trk_ids:
            self.trk_cb.current(self.trk_ids.index(f["truck_id"]))
        elif trucks: self.trk_cb.current(0)
        self.trk_cb.grid(row=0,column=1,padx=10,sticky="w")
        self.trk_cb.bind("<<ComboboxSelected>>", self._on_truck_select)

        label(self.own_frame, "Водитель:", bg=BG, size=10).grid(row=1,column=0,sticky="w",pady=4)
        drivers = self.db.get_all("drivers")
        self.drv_ids = [d["id"] for d in drivers]
        self.drv_var = tk.StringVar()
        self.drv_cb  = combo(self.own_frame,
                             [d.get("name","") for d in drivers] or ["—"],
                             textvariable=self.drv_var, width=30)
        if f.get("driver_id") and f["driver_id"] in self.drv_ids:
            self.drv_cb.current(self.drv_ids.index(f["driver_id"]))
        elif drivers: self.drv_cb.current(0)
        self.drv_cb.grid(row=1,column=1,padx=10,sticky="w")
        self._row += 1

        # Carrier frame
        self.carrier_frame = tk.Frame(self.f, bg=BG)
        self.carrier_frame.grid(row=self._row, column=0, columnspan=2, sticky="ew", padx=20)
        label(self.carrier_frame,"Перевозчик:",bg=BG,size=10).grid(row=0,column=0,sticky="w",pady=4)
        carriers = self.db.get_all("carriers")
        self.car_ids = [c["id"] for c in carriers]
        self.car_var = tk.StringVar()
        self.car_cb  = combo(self.carrier_frame,
                             [c.get("name","") for c in carriers] or ["—"],
                             textvariable=self.car_var, width=30)
        if f.get("carrier_id") and f["carrier_id"] in self.car_ids:
            self.car_cb.current(self.car_ids.index(f["carrier_id"]))
        elif carriers: self.car_cb.current(0)
        self.car_cb.grid(row=0,column=1,padx=10,sticky="w")
        self.car_cb.bind("<<ComboboxSelected>>", self._on_carrier_select)

        label(self.carrier_frame,"Ставка перевозчика (₽):",bg=BG,size=10).grid(row=1,column=0,sticky="w",pady=4)
        self.carrier_rate_e = entry(self.carrier_frame, width=18)
        self.carrier_rate_e.insert(0, str(f.get("carrier_rate","") or ""))
        self.carrier_rate_e.grid(row=1,column=1,padx=10,sticky="w")
        self.carrier_rate_e.bind("<KeyRelease>", self._recalc_carrier)
        self.carrier_margin_lbl = label(self.carrier_frame, "", bg=BG, color=MUTED, size=9)
        self.carrier_margin_lbl.grid(row=2,column=0,columnspan=2,sticky="w",pady=2)
        self._row += 1

        # ── Finance ─────────────────────────────────────────────
        label(self.f, "── Финансы ──", bg=BG, bold=True, color=MUTED).grid(
            row=self._row, column=0, columnspan=2, padx=20, pady=(10,4), sticky="w")
        self._row += 1

        # Total amount with VAT
        label(self.f, "Сумма рейса (с НДС если есть) ₽:", bg=BG, size=10).grid(
            row=self._row, column=0, sticky="w", padx=20, pady=5)
        self.income_e = entry(self.f, width=20)
        self.income_e.insert(0, str(f.get("income_total","")))
        self.income_e.grid(row=self._row, column=1, padx=20, pady=5, sticky="w")
        self.income_e.bind("<KeyRelease>", self._recalc)
        self._row += 1

        # VAT rate
        label(self.f, "НДС:", bg=BG, size=10).grid(
            row=self._row, column=0, sticky="w", padx=20, pady=5)
        self.vat_var = tk.StringVar(value=str(f.get("vat_rate",0)))
        vf = tk.Frame(self.f, bg=BG)
        vf.grid(row=self._row, column=1, sticky="w", padx=20)
        for val, lbl_text in [("0","Без НДС"),("5","НДС 5%")]:
            tk.Radiobutton(vf, text=lbl_text, variable=self.vat_var, value=val,
                          bg=BG, fg=TEXT, selectcolor=CARD, activebackground=BG,
                          command=self._recalc).pack(side="left", padx=6)
        self._row += 1

        # VAT breakdown info
        self.vat_info = tk.Frame(self.f, bg="#0f2d1f", padx=14, pady=8)
        self.vat_info.grid(row=self._row, column=0, columnspan=2,
                           padx=20, pady=4, sticky="ew")
        self.vat_no_label    = label(self.vat_info, "Без НДС: —",  bg="#0f2d1f", color="#86efac", size=10)
        self.vat_amt_label   = label(self.vat_info, "НДС: —",      bg="#0f2d1f", color=WARN,      size=10)
        self.vat_total_label = label(self.vat_info, "Итого: —",    bg="#0f2d1f", color=TEXT,      size=10, bold=True)
        self.vat_no_label.pack(side="left", padx=(0,20))
        self.vat_amt_label.pack(side="left", padx=(0,20))
        self.vat_total_label.pack(side="left")
        self._row += 1

        # Expeditor rate
        label(self.f, "Ставка экспедитора (₽):", bg=BG, size=10).grid(
            row=self._row, column=0, sticky="w", padx=20, pady=5)
        exp_row = tk.Frame(self.f, bg=BG)
        exp_row.grid(row=self._row, column=1, padx=20, pady=5, sticky="w")
        self.exp_e = entry(exp_row, width=18)
        self.exp_e.insert(0, str(f.get("expeditor_rate","")) )
        self.exp_e.pack(side="left")
        self.no_exp_var = tk.BooleanVar(value=f.get("no_expeditor", False))
        def _toggle_exp():
            if self.no_exp_var.get():
                self.exp_e.configure(state="disabled")
                self.exp_e.delete(0,"end")
            else:
                self.exp_e.configure(state="normal")
        no_exp_cb = tk.Checkbutton(exp_row, text="Нет экспедитора",
                                   variable=self.no_exp_var,
                                   bg=BG, fg=MUTED, selectcolor=CARD,
                                   activebackground=BG, font=("Segoe UI",9),
                                   command=_toggle_exp)
        no_exp_cb.pack(side="left", padx=8)
        if f.get("no_expeditor"): _toggle_exp()
        self._row += 1

        # Carrier cost (only shown for external carrier)
        self.carrier_cost_row_lbl = label(self.f, "Стоимость перевозчика (₽):", bg=BG, size=10)
        self.carrier_cost_row_lbl.grid(row=self._row, column=0, sticky="w", padx=20, pady=5)
        self.carrier_cost_e = entry(self.f, width=20)
        self.carrier_cost_e.insert(0, str(f.get("carrier_cost","")))
        self.carrier_cost_e.grid(row=self._row, column=1, padx=20, pady=5, sticky="w")
        self._carrier_cost_row = self._row
        self._row += 1

        # Distance for km rate calc
        label(self.f, "Расстояние (км):", bg=BG, size=10).grid(
            row=self._row, column=0, sticky="w", padx=20, pady=5)
        self.dist_e = entry(self.f, width=20)
        self.dist_e.insert(0, str(f.get("distance","")) )
        self.dist_e.grid(row=self._row, column=1, padx=20, pady=5, sticky="w")
        self.dist_e.bind("<KeyRelease>", self._recalc)
        self._row += 1

        # Driver salary calc info
        self.salary_info = label(self.f, "", bg=BG, color=MUTED, size=9)
        self.salary_info.grid(row=self._row, column=0, columnspan=2, padx=20, sticky="w")
        self._row += 1

        # ── Status ──────────────────────────────────────────────
        label(self.f, "── Статус ──", bg=BG, bold=True, color=MUTED).grid(
            row=self._row, column=0, columnspan=2, padx=20, pady=(10,4), sticky="w")
        self._row += 1

        label(self.f, "Статус:", bg=BG, size=10).grid(
            row=self._row, column=0, sticky="w", padx=20, pady=5)
        self.status_var = tk.StringVar(value=f.get("status","Запланирован"))
        combo(self.f, ["Запланирован","В пути","Выполнен","Отменён"],
              textvariable=self.status_var, width=18).grid(
            row=self._row, column=1, sticky="w", padx=20)
        self._row += 1

        # Save button
        btn(self.f, "💾 Сохранить рейс", self._save, color=SUCCESS).grid(
            row=self._row, column=0, columnspan=2, pady=20, padx=20, sticky="ew")

        self._toggle_transport()
        self._recalc()

    def _paste(self, event, widget):
        try:
            text = self.clipboard_get()
            if isinstance(widget, tk.Text):
                widget.insert(tk.INSERT, text)
            else:
                pos = widget.index(tk.INSERT)
                widget.insert(pos, text)
        except Exception:
            pass
        return "break"

    def _on_truck_select(self, e=None):
        """Auto-select driver when truck is selected."""
        idx = self.trk_cb.current()
        if idx < 0 or idx >= len(self.trk_ids): return
        truck_id = self.trk_ids[idx]
        # Find driver assigned to this truck
        drivers = self.db.get_all("drivers")
        for drv in drivers:
            if drv.get("truck_id") == truck_id and drv["id"] in self.drv_ids:
                self.drv_cb.current(self.drv_ids.index(drv["id"]))
                break

    def _on_carrier_select(self, e=None):
        """Auto-fill carrier rate from carrier record."""
        idx = self.car_cb.current()
        if idx < 0 or idx >= len(self.car_ids): return
        carrier = self.db.get_by_id("carriers", self.car_ids[idx])
        if carrier and carrier.get("rate"):
            self.carrier_rate_e.delete(0, "end")
            self.carrier_rate_e.insert(0, str(carrier["rate"]))
            self._recalc_carrier()

    def _recalc_carrier(self, event=None):
        """Show margin after carrier rate."""
        try:
            total = float(self.income_e.get().replace(",","").replace(" ",""))
            rate  = float(self.carrier_rate_e.get().replace(",","").replace(" ",""))
            margin = total - rate
            color = "#86efac" if margin >= 0 else "#f87171"
            self.carrier_margin_lbl.config(
                text=f"💰 Маржа: {total:,.0f} − {rate:,.0f} = {margin:,.0f} ₽",
                fg=color)
        except Exception:
            self.carrier_margin_lbl.config(text="")

    def _toggle_transport(self):
        if self.transport_type.get() == "Своя":
            self.carrier_frame.grid_remove()
            self.own_frame.grid()
            # Hide carrier cost
            self.carrier_cost_row_lbl.grid_remove()
            self.carrier_cost_e.grid_remove()
        else:
            self.own_frame.grid_remove()
            self.carrier_frame.grid()
            # Show carrier cost
            self.carrier_cost_row_lbl.grid(row=self._carrier_cost_row, column=0,
                                            sticky="w", padx=20, pady=5)
            self.carrier_cost_e.grid(row=self._carrier_cost_row, column=1,
                                     padx=20, pady=5, sticky="w")

    def _recalc(self, event=None):
        try:
            total = float(self.income_e.get().replace(",","").replace(" ",""))
            rate  = float(self.vat_var.get())
            no_vat, vat_amt, _ = calc_vat(total, rate)
            if rate > 0:
                self.vat_no_label.config(
                    text=f"Без НДС: {no_vat:,.2f} ₽")
                self.vat_amt_label.config(
                    text=f"НДС {rate:.0f}%: {vat_amt:,.2f} ₽")
                self.vat_total_label.config(
                    text=f"Итого: {total:,.2f} ₽")
            else:
                self.vat_no_label.config(text="Без НДС")
                self.vat_amt_label.config(text="")
                self.vat_total_label.config(text=f"Сумма: {total:,.2f} ₽")
        except Exception:
            self.vat_no_label.config(text="Введите сумму")
            self.vat_amt_label.config(text="")
            self.vat_total_label.config(text="")

        # Driver km rate calc
        try:
            dist = float(self.dist_e.get().replace(",","").replace(" ",""))
            idx  = self.drv_cb.current()
            if idx >= 0 and idx < len(self.drv_ids):
                drv = self.db.get_by_id("drivers", self.drv_ids[idx])
                if drv and drv.get("rate_type","km") == "km" and drv.get("rate",0):
                    salary = round(dist * drv["rate"], 2)
                    self.salary_info.config(
                        text=f"💰 Зарплата водителя: {dist:,.0f} км × {drv['rate']:,.2f} ₽/км = {salary:,.2f} ₽")
                    return
        except Exception:
            pass
        self.salary_info.config(text="")

    def _save(self):
        try:
            total = float(self.income_e.get().replace(",","").replace(" ",""))
            assert total > 0
        except Exception:
            messagebox.showerror("Ошибка","Введите корректную сумму"); return

        vat_rate = float(self.vat_var.get())
        no_vat, vat_amt, total = calc_vat(total, vat_rate)

        # Get route from Text widget
        try:
            route = self.route_e.get("1.0","end").strip()
        except Exception:
            route = self.route_e.get().strip()

        no_exp = self.no_exp_var.get()
        try: exp_rate = 0 if no_exp else float(self.exp_e.get().replace(",","").replace(" ",""))
        except: exp_rate = 0
        try: dist = float(self.dist_e.get().replace(",","").replace(" ",""))
        except: dist = 0

        data = {
            "act_number":    self.act_e.get().strip(),
            "date":          self.date_e.get().strip(),
            "route":         route,
            "status":        self.status_var.get(),
            "vat_rate":      vat_rate,
            "income_no_vat": no_vat,
            "vat_amount":    vat_amt,
            "income_total":  total,
            "transport_type": self.transport_type.get(),
            "expeditor_rate": exp_rate,
            "no_expeditor":  no_exp,
            "distance":      dist,
        }

        if self.cp_ids and self.cp_cb.current() >= 0:
            data["counterparty_id"] = self.cp_ids[self.cp_cb.current()]

        if self.transport_type.get() == "Своя":
            if self.trk_ids and self.trk_cb.current() >= 0:
                data["truck_id"] = self.trk_ids[self.trk_cb.current()]
            if self.drv_ids and self.drv_cb.current() >= 0:
                data["driver_id"] = self.drv_ids[self.drv_cb.current()]
            data["carrier_id"] = None; data["carrier_cost"] = 0; data["carrier_rate"] = 0
        else:
            if self.car_ids and self.car_cb.current() >= 0:
                data["carrier_id"] = self.car_ids[self.car_cb.current()]
            try: data["carrier_cost"] = float(self.carrier_cost_e.get().replace(",","").replace(" ",""))
            except: data["carrier_cost"] = 0
            try: data["carrier_rate"] = float(self.carrier_rate_e.get().replace(",","").replace(" ",""))
            except: data["carrier_rate"] = 0
            data["truck_id"] = None; data["driver_id"] = None

        if self.trip: self.db.update("trips", self.trip["id"], data)
        else:         self.db.add("trips", data)
        if self.on_save: self.on_save()
        self.destroy()


class PasteTripDialog(tk.Toplevel):
    """Parse and import trip data from clipboard text."""

    def __init__(self, parent, db, text, on_save=None):
        super().__init__(parent)
        self.db = db
        self.on_save = on_save
        self.title("Вставить рейс из буфера")
        self.geometry("620x580")
        self.configure(bg=BG)
        self.grab_set()
        self._build(text)

    def _build(self, text):
        hdr = tk.Frame(self, bg=BG, padx=20, pady=12)
        hdr.pack(fill="x")
        label(hdr, "📋 Вставить рейс", bold=True, size=14, bg=BG).pack(side="left")

        # Show raw text
        info = tk.Frame(self, bg=CARD, padx=16, pady=10)
        info.pack(fill="x", padx=20, pady=(0,8))
        label(info, "Скопированный текст:", bg=CARD, size=9, color=MUTED).pack(anchor="w")
        txt = tk.Text(info, height=5, bg="#111827", fg=MUTED,
                      font=("Consolas",9), relief="flat",
                      highlightthickness=0)
        txt.insert("1.0", text)
        txt.configure(state="disabled")
        txt.pack(fill="x")

        # Parse fields
        label(self, "Заполните или исправьте данные:", bold=True, bg=BG, size=10).pack(
            anchor="w", padx=20, pady=(8,4))

        form = tk.Frame(self, bg=BG)
        form.pack(fill="x", padx=20)
        form.columnconfigure(1, weight=1)

        self.entries = {}
        parsed = self._parse(text)

        fields = [
            ("Дата:",          "date",   parsed.get("date","")),
            ("Маршрут:",       "route",  parsed.get("route","")),
            ("Сумма (₽):",     "amount", parsed.get("amount","")),
            ("№ Акта:",        "act",    parsed.get("act","")),
            ("Расстояние (км):","dist",  parsed.get("dist","")),
        ]

        for i, (lbl, key, val) in enumerate(fields):
            label(form, lbl, bg=BG, size=10).grid(row=i, column=0, sticky="w", pady=5)
            e = entry(form, width=38)
            e.insert(0, val)
            e.grid(row=i, column=1, pady=5, sticky="ew", padx=(10,0))
            self.entries[key] = e

        # VAT
        n = len(fields)
        label(form, "НДС:", bg=BG, size=10).grid(row=n, column=0, sticky="w", pady=5)
        self.vat_var = tk.StringVar(value=parsed.get("vat","0"))
        vf = tk.Frame(form, bg=BG)
        vf.grid(row=n, column=1, sticky="w", padx=(10,0))
        for val, lbl_text in [("0","Без НДС"),("5","НДС 5%")]:
            tk.Radiobutton(vf, text=lbl_text, variable=self.vat_var, value=val,
                          bg=BG, fg=TEXT, selectcolor=CARD,
                          activebackground=BG).pack(side="left", padx=4)

        btn_row = tk.Frame(self, bg=BG, padx=20, pady=12)
        btn_row.pack(fill="x", side="bottom")
        btn(btn_row, "✅ Добавить рейс", self._save, color=SUCCESS).pack(side="left")
        btn(btn_row, "✏️ Открыть полную форму", self._open_full, color=CARD).pack(side="left", padx=8)
        btn(btn_row, "Отмена", self.destroy, color=CARD).pack(side="right")

    def _parse(self, text):
        """Try to extract trip data from free-form text."""
        import re
        result = {}

        # Date patterns dd.mm.yyyy or dd/mm/yyyy
        date_m = re.search(r'\b(\d{2}[./]\d{2}[./]\d{4})\b', text)
        if date_m:
            result["date"] = date_m.group(1).replace("/",".")

        # Amount - look for number with optional spaces/commas followed by ₽ or руб
        amt_m = re.search(r'(\d[\d\s,\.]*)\s*[₽рРуб]', text)
        if amt_m:
            raw = amt_m.group(1).replace(" ","").replace(",",".")
            try: result["amount"] = str(float(raw))
            except: pass

        # Route - look for city→city or "от...до" patterns
        route_m = re.search(r'([А-ЯЁа-яё\w\s]+)\s*[-–—→]\s*([А-ЯЁа-яё\w\s]+)', text)
        if route_m:
            result["route"] = f"{route_m.group(1).strip()} — {route_m.group(2).strip()}"

        # Distance
        dist_m = re.search(r'(\d+)\s*км', text, re.IGNORECASE)
        if dist_m:
            result["dist"] = dist_m.group(1)

        # Act number
        act_m = re.search(r'[Аакт№#Nn]+\s*[:\s]?\s*(\d+)', text, re.IGNORECASE)
        if act_m:
            result["act"] = act_m.group(1)

        # VAT
        if "ндс" in text.lower() or "nds" in text.lower():
            result["vat"] = "5"

        return result

    def _save(self):
        try:
            total = float(self.entries["amount"].get().replace(",","").replace(" ",""))
        except Exception:
            messagebox.showerror("Ошибка","Введите корректную сумму"); return

        from .trips import calc_vat
        vat_rate = float(self.vat_var.get())
        no_vat, vat_amt, total = calc_vat(total, vat_rate)

        try: dist = float(self.entries["dist"].get().replace(",",""))
        except: dist = 0

        data = {
            "date":          self.entries["date"].get().strip(),
            "route":         self.entries["route"].get().strip(),
            "act_number":    self.entries["act"].get().strip(),
            "status":        "Запланирован",
            "vat_rate":      vat_rate,
            "income_no_vat": no_vat,
            "vat_amount":    vat_amt,
            "income_total":  total,
            "transport_type":"Своя",
            "distance":      dist,
        }
        self.db.add("trips", data)
        if self.on_save: self.on_save()
        messagebox.showinfo("Готово","Рейс добавлен! Откройте его для заполнения деталей.")
        self.destroy()

    def _open_full(self):
        """Pre-fill full trip dialog with parsed data."""
        try:
            total = float(self.entries["amount"].get().replace(",","").replace(" ",""))
        except: total = 0
        try: dist = float(self.entries["dist"].get())
        except: dist = 0

        pre = {
            "date":         self.entries["date"].get().strip(),
            "route":        self.entries["route"].get().strip(),
            "act_number":   self.entries["act"].get().strip(),
            "income_total": total,
            "vat_rate":     float(self.vat_var.get()),
            "distance":     dist,
            "status":       "Запланирован",
        }
        self.destroy()
        TripDialog(self.master, self.db, trip=pre, on_save=self.on_save)
