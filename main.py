import tkinter as tk
import sys
import os

# PyInstaller path fix
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
    WORK_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    WORK_DIR = BASE_DIR

os.chdir(WORK_DIR)
sys.path.insert(0, BASE_DIR)

# Data always lives in a fixed location, independent of where the
# app/exe is launched from (so updates/rebuilds never lose data).
DATA_DIR = os.path.join(os.path.expanduser("~"), "TransLogistData")
os.makedirs(DATA_DIR, exist_ok=True)
_ABS_DATA_FILE = os.path.join(DATA_DIR, "data.json")

# One-time migration: if an old data.json exists next to the app
# but nothing in the new fixed location yet, move it over.
_old_data = os.path.join(WORK_DIR, "data.json")
if os.path.exists(_old_data) and not os.path.exists(_ABS_DATA_FILE):
    try:
        import shutil as _shutil
        _shutil.copy2(_old_data, _ABS_DATA_FILE)
        _old_backups = os.path.join(WORK_DIR, "backups")
        if os.path.isdir(_old_backups):
            _shutil.copytree(_old_backups, os.path.join(DATA_DIR, "backups"),
                              dirs_exist_ok=True)
    except Exception:
        pass

# DPI awareness
try:
    from ctypes import windll
    try:    windll.shcore.SetProcessDpiAwareness(2)
    except: windll.shcore.SetProcessDpiAwareness(1)
except: pass

DB_FILE = _ABS_DATA_FILE

# ── Splash ────────────────────────────────────────────────────────
from splash import SplashScreen
SplashScreen().show()

# ── Auth ──────────────────────────────────────────────────────────
from modules.auth_screen import AuthScreen, load_session, clear_session
from modules.sync import SupabaseClient, SyncManager
from modules.permissions import PermissionManager

# ── Auto-updater ──────────────────────────────────────────────────
try:
    from updater import check_for_updates, show_update_dialog
    _UPDATER_OK = True
except Exception:
    _UPDATER_OK = False

# Try to restore saved session
session = load_session()
if not session:
    auth = AuthScreen()
    session = auth.show()
    if not session:
        sys.exit(0)

client = SupabaseClient(token=session["token"])

# ── Main App ──────────────────────────────────────────────────────
from modules.database import Database
from modules.ui_helpers import *


