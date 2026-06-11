import tkinter as tk
from tkinter import messagebox
import threading
import json
import os
import sys
import zipfile
import shutil

# URL репозитория
GITHUB_USER = "Sergeevichstile"
GITHUB_REPO = "translogist-updates"
RAW_BASE    = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main"
VERSION_URL = f"{RAW_BASE}/version.json"
ZIP_URL     = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/main.zip"

CURRENT_VERSION = "4.0.0"   # ← будем менять при каждом обновлении


def get_app_dir():
    """Папка где лежит приложение."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def check_for_updates(on_update_available=None, silent=True):
    """
    Проверяет наличие обновлений в фоновом потоке.
    on_update_available(version, changelog) — вызывается если есть обновление.
    """
    def _check():
        try:
            import urllib.request
            with urllib.request.urlopen(VERSION_URL, timeout=5) as r:
                data = json.loads(r.read().decode())
            latest  = data.get("version", "0.0.0")
            changes = data.get("changelog", "Исправления и улучшения")
            if _newer(latest, CURRENT_VERSION):
                if on_update_available:
                    on_update_available(latest, changes)
        except Exception:
            pass   # нет интернета — молча пропускаем

    t = threading.Thread(target=_check, daemon=True)
    t.start()


def _newer(v1, v2):
    """True если v1 > v2  (формат 'X.Y.Z')."""
    try:
        return tuple(int(x) for x in v1.split(".")) > \
               tuple(int(x) for x in v2.split("."))
    except Exception:
        return False


def download_and_install(parent_window, version, on_done=None):
    """Скачивает zip с GitHub и заменяет файлы modules/ и main.py."""

    dlg = tk.Toplevel(parent_window)
    dlg.title("Обновление")
    dlg.geometry("420x160")
    dlg.resizable(False, False)
    dlg.grab_set()
    try:
        dlg.configure(bg="#1a1d2e")
    except Exception:
        pass

    lbl = tk.Label(dlg, text=f"⬇️  Скачиваем версию {version}...",
                   font=("Segoe UI", 11), bg="#1a1d2e", fg="white")
    lbl.pack(pady=(24, 8))

    bar_frame = tk.Frame(dlg, bg="#2a2d45", width=360, height=18)
    bar_frame.pack(pady=4)
    bar_frame.pack_propagate(False)
    bar = tk.Frame(bar_frame, bg="#6366f1", width=0, height=18)
    bar.place(x=0, y=0, relheight=1)

    status = tk.Label(dlg, text="Подготовка...", font=("Segoe UI", 9),
                      bg="#1a1d2e", fg="#94a3b8")
    status.pack()

    def _set_progress(pct, text=""):
        bar.place(x=0, y=0, relheight=1, width=int(360 * pct / 100))
        if text: status.config(text=text)
        dlg.update_idletasks()

    def _install():
        try:
            import urllib.request
            import tempfile

            app_dir = get_app_dir()
            tmp_zip = os.path.join(tempfile.gettempdir(), "translogist_update.zip")
            tmp_dir = os.path.join(tempfile.gettempdir(), "translogist_update")

            # 1. Скачать zip
            _set_progress(10, "Скачиваем архив...")
            urllib.request.urlretrieve(ZIP_URL, tmp_zip)
            _set_progress(50, "Распаковываем...")

            # 2. Распаковать
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            with zipfile.ZipFile(tmp_zip, 'r') as z:
                z.extractall(tmp_dir)
            _set_progress(70, "Устанавливаем файлы...")

            # 3. Найти папку внутри архива (обычно repo-main/)
            extracted = os.listdir(tmp_dir)
            src_root = os.path.join(tmp_dir, extracted[0]) if extracted else tmp_dir

            # 4. Заменить modules/ и main.py
            for item in ["modules", "main.py"]:
                src = os.path.join(src_root, item)
                dst = os.path.join(app_dir, item)
                if not os.path.exists(src):
                    continue
                if os.path.isdir(src):
                    if os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

            # 5. Почистить
            os.remove(tmp_zip)
            shutil.rmtree(tmp_dir)
            _set_progress(100, "Готово!")

            dlg.after(600, lambda: _finish(True))

        except Exception as ex:
            dlg.after(0, lambda: _finish(False, str(ex)))

    def _finish(success, err=""):
        dlg.destroy()
        if success:
            if messagebox.askyesno("Обновление установлено",
                                   f"✅ Версия {version} установлена!\n\n"
                                   "Перезапустить приложение сейчас?",
                                   parent=parent_window):
                _restart()
        else:
            messagebox.showerror("Ошибка обновления",
                                 f"Не удалось установить обновление:\n{err}",
                                 parent=parent_window)
        if on_done: on_done(success)

    threading.Thread(target=_install, daemon=True).start()


def _restart():
    """Перезапускает приложение."""
    python = sys.executable
    os.execl(python, python, *sys.argv)


def show_update_dialog(parent_window, version, changelog):
    """Диалог 'Доступно обновление — установить?'"""
    msg = (f"🆕  Доступна новая версия  {version}\n\n"
           f"{changelog}\n\n"
           "Установить сейчас? (займёт ~10 секунд)")
    if messagebox.askyesno("Обновление ТрансЛогист", msg, parent=parent_window):
        download_and_install(parent_window, version)
