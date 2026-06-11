import tkinter as tk
from tkinter import messagebox
import threading
from .ui_helpers import *
from .sync import SupabaseClient
from .permissions import PERMISSION_LABELS, DEFAULT_PERMISSIONS


class UsersFrame(tk.Frame):
    """Owner panel — manage team members and their permissions."""

    def __init__(self, parent, db, session, client: SupabaseClient):
        super().__init__(parent, bg=BG)
        self.db      = db
        self.session = session
        self.client  = client
        self.members = []
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG, padx=24, pady=14)
        hdr.pack(fill="x")
        label(hdr, "👥 Команда и доступ", size=16, bold=True, bg=BG).pack(side="left")
        btn(hdr, "🔄 Обновить", self.refresh, color=CARD).pack(side="right")

        # Invite code banner
        org_id = self.session.get("org_id", "")
        banner = tk.Frame(self, bg="#0f2d1f", padx=20, pady=12)
        banner.pack(fill="x", padx=24, pady=(0, 12))
        label(banner, "📋  Код для приглашения сотрудников:", bg="#0f2d1f",
              color="#86efac", bold=True).pack(anchor="w")
        code_frame = tk.Frame(banner, bg="#0f2d1f")
        code_frame.pack(fill="x", pady=(6, 0))
        code_lbl = tk.Label(code_frame, text=org_id, bg="#111827",
                            fg="#34d399", font=("Consolas", 11),
                            padx=12, pady=6)
        code_lbl.pack(side="left")
        btn(code_frame, "📋 Копировать",
            lambda: self._copy(org_id), color="#166534", fg="#86efac").pack(
            side="left", padx=8)
        label(banner, "Отправьте этот код сотруднику при регистрации",
              bg="#0f2d1f", color="#4ade80", size=9).pack(anchor="w")

        wrap = tk.Frame(self, bg=BG, padx=24)
        wrap.pack(fill="both", expand=True)

        tbl, self.tree = make_table(wrap,
            ["Имя", "Email", "Роль", "Статус", ""],
            [180, 220, 100, 100, 80])
        tbl.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self._edit_permissions)

    def _copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Скопировано", "Код скопирован в буфер обмена!")

    def _edit_permissions(self, e=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0])["values"]
        email = vals[1]
        member = next((m for m in self.members if m.get("email") == email), None)
        if member:
            PermissionsDialog(self, member, self.client, self.session)

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        def _load():
            org_id = self.session.get("org_id", "")
            # Get users with same org_id from metadata
            # Using Supabase admin API to list users
            result = self.client._request("GET", "/auth/v1/admin/users",
                                          params={"page": 1, "per_page": 50})
            members = []
            if isinstance(result, dict) and "users" in result:
                for u in result["users"]:
                    meta = u.get("user_metadata", {})
                    if meta.get("org_id") == org_id:
                        members.append({
                            "id":    u.get("id"),
                            "email": u.get("email"),
                            "name":  meta.get("name", u.get("email","")),
                            "role":  meta.get("role", "employee"),
                            "permissions": meta.get("permissions", {}),
                        })
            self.members = members
            self.after(0, self._populate)

        threading.Thread(target=_load, daemon=True).start()

    def _populate(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for m in self.members:
            role_lbl = "Начальник" if m["role"] == "owner" else "Сотрудник"
            self.tree.insert("", "end", values=(
                m.get("name",""), m.get("email",""),
                role_lbl, "Активен", "⚙️"
            ))


class PermissionsDialog(tk.Toplevel):
    def __init__(self, parent, member, client, session):
        super().__init__(parent)
        self.member  = member
        self.client  = client
        self.session = session
        self.title(f"Права: {member.get('name','')}")
        self.geometry("400x480")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        label(self, f"Сотрудник: {self.member.get('name','')}",
              bold=True, bg=BG, size=12).pack(anchor="w", padx=20, pady=(16, 4))
        label(self, self.member.get("email",""),
              bg=BG, color=MUTED, size=10).pack(anchor="w", padx=20, pady=(0, 12))

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=20, pady=4)
        label(self, "Разрешения:", bold=True, bg=BG).pack(
            anchor="w", padx=20, pady=(8, 4))

        current = self.member.get("permissions", DEFAULT_PERMISSIONS.copy())
        self.vars = {}

        scroll_frame = tk.Frame(self, bg=BG)
        scroll_frame.pack(fill="both", expand=True, padx=20)

        for key, lbl in PERMISSION_LABELS.items():
            if key == "manage_users":
                continue
            row = tk.Frame(scroll_frame, bg=CARD, padx=12, pady=8)
            row.pack(fill="x", pady=2)
            var = tk.BooleanVar(value=current.get(key, DEFAULT_PERMISSIONS.get(key, True)))
            self.vars[key] = var
            tk.Checkbutton(row, text=lbl, variable=var,
                          bg=CARD, fg=TEXT, selectcolor=BG2,
                          activebackground=CARD,
                          font=("Segoe UI", 10)).pack(side="left")

        btn(self, "💾 Сохранить права", self._save, color=SUCCESS).pack(
            fill="x", padx=20, pady=16)

    def _save(self):
        perms = {k: v.get() for k, v in self.vars.items()}
        # Update user metadata via Supabase admin
        user_id = self.member.get("id")
        result  = self.client._request("PUT", f"/auth/v1/admin/users/{user_id}",
                                       data={"user_metadata": {"permissions": perms}})
        if isinstance(result, dict) and "error" in result:
            messagebox.showerror("Ошибка", "Не удалось сохранить права")
        else:
            messagebox.showinfo("Готово", "Права сохранены!")
            self.destroy()
