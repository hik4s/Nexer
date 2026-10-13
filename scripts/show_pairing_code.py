"""Native local pairing window; code arrives only through inherited stdin."""
import json
import re
import sys
import tkinter as tk
from tkinter import ttk


def main():
    try:
        payload = json.loads(sys.stdin.readline(1024))
        code = payload.pop("code")
        if payload or not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", code):
            raise ValueError()
        root = tk.Tk()
        root.title("Pareamento local — Nexer")
        root.resizable(False, False)
        panel = ttk.Frame(root, padding=24)
        panel.pack()
        ttk.Label(panel, text="Código de pareamento do Nexer", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(panel, text="Cole este código na tela Entrar no Nexer.\nVálido por até cinco minutos, para um único uso.\nGerar outro código invalida este.").pack(anchor="w", pady=(10, 14))
        value = tk.StringVar(value=code)
        code = None
        entry = ttk.Entry(panel, textvariable=value, state="readonly", width=58)
        entry.pack(fill="x")
        status = tk.StringVar()
        def copy():
            root.clipboard_clear()
            root.clipboard_append(value.get())
            status.set("Código copiado. Cole na tela do Nexer.")
        ttk.Button(panel, text="Copiar código", command=copy).pack(anchor="w", pady=(14, 8))
        ttk.Label(panel, textvariable=status).pack(anchor="w")
        def close():
            value.set("")
            root.destroy()
        root.protocol("WM_DELETE_WINDOW", close)
        root.after(300000, close)
        root.update_idletasks()
        sys.stdout.write("READY\n")
        sys.stdout.flush()
        root.mainloop()
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
