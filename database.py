import json
import os
import uuid
from datetime import datetime
from copy import deepcopy


DEFAULT = {
    "trucks": [],
    "drivers": [],
    "trips": [],
    "expenses": [],
    "incomes": [],
    "counterparties": [],
    "carriers": [],
    "documents": [],
    "salary_payments": [],
    "companies": [],
    "company_info": {},
    "meta": {"updated_at": ""}
}


class Database:
    def __init__(self, filepath="data.json"):
        # Always use absolute path
        self.filepath = os.path.abspath(filepath)
        self._data = deepcopy(DEFAULT)
        self._load()

    def _backup(self):
        """Create automatic backup on every launch."""
        if not os.path.exists(self.filepath):
            return
        try:
            backup_dir = os.path.join(os.path.dirname(self.filepath), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            from datetime import datetime
            stamp = datetime.now().strftime("%Y-%m-%d")
            backup_path = os.path.join(backup_dir, f"data_backup_{stamp}.json")
            if not os.path.exists(backup_path):
                import shutil
                shutil.copy2(self.filepath, backup_path)
            # Keep only last 30 backups
            backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("data_backup")])
            for old_backup in backups[:-30]:
                os.remove(os.path.join(backup_dir, old_backup))
        except Exception:
            pass

    def _load(self):
        self._backup()
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if not content:
                    return
                loaded = json.loads(content)
                for key in DEFAULT:
                    if key in loaded:
                        self._data[key] = loaded[key]
                # Migrate old company_info -> companies
                old = self._data.get("company_info", {})
                if old.get("name") and not self._data["companies"]:
                    old["id"] = self._new_id()
                    old["active"] = True
                    old["created_at"] = datetime.now().isoformat()
                    self._data["companies"].append(old)
                    self._data["company_info"] = {}
                    self._save()
            except Exception:
                pass

    def _save(self):
        self._data["meta"]["updated_at"] = datetime.now().isoformat()
        # Write without indent for speed (saves ~30% time on large files)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, separators=(',', ':'))

    def _new_id(self):
        return str(uuid.uuid4())[:8]

    # ── Generic CRUD ──────────────────────────────────────────────

    def get_all(self, table: str):
        return list(self._data.get(table, []))

    def get_by_id(self, table: str, item_id: str):
        for item in self._data.get(table, []):
            if item.get("id") == item_id:
                return item
        return None

    def add(self, table: str, record: dict):
        record = dict(record)
        if "id" not in record:
            record["id"] = self._new_id()
        if "created_at" not in record:
            record["created_at"] = datetime.now().isoformat()
        self._data[table].append(record)
        self._save()
        return record

    def update(self, table: str, item_id: str, updates: dict):
        for i, item in enumerate(self._data[table]):
            if item.get("id") == item_id:
                self._data[table][i].update(updates)
                self._save()
                return self._data[table][i]
        return None

    def delete(self, table: str, item_id: str):
        self._data[table] = [x for x in self._data[table] if x.get("id") != item_id]
        self._save()

    # ── Companies ─────────────────────────────────────────────────

    def get_active_company(self):
        for co in self._data["companies"]:
            if co.get("active"):
                return dict(co)
        if self._data["companies"]:
            return dict(self._data["companies"][0])
        return {}

    def set_active_company_by_name(self, name: str):
        for i, co in enumerate(self._data["companies"]):
            self._data["companies"][i]["active"] = (co.get("name") == name)
        self._save()

    def get_active_company_subs(self):
        ci = self.get_active_company()
        return {
            "{{КОМПАНИЯ}}":      ci.get("name", "________________"),
            "{{ИНН_КОМПАНИИ}}":  ci.get("inn", "________________"),
            "{{КПП_КОМПАНИИ}}":  ci.get("kpp", "________________"),
            "{{ОГРН_КОМПАНИИ}}": ci.get("ogrn", "________________"),
            "{{АДРЕС_КОМПАНИИ}}": ci.get("address", "________________"),
            "{{БАНК_КОМПАНИИ}}": ci.get("bank", "________________"),
            "{{РС_КОМПАНИИ}}":   ci.get("rs", "________________"),
            "{{БИК_КОМПАНИИ}}":  ci.get("bik", "________________"),
            "{{КС_КОМПАНИИ}}":   ci.get("ks", "________________"),
            "{{ДИРЕКТОР}}":      ci.get("director", "________________"),
            "{{ТЕЛЕФОН_КОМПАНИИ}}": ci.get("phone", "________________"),
            "{{EMAIL_КОМПАНИИ}}": ci.get("email", "________________"),
        }

    # Legacy compat
    def get_company_info(self):
        return self.get_active_company()

    def set_company_info(self, info: dict):
        active = self.get_active_company()
        if active.get("id"):
            self.update("companies", active["id"], info)
        else:
            info["active"] = True
            self.add("companies", info)

    # ── Finance helpers ───────────────────────────────────────────

    def total_income(self, month=None, year=None):
        trips = self._filter_by_period(self._data["trips"], month, year)
        return sum(t.get("income_total", 0) for t in trips)

    def total_expense(self, month=None, year=None):
        expenses = self._filter_by_period(self._data["expenses"], month, year)
        base = sum(e.get("amount", 0) for e in expenses)
        trips = self._filter_by_period(self._data["trips"], month, year)
        carrier_costs = sum(t.get("carrier_cost", 0) for t in trips if t.get("carrier_id"))
        salaries = self._filter_by_period(self._data.get("salary_payments", []), month, year)
        sal_total = sum(s.get("amount", 0) for s in salaries)
        # Add km-based driver salary costs
        km_salary = self._calc_km_salary(trips)
        return base + carrier_costs + sal_total + km_salary

    def _calc_km_salary(self, trips):
        """Calculate total driver salary based on km rate."""
        drv_map = {d["id"]: d for d in self._data.get("drivers", [])}
        total = 0
        for t in trips:
            drv_id = t.get("driver_id")
            if not drv_id: continue
            drv = drv_map.get(drv_id)
            if not drv: continue
            if drv.get("rate_type","km") == "km" and drv.get("rate",0) and t.get("distance",0):
                total += drv["rate"] * t["distance"]
        return round(total, 2)

    def salary_fund_summary(self, month=None, year=None):
        """Returns breakdown of salary costs."""
        trips = self._filter_by_period(self._data["trips"], month, year)
        drv_map = {d["id"]: d for d in self._data.get("drivers", [])}
        result = []
        totals = {}
        for t in trips:
            drv_id = t.get("driver_id")
            if not drv_id: continue
            drv = drv_map.get(drv_id)
            if not drv: continue
            if drv.get("rate_type","km") == "km" and drv.get("rate",0):
                dist = t.get("distance",0) or 0
                sal  = round(drv["rate"] * dist, 2)
            else:
                sal = drv.get("rate",0) or 0
            if drv_id not in totals:
                totals[drv_id] = {"name": drv.get("name",""), "trips": 0,
                                   "km": 0, "salary": 0,
                                   "rate": drv.get("rate",0),
                                   "rate_type": drv.get("rate_type","km")}
            totals[drv_id]["trips"]  += 1
            totals[drv_id]["km"]     += t.get("distance",0) or 0
            totals[drv_id]["salary"] += sal
        return list(totals.values())

    def net_profit(self, month=None, year=None):
        return self.total_income(month, year) - self.total_expense(month, year)

    def vat_summary(self, month=None, year=None):
        trips = self._filter_by_period(self._data["trips"], month, year)
        vat5 = sum(t.get("vat_amount", 0) for t in trips if t.get("vat_rate", 0) == 5)
        no_vat = sum(t.get("income_total", 0) for t in trips if t.get("vat_rate", 0) == 0)
        return {"vat_5_total": round(vat5, 2), "no_vat_total": round(no_vat, 2)}

    def monthly_stats(self):
        from collections import defaultdict
        stats = defaultdict(lambda: {"income": 0, "expense": 0})
        for t in self._data["trips"]:
            key = self._period_key(t.get("date", ""))
            if key:
                stats[key]["income"] += t.get("income_total", 0)
                stats[key]["expense"] += t.get("carrier_cost", 0)
        for e in self._data["expenses"]:
            key = self._period_key(e.get("date", ""))
            if key:
                stats[key]["expense"] += e.get("amount", 0)
        for s in self._data.get("salary_payments", []):
            key = self._period_key(s.get("date", ""))
            if key:
                stats[key]["expense"] += s.get("amount", 0)
        result = []
        for key in sorted(stats.keys()):
            m, y = key
            inc = round(stats[key]["income"], 2)
            exp = round(stats[key]["expense"], 2)
            result.append({"month": m, "year": y, "income": inc,
                           "expense": exp, "profit": round(inc - exp, 2)})
        return result

    def _period_key(self, date_str):
        try:
            parts = date_str.split(".")
            return (int(parts[1]), int(parts[2]))
        except Exception:
            return None

    def _filter_by_period(self, items, month, year):
        if month is None and year is None:
            return items
        result = []
        for item in items:
            key = self._period_key(item.get("date", ""))
            if key:
                m, y = key
                if (month is None or m == month) and (year is None or y == year):
                    result.append(item)
        return result
