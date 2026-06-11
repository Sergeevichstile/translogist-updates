import tkinter as tk
from tkinter import ttk

# ── Color palette ────────────────────────────────────────────────
BG       = "#1a1d2e"
BG2      = "#12152a"
CARD     = "#21253a"
BORDER   = "#2a2d45"
ACCENT   = "#2563eb"
SUCCESS  = "#16a34a"
DANGER   = "#dc2626"
WARN     = "#d97706"
TEXT     = "#f1f5f9"
MUTED    = "#9ca3af"
WHITE    = "#ffffff"


def card(parent, **kw):
    kw.setdefault("bg", CARD)
    kw.setdefault("relief", "flat")
    kw.setdefault("padx", 16)
    kw.setdefault("pady", 12)
    return tk.Frame(parent, **kw)


def label(parent, text, size=11, bold=False, color=TEXT, **kw):
    weight = "bold" if bold else "normal"
    return tk.Label(parent, text=text, bg=kw.pop("bg", parent["bg"]),
                    fg=color, font=("Arial", size, weight), **kw)


def entry(parent, width=24, **kw):
    e = tk.Entry(parent, width=width,
                 bg="#2a2d45", fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Segoe UI", 11),
                 highlightthickness=1, highlightcolor=ACCENT,
                 highlightbackground=BORDER, **kw)
    return e


def _bind_clipboard(root):
    """Bind Ctrl+V/C/X/A to all Entry and Text widgets recursively."""
    def _paste(e):
        w = e.widget
        try:
            txt = w.clipboard_get()
            if isinstance(w, tk.Text):
                w.insert(tk.INSERT, txt)
            else:
                try: w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except: pass
                w.insert(tk.INSERT, txt)
        except Exception:
            pass
        return "break"

    def _copy(e):
        w = e.widget
        try:
            if isinstance(w, tk.Text):
                txt = w.get(tk.SEL_FIRST, tk.SEL_LAST)
            else:
                txt = w.selection_get()
            w.clipboard_clear()
            w.clipboard_append(txt)
        except Exception:
            pass
        return "break"

    def _cut(e):
        w = e.widget
        try:
            if isinstance(w, tk.Text):
                txt = w.get(tk.SEL_FIRST, tk.SEL_LAST)
                w.delete(tk.SEL_FIRST, tk.SEL_LAST)
            else:
                txt = w.selection_get()
                w.delete(tk.SEL_FIRST, tk.SEL_LAST)
            w.clipboard_clear()
            w.clipboard_append(txt)
        except Exception:
            pass
        return "break"

    def _select_all(e):
        w = e.widget
        try:
            if isinstance(w, tk.Text):
                w.tag_add(tk.SEL, "1.0", tk.END)
            else:
                w.select_range(0, tk.END)
                w.icursor(tk.END)
        except Exception:
            pass
        return "break"

    for seq, fn in [
        ("<Control-v>", _paste), ("<Control-V>", _paste),
        ("<Control-c>", _copy),  ("<Control-C>", _copy),
        ("<Control-x>", _cut),   ("<Control-X>", _cut),
        ("<Control-a>", _select_all), ("<Control-A>", _select_all),
    ]:
        root.bind_class("Entry", seq, fn)
        root.bind_class("Text",  seq, fn)


def combo(parent, values, width=22, **kw):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TCombobox",
                    fieldbackground="#2a2d45", background="#2a2d45",
                    foreground=TEXT, arrowcolor=TEXT,
                    selectbackground="#2a2d45", selectforeground=TEXT)
    c = ttk.Combobox(parent, values=values, width=width,
                     style="Dark.TCombobox", state="readonly", **kw)
    return c


def btn(parent, text, command=None, color=ACCENT, fg=WHITE, **kw):
    b = tk.Button(parent, text=text, command=command,
                  bg=color, fg=fg, activebackground=color,
                  activeforeground=fg, relief="flat",
                  font=("Arial", 10, "bold"),
                  padx=14, pady=6, cursor="hand2", **kw)
    return b


def section_title(parent, text):
    f = tk.Frame(parent, bg=parent["bg"])
    tk.Label(f, text=text, bg=parent["bg"], fg=TEXT,
             font=("Arial", 13, "bold")).pack(side="left")
    tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x",
                                           expand=True, padx=(12, 0), pady=6)
    return f


_table_style_initialized = False

def make_table(parent, columns, col_widths=None):
    global _table_style_initialized
    if not _table_style_initialized:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview",
                        background=CARD, foreground=TEXT,
                        fieldbackground=CARD, rowheight=32,
                        font=("Segoe UI", 10))
        style.configure("Dark.Treeview.Heading",
                        background=BG2, foreground=MUTED,
                        font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Dark.Treeview", background=[("selected", ACCENT)])
        _table_style_initialized = True

    frame = tk.Frame(parent, bg=BG)
    tree = ttk.Treeview(frame, columns=columns, show="headings",
                        style="Dark.Treeview")
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    for i, col in enumerate(columns):
        tree.heading(col, text=col)
        w = col_widths[i] if col_widths and i < len(col_widths) else 120
        tree.column(col, width=w, anchor="center")

    return frame, tree


def metric_card(parent, title, value, color=TEXT):
    f = tk.Frame(parent, bg=CARD, padx=20, pady=14,
                 highlightthickness=1, highlightbackground=BORDER)
    tk.Label(f, text=title, bg=CARD, fg=MUTED,
             font=("Arial", 10)).pack(anchor="w")
    tk.Label(f, text=value, bg=CARD, fg=color,
             font=("Arial", 18, "bold")).pack(anchor="w", pady=(4, 0))
    return f
