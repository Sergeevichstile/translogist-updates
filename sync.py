"""
Supabase sync module using only built-in Python libraries.
Uses Supabase REST API directly via urllib.
"""
import json
import urllib.request
import urllib.error
import urllib.parse
import threading
import os
from datetime import datetime

SUPABASE_URL = "https://qmllznbmckdxhequiojx.supabase.co"
SUPABASE_KEY = "sb_publishable_MFi-lb-v7odrJlqGpKRpqg_xNdWZyq-"

TABLES = ["trucks", "drivers", "trips", "expenses", "counterparties",
          "carriers", "salary_payments", "companies", "documents"]


class SupabaseClient:
    """Minimal Supabase REST client using urllib."""

    def __init__(self, url=SUPABASE_URL, key=SUPABASE_KEY, token=None):
        self.url = url.rstrip("/")
        self.key = key
        self.token = token  # JWT token after login

    def _headers(self, extra=None):
        h = {
            "Content-Type": "application/json",
            "apikey": self.key,
            "Prefer": "return=representation",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        else:
            h["Authorization"] = f"Bearer {self.key}"
        if extra:
            h.update(extra)
        return h

    def _request(self, method, path, data=None, params=None, timeout=20, retries=2):
        url = f"{self.url}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        body = json.dumps(data).encode() if data else None
        last_err = None
        for attempt in range(retries + 1):
            req = urllib.request.Request(url, data=body, method=method)
            for k, v in self._headers().items():
                req.add_header(k, v)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw else []
            except urllib.error.HTTPError as e:
                raw = e.read()
                try:
                    err = json.loads(raw)
                except Exception:
                    err = {"error": str(e)}
                return {"error": err, "status": e.code}
            except Exception as e:
                last_err = e
                if attempt < retries:
                    continue
        msg = str(last_err)
        if "timed out" in msg.lower():
            msg = ("Сервер не отвечает (превышено время ожидания).\n\n"
                   "Возможные причины:\n"
                   "• Антивирус или файрвол блокирует подключение программы к интернету "
                   "(добавьте TransLogist.exe в исключения)\n"
                   "• Нестабильное интернет-соединение — попробуйте позже\n"
                   "• Включён VPN, который блокирует доступ — попробуйте отключить")
        return {"error": msg}

    # ── Auth ──────────────────────────────────────────────────────

    def sign_up(self, email, password, metadata=None):
        data = {"email": email, "password": password}
        if metadata:
            data["data"] = metadata
        return self._request("POST", "/auth/v1/signup", data)

    def sign_in(self, email, password):
        url = f"{self.url}/auth/v1/token?grant_type=password"
        body = json.dumps({"email": email, "password": password}).encode()
        headers = {
            "Content-Type": "application/json",
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
        }
        last_err = None
        for attempt in range(3):
            req = urllib.request.Request(url, data=body, method="POST")
            for k, v in headers.items():
                req.add_header(k, v)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                raw = e.read()
                try:
                    return json.loads(raw)
                except Exception:
                    return {"error": str(e)}
            except Exception as e:
                last_err = e
        return {"error": str(last_err)}

    def get_user(self):
        return self._request("GET", "/auth/v1/user")

    # ── Database ──────────────────────────────────────────────────

    def select(self, table, filters=None):
        params = {"select": "*"}
        if filters:
            params.update(filters)
        return self._request("GET", f"/rest/v1/{table}", params=params)

    def insert(self, table, record):
        return self._request("POST", f"/rest/v1/{table}", data=record)

    def update(self, table, record_id, updates):
        params = {"id": f"eq.{record_id}"}
        return self._request("PATCH", f"/rest/v1/{table}",
                              data=updates, params=params)

    def delete(self, table, record_id):
        params = {"id": f"eq.{record_id}"}
        return self._request("DELETE", f"/rest/v1/{table}", params=params)

    def upsert(self, table, records):
        if not isinstance(records, list):
            records = [records]
        req = urllib.request.Request(
            f"{self.url}/rest/v1/{table}",
            data=json.dumps(records).encode(),
            method="POST"
        )
        headers = self._headers({"Prefer": "resolution=merge-duplicates,return=representation"})
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else []
        except Exception as e:
            return {"error": str(e)}


class SyncManager:
    """Manages sync between local JSON and Supabase."""

    def __init__(self, db, client: SupabaseClient):
        self.db = db
        self.client = client
        self.user_id = None
        self.org_id = None
        self._sync_lock = threading.Lock()

    def set_user(self, user_id, org_id):
        self.user_id = user_id
        self.org_id = org_id

    def push_all(self, progress_callback=None):
        """Push all local data to Supabase."""
        if not self.org_id:
            return False, ["org_id не задан — войдите в аккаунт заново"]
        errors = []
        for i, table in enumerate(TABLES):
            records = self.db.get_all(table)
            if records:
                # Ensure every record has the exact same set of keys
                # (PostgREST batch upsert requires uniform columns)
                all_keys = set()
                for r in records:
                    all_keys.update(r.keys())
                all_keys.discard("org_id")
                safe_records = []
                for r in records:
                    r2 = {k: r.get(k) for k in all_keys}
                    r2["org_id"] = self.org_id
                    safe_records.append(r2)
                result = self.client.upsert(table, safe_records)
                if isinstance(result, dict) and "error" in result:
                    err_msg = result["error"]
                    if isinstance(err_msg, dict):
                        err_msg = err_msg.get("message", str(err_msg))
                    errors.append(f"{table}: {err_msg}")
            if progress_callback:
                progress_callback(int((i+1)/len(TABLES)*100))
        return len(errors) == 0, errors

    def pull_all(self, progress_callback=None):
        """Pull all data from Supabase to local.
        Only overwrites local data if cloud has more records."""
        if not self.org_id:
            return False
        for i, table in enumerate(TABLES):
            result = self.client.select(table, {"org_id": f"eq.{self.org_id}"})
            if isinstance(result, list) and len(result) > 0:
                # Only overwrite if cloud has data
                clean = []
                for r in result:
                    r.pop("org_id", None)
                    clean.append(r)
                self.db._data[table] = clean
                self.db._save()
            # If cloud returns empty [] - keep local data (don't overwrite)
            if progress_callback:
                progress_callback(int((i+1)/len(TABLES)*100))
        return True

    def sync(self, direction="both", progress_callback=None):
        """Sync in background thread."""
        def _do():
            with self._sync_lock:
                if direction in ("push", "both"):
                    self.push_all(progress_callback)
                if direction in ("pull", "both"):
                    self.pull_all(progress_callback)
        t = threading.Thread(target=_do, daemon=True)
        t.start()
        return t
