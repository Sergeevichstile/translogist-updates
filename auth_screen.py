import tkinter as tk
from tkinter import messagebox
import threading
import json
import os
from .ui_helpers import *
from .sync import SupabaseClient

SESSION_FILE = "session.json"

def load_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_session(data):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f)

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)


class AuthScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ТрансЛогист — Вход")
        self.resizable(False, False)
        self.configure(bg="#0f1729")
        self.result = None
        self.client = SupabaseClient()
        self._mode = "login"

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        if os.path.exists("icon.ico"):
            try: self.iconbitmap("icon.ico")
            except Exception: pass

        self._show_login()

    # ── Helpers ───────────────────────────────────────────────────

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def _center(self, w, h):
        self.geometry(f"{w}x{h}")
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _logo(self, parent):
        f = tk.Frame(parent, bg="#0f1729", pady=20)
        f.pack(fill="x")
        tk.Label(f, text="🚛", bg="#0f1729", fg="#3b82f6",
                 font=("Segoe UI", 32)).pack()
        tk.Label(f, text="ТрансЛогист", bg="#0f1729", fg="#f1f5f9",
                 font=("Segoe UI", 18, "bold")).pack()
        tk.Label(f, text="Управление грузоперевозками", bg="#0f1729",
                 fg="#64748b", font=("Segoe UI", 9)).pack()

    def _input(self, parent, label_text, show=None):
        tk.Label(parent, text=label_text, bg="#1e2435", fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 3))
        e = tk.Entry(parent, bg="#111827", fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=("Segoe UI", 11),
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT, show=show or "")
        e.pack(fill="x", ipady=8)
        return e

    def _status_lbl(self, parent):
        lbl = tk.Label(parent, text="", bg="#1e2435", fg=DANGER,
                       font=("Segoe UI", 9), wraplength=360)
        lbl.pack(pady=(6, 0))
        return lbl

    def _submit_btn(self, parent, text, command):
        b = tk.Button(parent, text=text, bg=ACCENT, fg=WHITE,
                      relief="flat", font=("Segoe UI", 11, "bold"),
                      pady=10, cursor="hand2", command=command)
        b.pack(fill="x", pady=(14, 0))
        return b

    def _link_btn(self, parent, text, command):
        b = tk.Button(parent, text=text, bg="#1e2435", fg="#60a5fa",
                      relief="flat", font=("Segoe UI", 9),
                      cursor="hand2", command=command)
        b.pack(pady=(8, 0))
        return b

    # ── Login screen ──────────────────────────────────────────────

    def _show_login(self):
        self._clear()
        self._center(460, 520)
        self._mode = "login"

        self._logo(self)

        # Tabs
        tab_f = tk.Frame(self, bg="#0d1117", pady=3, padx=3)
        tab_f.pack(fill="x", padx=32)
        for mode, title in [("login","Войти"), ("register","Регистрация")]:
            active = mode == "login"
            tk.Button(tab_f, text=title,
                      bg=ACCENT if active else "#0d1117",
                      fg=WHITE, relief="flat",
                      font=("Segoe UI", 10, "bold"),
                      padx=20, pady=7, cursor="hand2",
                      command=self._show_login if mode=="login" else self._show_register
                      ).pack(side="left", expand=True, fill="x", padx=2)

        card = tk.Frame(self, bg="#1e2435", padx=28, pady=4)
        card.pack(fill="x", padx=32, pady=8)

        self.email_e = self._input(card, "Email:")
        self.pass_e  = self._input(card, "Пароль:", show="•")
        self.status  = self._status_lbl(card)
        self.sub_btn = self._submit_btn(card, "Войти", self._do_login)
        self._link_btn(card, "🔑  Забыли пароль?", self._show_forgot)
        self.bind("<Return>", lambda e: self._do_login())

    # ── Register screen ───────────────────────────────────────────

    def _show_register(self):
        self._clear()
        self._center(480, 700)
        self._mode = "register"

        # Tabs at top (outside scroll)
        tab_f = tk.Frame(self, bg="#0d1117", pady=3, padx=3)
        tab_f.pack(fill="x", padx=32, pady=(8,0))
        for mode, title in [("login","Войти"), ("register","Регистрация")]:
            active = mode == "register"
            tk.Button(tab_f, text=title,
                      bg=ACCENT if active else "#0d1117",
                      fg=WHITE, relief="flat",
                      font=("Segoe UI", 10, "bold"),
                      padx=20, pady=7, cursor="hand2",
                      command=self._show_login if mode=="login" else self._show_register
                      ).pack(side="left", expand=True, fill="x", padx=2)

        # Scrollable area
        outer = tk.Frame(self, bg="#0f1729")
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg="#0f1729", highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg="#0f1729")
        win = canvas.create_window((0,0), window=inner, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win, width=canvas.winfo_width())
        inner.bind("<Configure>", _resize)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Logo inside scroll
        f = tk.Frame(inner, bg="#0f1729", pady=16)
        f.pack(fill="x")
        tk.Label(f, text="🚛", bg="#0f1729", fg="#3b82f6",
                 font=("Segoe UI", 28)).pack()
        tk.Label(f, text="ТрансЛогист", bg="#0f1729", fg="#f1f5f9",
                 font=("Segoe UI", 16, "bold")).pack()

        card = tk.Frame(inner, bg="#1e2435", padx=28, pady=8)
        card.pack(fill="x", padx=32, pady=8)

        # Role
        tk.Label(card, text="Роль:", bg="#1e2435", fg=MUTED,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 4))
        self.role_var = tk.StringVar(value="owner")
        role_f = tk.Frame(card, bg="#1e2435")
        role_f.pack(fill="x")
        for val, lbl in [("owner","👔  Начальник"), ("employee","👷  Сотрудник")]:
            rf = tk.Frame(role_f, bg="#111827", padx=10, pady=8, cursor="hand2")
            rf.pack(side="left", expand=True, fill="x", padx=(0,4))
            rb = tk.Radiobutton(rf, text=lbl, variable=self.role_var, value=val,
                               bg="#111827", fg=TEXT, selectcolor="#1e3a5f",
                               activebackground="#111827",
                               font=("Segoe UI", 10, "bold"),
                               command=self._toggle_role_fields)
            rb.pack()
            rf.bind("<Button-1>", lambda e, v=val: self.role_var.set(v) or self._toggle_role_fields())

        # Dynamic fields
        self.dyn_frame = tk.Frame(card, bg="#1e2435")
        self.dyn_frame.pack(fill="x")

        self.name_e   = self._input(card, "Ваше имя:")
        self.email_e  = self._input(card, "Email:")
        self.pass_e   = self._input(card, "Пароль:", show="•")
        self.pass2_e  = self._input(card, "Повторите пароль:", show="•")
        self.status   = self._status_lbl(card)
        self.sub_btn  = self._submit_btn(card, "✅  Зарегистрироваться", self._do_register)

        self._link_btn(card, "Уже есть аккаунт? Войти", self._show_login)

        tk.Frame(inner, bg="#0f1729", height=20).pack()

        self._toggle_role_fields()
        self.bind("<Return>", lambda e: self._do_register())

    def _toggle_role_fields(self):
        for w in self.dyn_frame.winfo_children():
            w.destroy()
        role = self.role_var.get()
        if role == "owner":
            tk.Label(self.dyn_frame, text="Название компании:", bg="#1e2435",
                     fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(10,3))
            self.company_e = tk.Entry(self.dyn_frame, bg="#111827", fg=TEXT,
                                       insertbackground=TEXT, relief="flat",
                                       font=("Segoe UI", 11),
                                       highlightthickness=1,
                                       highlightbackground=BORDER,
                                       highlightcolor=ACCENT)
            self.company_e.pack(fill="x", ipady=8)
        else:
            tk.Label(self.dyn_frame, text="Код приглашения от начальника:",
                     bg="#1e2435", fg=MUTED, font=("Segoe UI", 10)).pack(
                     anchor="w", pady=(10,3))
            self.invite_e = tk.Entry(self.dyn_frame, bg="#111827", fg=TEXT,
                                      insertbackground=TEXT, relief="flat",
                                      font=("Segoe UI", 11),
                                      highlightthickness=1,
                                      highlightbackground=BORDER,
                                      highlightcolor=ACCENT)
            self.invite_e.pack(fill="x", ipady=8)

    # ── Forgot password screen ────────────────────────────────────

    def _show_forgot(self):
        self._clear()
        self._center(460, 400)

        self._logo(self)

        card = tk.Frame(self, bg="#1e2435", padx=28, pady=16)
        card.pack(fill="x", padx=32, pady=8)

        tk.Label(card, text="Восстановление пароля", bg="#1e2435",
                 fg=TEXT, font=("Segoe UI", 13, "bold")).pack(pady=(0,4))
        tk.Label(card, text="Введите email — отправим ссылку для сброса пароля",
                 bg="#1e2435", fg=MUTED, font=("Segoe UI", 9),
                 wraplength=360).pack()

        self.forgot_email = self._input(card, "Email:")
        self.status = self._status_lbl(card)
        self._submit_btn(card, "Отправить письмо", self._do_forgot)
        self._link_btn(card, "← Вернуться ко входу", self._show_login)

    # ── Verify email screen ───────────────────────────────────────

    def _show_verify(self, email):
        self._clear()
        self._center(460, 440)
        self._mode = "verify"
        self.configure(bg="#0f1729")

        # Logo compact
        f = tk.Frame(self, bg="#0f1729", pady=12)
        f.pack(fill="x")
        tk.Label(f, text="🚛  ТрансЛогист", bg="#0f1729", fg="#f1f5f9",
                 font=("Segoe UI", 14, "bold")).pack()

        card = tk.Frame(self, bg="#1e2435", padx=28, pady=14)
        card.pack(fill="x", padx=32)

        tk.Label(card, text="✉️  Введите код из письма", bg="#1e2435",
                 fg=TEXT, font=("Segoe UI", 13, "bold")).pack(pady=(0,4))
        tk.Label(card, text="Мы отправили 6-значный код на:", bg="#1e2435",
                 fg=MUTED, font=("Segoe UI", 10)).pack()
        tk.Label(card, text=email, bg="#1e2435", fg="#60a5fa",
                 font=("Segoe UI", 10, "bold")).pack(pady=(2,10))

        tk.Label(card, text="Код подтверждения:", bg="#1e2435",
                 fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(0,3))

        self.otp_e = tk.Entry(card, bg="#111827", fg="#3b82f6",
                               insertbackground=TEXT, relief="flat",
                               font=("Segoe UI", 26, "bold"),
                               highlightthickness=2, highlightbackground=BORDER,
                               highlightcolor=ACCENT, justify="center")
        self.otp_e.pack(fill="x", ipady=10)
        self.otp_e.focus_set()

        tk.Label(card, text="Код действует 10 минут", bg="#1e2435",
                 fg=MUTED, font=("Segoe UI", 9)).pack(pady=(4,0))

        self.status = self._status_lbl(card)

        # Confirm button - always visible
        btn_frame = tk.Frame(self, bg="#0f1729", padx=32, pady=12)
        btn_frame.pack(fill="x")
        self.sub_btn = tk.Button(btn_frame, text="✅  Подтвердить код",
                                  bg=ACCENT, fg=WHITE, relief="flat",
                                  font=("Segoe UI", 12, "bold"),
                                  pady=12, cursor="hand2",
                                  command=lambda: self._do_verify(email))
        self.sub_btn.pack(fill="x")

        links = tk.Frame(self, bg="#0f1729")
        links.pack(fill="x", padx=32)
        tk.Button(links, text="Отправить код повторно",
                  bg="#0f1729", fg="#60a5fa", relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=lambda: self._resend_verification(email)).pack(pady=2)
        tk.Button(links, text="← Вернуться к регистрации",
                  bg="#0f1729", fg="#60a5fa", relief="flat",
                  font=("Segoe UI", 9), cursor="hand2",
                  command=self._show_register).pack()

        self.bind("<Return>", lambda e: self._do_verify(email))

    # ── Actions ───────────────────────────────────────────────────

    def _set_status(self, msg, color=DANGER):
        if hasattr(self, "status"):
            self.status.configure(text=msg, fg=color)

    def _set_loading(self, loading):
        if hasattr(self, "sub_btn"):
            if loading:
                self.sub_btn.configure(state="disabled", text="Подождите...")
            else:
                texts = {"login":"Войти","register":"Зарегистрироваться",
                         "forgot":"Отправить письмо"}
                self.sub_btn.configure(state="normal",
                                       text=texts.get(self._mode,"OK"))

    def _do_login(self):
        email    = self.email_e.get().strip()
        password = self.pass_e.get().strip()
        if not email or not password:
            self._set_status("Заполните все поля"); return
        self._set_loading(True)
        threading.Thread(target=self._login_thread,
                         args=(email, password), daemon=True).start()

    def _login_thread(self, email, password):
        result = self.client.sign_in(email, password)
        if "access_token" not in result:
            msg = result.get("error_description") or result.get("error") or "Неверный email или пароль"
            if isinstance(msg, dict): msg = msg.get("message","Ошибка")
            self.after(0, lambda: self._set_status(str(msg)))
            self.after(0, lambda: self._set_loading(False))
            return
        token = result["access_token"]
        user  = result.get("user", {})
        meta  = user.get("user_metadata", {})
        session = {
            "token":    token,
            "user_id":  user.get("id"),
            "email":    email,
            "name":     meta.get("name", email.split("@")[0]),
            "role":     meta.get("role", "owner"),
            "org_id":   meta.get("org_id"),
            "org_name": meta.get("org_name",""),
        }
        save_session(session)
        self.result = session
        self.after(50, self.destroy)

    def _do_register(self):
        name  = self.name_e.get().strip()
        email = self.email_e.get().strip()
        pwd1  = self.pass_e.get().strip()
        pwd2  = self.pass2_e.get().strip()
        role  = self.role_var.get()

        if not name:
            self._set_status("Введите ваше имя"); return
        if not email or "@" not in email:
            self._set_status("Введите корректный email"); return
        if len(pwd1) < 6:
            self._set_status("Пароль минимум 6 символов"); return
        if pwd1 != pwd2:
            self._set_status("Пароли не совпадают"); return

        import uuid
        org_id   = None
        org_name = ""

        if role == "owner":
            org_name = getattr(self, "company_e", None)
            org_name = org_name.get().strip() if org_name else ""
            if not org_name:
                self._set_status("Введите название компании"); return
            org_id = str(uuid.uuid4())
        else:
            invite = getattr(self, "invite_e", None)
            invite = invite.get().strip() if invite else ""
            if not invite:
                self._set_status("Введите код приглашения"); return
            org_id = invite

        self._set_loading(True)
        meta = {"name": name, "role": role,
                "org_id": org_id, "org_name": org_name}
        threading.Thread(target=self._register_thread,
                         args=(email, pwd1, meta), daemon=True).start()

    def _register_thread(self, email, password, meta):
        result = self.client.sign_up(email, password, meta)
        if "error" in result:
            msg = result.get("error",{})
            if isinstance(msg, dict): msg = msg.get("message","Ошибка регистрации")
            self.after(0, lambda: self._set_status(str(msg)))
            self.after(0, lambda: self._set_loading(False))
            return
        # If we got access_token directly - email confirmation is disabled, login immediately
        if "access_token" in result:
            user  = result.get("user", {})
            meta2 = user.get("user_metadata", {})
            session = {
                "token":    result["access_token"],
                "user_id":  user.get("id"),
                "email":    email,
                "name":     meta2.get("name", email.split("@")[0]),
                "role":     meta2.get("role", "owner"),
                "org_id":   meta2.get("org_id"),
                "org_name": meta2.get("org_name",""),
            }
            save_session(session)
            self.result = session
            self.after(0, self.destroy)
            return
        # Email confirmation enabled - show OTP screen
        self.after(0, lambda: self._show_verify(email))

    def _do_verify(self, email):
        token = self.otp_e.get().strip()
        if len(token) != 6 or not token.isdigit():
            self._set_status("Введите 6-значный код из письма"); return
        self._set_loading(True)
        def _verify():
            result = self.client._request("POST", "/auth/v1/verify",
                                          data={"type": "signup",
                                                "email": email,
                                                "token": token})
            if "access_token" not in result:
                msg = result.get("error_description") or result.get("error") or "Неверный код"
                if isinstance(msg, dict): msg = msg.get("message", "Неверный код")
                self.after(0, lambda: self._set_status(str(msg)))
                self.after(0, lambda: self._set_loading(False))
                return
            # Success - save session and enter app
            user = result.get("user", {})
            meta = user.get("user_metadata", {})
            session = {
                "token":    result["access_token"],
                "user_id":  user.get("id"),
                "email":    email,
                "name":     meta.get("name", email.split("@")[0]),
                "role":     meta.get("role", "owner"),
                "org_id":   meta.get("org_id"),
                "org_name": meta.get("org_name", ""),
            }
            save_session(session)
            self.result = session
            self.after(0, self.destroy)
        threading.Thread(target=_verify, daemon=True).start()

    def _do_forgot(self):
        self._mode = "forgot"
        email = self.forgot_email.get().strip()
        if not email or "@" not in email:
            self._set_status("Введите корректный email"); return
        self._set_loading(True)
        def _send():
            result = self.client._request("POST", "/auth/v1/recover",
                                          data={"email": email})
            self.after(0, lambda: self._set_status(
                f"✅ Письмо отправлено на {email}", SUCCESS))
            self.after(0, lambda: self._set_loading(False))
        threading.Thread(target=_send, daemon=True).start()

    def _resend_verification(self, email):
        self.client._request("POST", "/auth/v1/resend",
                              data={"type": "signup", "email": email})
        messagebox.showinfo("Отправлено", f"Новый код отправлен на {email}")

    def show(self):
        self.mainloop()
        return self.result