class App(tk.Tk):
    def __init__(self, session, client):
        super().__init__()
        self.session = session
        self.client  = client
        self.perms   = PermissionManager(session)
        self.title("ТрансЛогист — Управление грузоперевозками")
        self.geometry("1300x800")
        self.minsize(1100, 680)
        self.configure(bg="#111827")

        icon_path = os.path.join(BASE_DIR, "icon.ico")
        if os.path.exists(icon_path):
            try: self.iconbitmap(icon_path)
            except: pass

        try:
            from tkinter import font
            font.nametofont("TkDefaultFont").configure(family="Segoe UI", size=10)
            font.nametofont("TkTextFont").configure(family="Segoe UI", size=10)
        except: pass

        self.db   = Database(DB_FILE)
        self.sync = SyncManager(self.db, self.client)
        self.sync.set_user(session.get("user_id"), session.get("org_id"))

        self._build_ui()
        # Auto-sync on startup (pull from server)
        self.after(1500, self._auto_sync_on_start)
        # Check for updates 3 sec after launch (non-blocking)
        if _UPDATER_OK:
            self.after(4000, self._check_updates)


    def _auto_sync_on_start(self):
        """Auto pull data from server on startup."""
        import threading
        self._show_sync_status("🔄 Загрузка данных...")
        def _run():
            try:
                self.sync.pull_all()
                self.after(0, lambda: self._show_sync_status("✅ Данные загружены", success=True))
                self.after(0, lambda: self.pages[self._current_page].refresh())
                self.after(3000, lambda: self._show_sync_status(""))
            except Exception:
                self.after(0, lambda: self._show_sync_status(""))
        threading.Thread(target=_run, daemon=True).start()

    def _check_updates(self):
        check_for_updates(
            on_update_available=lambda v, c: self.after(
                0, lambda: show_update_dialog(self, v, c)
            )
        )

    def _initial_sync(self):
        """Manual sync - called only when user clicks sync button."""
        self._show_sync_status("🔄 Синхронизация...")
        import threading
        def _run():
            self.sync.pull_all()
            result = self.sync.push_all()
            ok = result[0] if isinstance(result, tuple) else result
            errors = result[1] if isinstance(result, tuple) and len(result) > 1 else []
            if ok:
                self.after(0, lambda: self._show_sync_status("✅ Готово", success=True))
                self.after(3000, lambda: self._show_sync_status(""))
            else:
                err_text = "; ".join(errors[:2]) if errors else "Неизвестная ошибка"
                self.after(0, lambda: self._show_sync_status(f"❌ {err_text}"))
                import tkinter.messagebox as mb
                msg = "Не удалось загрузить данные на сервер:\n\n" + "\n".join(errors)
                self.after(0, lambda: mb.showerror("Ошибка синхронизации", msg, parent=self))
            self.after(0, lambda: self.pages[self._current_page].refresh())
        threading.Thread(target=_run, daemon=True).start()

    def _show_sync_status(self, msg, success=False):
        color = SUCCESS if success else WARN
        if hasattr(self, "sync_lbl"):
            self.sync_lbl.configure(text=msg, fg=color)

    def _build_ui(self):
        # Import frames lazily for faster startup
        from modules.finances import FinancesFrame
        from modules.trucks import TrucksFrame
        from modules.drivers import DriversFrame
        from modules.trips import TripsFrame
        from modules.counterparties import CounterpartiesFrame
        from modules.documents import DocumentsFrame
        from modules.reports import ReportsFrame
        from modules.companies import CompaniesFrame
        from modules.users_frame import UsersFrame

        # Sidebar
        sidebar = tk.Frame(self, bg="#0d1117", width=215)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo
        logo_f = tk.Frame(sidebar, bg="#0d1117", pady=14)
        logo_f.pack(fill="x")
        tk.Label(logo_f, text="🚛", bg="#0d1117", fg="#3b82f6",
                 font=("Segoe UI", 18)).pack(side="left", padx=(14, 6))
        tk.Label(logo_f, text="ТрансЛогист", bg="#0d1117", fg="#f1f5f9",
                 font=("Segoe UI", 12, "bold")).pack(side="left")

        # User info
        user_f = tk.Frame(sidebar, bg="#111827", padx=12, pady=8)
        user_f.pack(fill="x", padx=8, pady=4)
        name  = session.get("name", "")
        role  = "👔 Начальник" if session.get("role") == "owner" else "👷 Сотрудник"
        tk.Label(user_f, text=name, bg="#111827", fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(user_f, text=role, bg="#111827", fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")

        # Sync status
        self.sync_lbl = tk.Label(sidebar, text="", bg="#0d1117", fg=WARN,
                                  font=("Segoe UI", 9), padx=14)
        self.sync_lbl.pack(fill="x")

        tk.Frame(sidebar, bg="#1e2435", height=1).pack(fill="x", padx=10, pady=6)

        self.nav_buttons = []
        self.pages       = {}
        self._current_page = "finances"

        self.content = tk.Frame(self, bg="#111827")
        self.content.pack(side="right", fill="both", expand=True)

        # Build sections based on permissions
        sections = []
        if self.perms.can("view_finances"):
            sections.append(("📊", "Финансы", "finances", FinancesFrame))
        sections.append(("🚛", "Фуры", "trucks", TrucksFrame))
        sections.append(("👤", "Водители", "drivers", DriversFrame))
        if self.perms.can("add_trips"):
            sections.append(("🗺️", "Рейсы", "trips", TripsFrame))
        sections.append(("🏢", "Контрагенты", "counterparties", CounterpartiesFrame))
        if self.perms.can("manage_docs"):
            sections.append(("📄", "Документы", "documents", DocumentsFrame))
        if self.perms.can("view_reports"):
            sections.append(("📈", "Отчёты", "reports", ReportsFrame))

        for icon, title, key, FrameClass in sections:
            frame = FrameClass(self.content, self.db)
            frame.place(relwidth=1, relheight=1)
            self.pages[key] = frame
            self._add_nav_btn(sidebar, icon, title, key)

        tk.Frame(sidebar, bg="#1e2435", height=1).pack(fill="x", padx=10, pady=4)

        # Companies
        frame = CompaniesFrame(self.content, self.db)
        frame.place(relwidth=1, relheight=1)
        self.pages["companies"] = frame
        self._add_nav_btn(sidebar, "🏦", "Компании", "companies")

        # Users (owner only)
        if self.perms.is_owner():
            frame = UsersFrame(self.content, self.db, self.session, self.client)
            frame.place(relwidth=1, relheight=1)
            self.pages["users"] = frame
            self._add_nav_btn(sidebar, "👥", "Команда", "users")

        # Bottom buttons
        tk.Frame(sidebar, bg="#1e2435", height=1).pack(
            fill="x", padx=10, pady=4, side="bottom")

        # Sync button
        sync_btn = tk.Button(sidebar, text="☁️  Синхронизировать",
                             bg="#0d1117", fg="#94a3b8",
                             relief="flat", font=("Segoe UI", 10),
                             padx=16, pady=8, cursor="hand2",
                             command=self._initial_sync)
        sync_btn.pack(side="bottom", fill="x", padx=8, pady=2)

        # Logout button
        logout_btn = tk.Button(sidebar, text="🚪  Выйти",
                               bg="#0d1117", fg="#94a3b8",
                               relief="flat", font=("Segoe UI", 10),
                               padx=16, pady=8, cursor="hand2",
                               command=self._logout)
        logout_btn.pack(side="bottom", fill="x", padx=8, pady=2)

        tk.Label(sidebar, text="v4.0.0", bg="#0d1117", fg="#374151",
                 font=("Segoe UI", 9)).pack(side="bottom", pady=4)

        self.show_page(list(self.pages.keys())[0])

    def _add_nav_btn(self, sidebar, icon, title, key):
        nav = tk.Frame(sidebar, bg="#0d1117", cursor="hand2")
        nav.pack(fill="x", padx=8, pady=1)
        icon_l  = tk.Label(nav, text=icon, bg="#0d1117", fg="#94a3b8",
                           font=("Segoe UI", 11), width=3)
        icon_l.pack(side="left", padx=(8, 4), pady=8)
        title_l = tk.Label(nav, text=title, bg="#0d1117", fg="#94a3b8",
                           font=("Segoe UI", 11), anchor="w")
        title_l.pack(side="left", fill="x", expand=True)
        for w in (nav, icon_l, title_l):
            w.bind("<Button-1>", lambda e, k=key: self.show_page(k))
            w.bind("<Enter>", lambda e, n=nav, i=icon_l, t=title_l: self._hover(n,i,t,True))
            w.bind("<Leave>", lambda e, n=nav, i=icon_l, t=title_l: self._hover(n,i,t,False))
        self.nav_buttons.append((key, nav, icon_l, title_l))

    def _hover(self, nav, icon_l, title_l, on):
        for k, n, i, t in self.nav_buttons:
            if n == nav and i.cget("fg") == "#ffffff":
                return
        bg = "#1e2435" if on else "#0d1117"
        fg = "#cbd5e1" if on else "#94a3b8"
        nav.configure(bg=bg)
        icon_l.configure(bg=bg, fg=fg)
        title_l.configure(bg=bg, fg=fg)


    def _logout(self):
        if tk.messagebox.askyesno("Выход", "Выйти из аккаунта?"):
            clear_session()
            self.destroy()

    def show_page(self, key):
        self._current_page = key
        for k, nav, icon_l, title_l in self.nav_buttons:
            if k == key:
                nav.configure(bg="#1e3a5f")
                icon_l.configure(bg="#1e3a5f", fg="#ffffff")
                title_l.configure(bg="#1e3a5f", fg="#ffffff",
                                  font=("Segoe UI", 11, "bold"))
            else:
                nav.configure(bg="#0d1117")
                icon_l.configure(bg="#0d1117", fg="#94a3b8")
                title_l.configure(bg="#0d1117", fg="#94a3b8",
                                  font=("Segoe UI", 11))
        self.pages[key].tkraise()
        self.pages[key].refresh()


if __name__ == "__main__":
    app = App(session, client)
    app.mainloop()
