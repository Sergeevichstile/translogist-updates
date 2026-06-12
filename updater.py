import tkinter as tk
from tkinter import messagebox
import threading
import json
import os
import sys
import zipfile
import shutil
import subprocess

# URL репозитория
GITHUB_USER = "Sergeevichstile"
GITHUB_REPO = "translogist-updates"
RAW_BASE    = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main"
VERSION_URL = f"{RAW_BASE}/version.json"
ZIP_URL     = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/archive/refs/heads/main.zip"

DEFAULT_VERSION = "4.0.0"   # версия "из коробки", если локального файла версии нет


def get_app_dir():
    """Папка где лежит приложение (.exe или main.py)."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _local_version_file():
    # Версия хранится в постоянной папке с данными, а не рядом с .exe,
    # чтобы переживать пересборку/замену exe.
    data_dir = os.path.join(os.path.expanduser("~"), "TransLogistData")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "installed_version.json")


def get_current_version():
    path = _local_version_file()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("version", DEFAULT_VERSION)
    except Exception:
        return DEFAULT_VERSION


def _save_current_version(version):
    path = _local_version_file()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"version": version}, f, ensure_ascii=False)
    except Exception:
        pass


def check_for_updates(on_update_available=None, silent=True):
    def _check():
        try:
            import urllib.request
            with urllib.request.urlopen(VERSION_URL, timeout=5) as r:
                data = json.loads(r.read().decode())
            latest  = data.get("version", "0.0.0")
            changes = data.get("changelog", "Исправления и улучшения")
            current = get_current_version()
            if _newer(latest, current):
                if on_update_available:
                    on_update_available(latest, changes)
        except Exception:
            pass

    t = threading.Thread(target=_check, daemon=True)
    t.start()


def _newer(v1, v2):
    try:
        return tuple(int(x) for x in v1.split(".")) > \
               tuple(int(x) for x in v2.split("."))
    except Exception:
        return False


def _find_python():
    """Находит интерпретатор Python для пересборки exe."""
    # Сначала пробуем py launcher
    for cmd in (["py", "-3"], ["python"], ["python3"]):
        try:
            r = subprocess.run(cmd + ["--version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return cmd
        except Exception:
            continue
    return None


def download_and_install(parent_window, version, on_done=None):
    """Скачивает новый код, обновляет файлы, и если запущено как .exe — пересобирает себя."""

    is_frozen = getattr(sys, 'frozen', False)

    dlg = tk.Toplevel(parent_window)
    dlg.title("Обновление")
    dlg.geometry("440x180")
    dlg.resizable(False, False)
    dlg.grab_set()
    try:
        dlg.configure(bg="#1a1d2e")
    except Exception:
        pass

    lbl = tk.Label(dlg, text=f"⬇️  Скачиваем версию {version}...",
                   font=("Segoe UI", 11), bg="#1a1d2e", fg="white")
    lbl.pack(pady=(24, 8))

    bar_frame = tk.Frame(dlg, bg="#2a2d45", width=380, height=18)
    bar_frame.pack(pady=4)
    bar_frame.pack_propagate(False)
    bar = tk.Frame(bar_frame, bg="#6366f1", width=0, height=18)
    bar.place(x=0, y=0, relheight=1)

    status = tk.Label(dlg, text="Подготовка...", font=("Segoe UI", 9),
                      bg="#1a1d2e", fg="#94a3b8")
    status.pack()

    def _set_progress(pct, text=""):
        bar.place(x=0, y=0, relheight=1, width=int(380 * pct / 100))
        if text: status.config(text=text)
        dlg.update_idletasks()

    def _install():
        try:
            import urllib.request
            import tempfile

            app_dir = get_app_dir()
            tmp_zip = os.path.join(tempfile.gettempdir(), "translogist_update.zip")
            tmp_dir = os.path.join(tempfile.gettempdir(), "translogist_update")

            # 1. Скачать zip с исходниками
            _set_progress(10, "Скачиваем исходный код...")
            urllib.request.urlretrieve(ZIP_URL, tmp_zip)
            _set_progress(30, "Распаковываем...")

            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            with zipfile.ZipFile(tmp_zip, 'r') as z:
                z.extractall(tmp_dir)

            extracted = os.listdir(tmp_dir)
            src_root = os.path.join(tmp_dir, extracted[0]) if extracted else tmp_dir

            if not is_frozen:
                # ── Режим python main.py: просто заменяем файлы ──────────
                _set_progress(60, "Обновляем файлы...")
                for item in ["modules", "main.py", "updater.py"]:
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

                _save_current_version(version)
                os.remove(tmp_zip)
                shutil.rmtree(tmp_dir)
                _set_progress(100, "Готово!")
                dlg.after(600, lambda: _finish(True, restart_mode="python"))

            else:
                # ── Режим .exe: пересобираем через PyInstaller ───────────
                _set_progress(40, "Готовим сборку...")
                py = _find_python()
                if not py:
                    raise RuntimeError(
                        "Python не найден. Установите Python и PyInstaller "
                        "(pip install pyinstaller) для автообновления .exe")

                build_dir = os.path.join(tempfile.gettempdir(), "translogist_build")
                if os.path.exists(build_dir):
                    shutil.rmtree(build_dir)
                os.makedirs(build_dir)

                # Копируем исходники для сборки
                for item in ["modules", "main.py", "updater.py", "splash.py",
                              "icon.ico", "icon.png"]:
                    src = os.path.join(src_root, item)
                    if not os.path.exists(src):
                        continue
                    dst = os.path.join(build_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)

                _set_progress(50, "Собираем новый .exe (1-2 минуты)...")
                cmd = py + [
                    "-m", "PyInstaller", "--onefile", "--windowed",
                    "--icon=icon.ico", "--name=TransLogist_new",
                    "--add-data=icon.ico;.",
                    "--hidden-import=tkinter",
                    "--hidden-import=docx",
                    "--hidden-import=lxml",
                    "--distpath", os.path.join(build_dir, "dist"),
                    "--workpath", os.path.join(build_dir, "build"),
                    "--specpath", build_dir,
                    "--clean",
                    os.path.join(build_dir, "main.py"),
                ]
                result = subprocess.run(cmd, cwd=build_dir,
                                         capture_output=True, text=True, timeout=600)

                new_exe = os.path.join(build_dir, "dist", "TransLogist_new.exe")
                if result.returncode != 0 or not os.path.exists(new_exe):
                    raise RuntimeError("Ошибка сборки:\n" + result.stderr[-800:])

                _set_progress(90, "Готовим установку...")

                current_exe = sys.executable
                exe_dir  = os.path.dirname(current_exe)
                exe_name = os.path.basename(current_exe)
                staged_exe = os.path.join(exe_dir, "_TransLogist_update.exe")
                shutil.copy2(new_exe, staged_exe)

                # bat-скрипт: ждём закрытия текущего exe, заменяем, запускаем новый
                bat_path = os.path.join(tempfile.gettempdir(), "translogist_apply_update.bat")
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write("@echo off\r\n")
                    f.write("timeout /t 2 /nobreak >nul\r\n")
                    f.write(f'del /F /Q "{os.path.join(exe_dir, exe_name)}"\r\n')
                    f.write(f'move /Y "{staged_exe}" "{os.path.join(exe_dir, exe_name)}"\r\n')
                    f.write(f'start "" "{os.path.join(exe_dir, exe_name)}"\r\n')
                    f.write(f'del "%~f0"\r\n')

                _save_current_version(version)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                os.remove(tmp_zip)
                shutil.rmtree(build_dir, ignore_errors=True)

                _set_progress(100, "Готово! Перезапуск...")
                dlg.after(400, lambda: _finish(True, restart_mode="exe", bat_path=bat_path))

        except Exception as ex:
            dlg.after(0, lambda: _finish(False, str(ex)))

    def _finish(success, err="", restart_mode=None, bat_path=None):
        dlg.destroy()
        if success:
            messagebox.showinfo("Обновление установлено",
                                f"✅ Версия {version} установлена!\n"
                                "Приложение сейчас перезапустится.",
                                parent=parent_window)
            if restart_mode == "python":
                _restart_python()
            elif restart_mode == "exe":
                subprocess.Popen(["cmd", "/c", bat_path],
                                  creationflags=subprocess.CREATE_NO_WINDOW)
                os._exit(0)
        else:
            messagebox.showerror("Ошибка обновления",
                                 f"Не удалось установить обновление:\n{err}",
                                 parent=parent_window)
        if on_done: on_done(success)

    threading.Thread(target=_install, daemon=True).start()


def _restart_python():
    python = sys.executable
    os.execl(python, python, *sys.argv)


def show_update_dialog(parent_window, version, changelog):
    msg = (f"🆕  Доступна новая версия  {version}\n\n"
           f"{changelog}\n\n"
           "Установить сейчас?")
    if messagebox.askyesno("Обновление ТрансЛогист", msg, parent=parent_window):
        download_and_install(parent_window, version)
