"""Nexer desktop launcher: native Nexer branding, no report workers."""
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser

EXECUTABLE_PATH = Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()
START_DIRECTORY = EXECUTABLE_PATH.parent if getattr(sys, "frozen", False) else EXECUTABLE_PATH.parents[1]
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", START_DIRECTORY))


def find_project_root(start: Path) -> Path:
    """Support a launcher in the root or an internal build subfolder."""
    for candidate in (start, *start.parents):
        if (candidate / "scripts" / "manage_nexer.ps1").is_file() and (candidate / "apps" / "frontend").is_dir():
            return candidate
    raise FileNotFoundError("Pasta do Nexer não encontrada. Mantenha o executável dentro da pasta do projeto.")


ROOT = find_project_root(START_DIRECTORY)
CONTROL = ROOT / "scripts" / "manage_nexer.ps1"
DASHBOARD = "http://127.0.0.1:5173/"

INK = "#171719"
MUTED = "#68717e"
BACKGROUND = "#f4f7fb"
WHITE = "#ffffff"
BORDER = "#dfe6ef"
GREEN = "#138451"
RED = "#b42332"


def control(action: str) -> str:
    if action not in {"start", "stop", "restart", "status"}:
        raise ValueError("Invalid action")
    if not CONTROL.is_file():
        raise FileNotFoundError("Não foi encontrado scripts/manage_nexer.ps1. Mantenha o executável na raiz do Nexer.")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
         "-File", str(CONTROL), "-Action", action],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=75, creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Operação não concluída.").strip())
    return result.stdout.strip()


def main():
    window = tk.Tk()
    window.title("Nexer | Central de controle")
    window.geometry("490x450")
    window.minsize(490, 450)
    window.resizable(False, False)
    window.configure(bg=BACKGROUND)
    # Widgets define font tuples individually; a string such as "Segoe UI 10" is parsed incorrectly by Tcl.
    try:
        icon = RESOURCE_ROOT / "assets" / "nexer.ico"
        if icon.is_file():
            window.iconbitmap(str(icon))
    except tk.TclError:
        pass

    outer = tk.Frame(window, bg=BACKGROUND, padx=25, pady=18)
    outer.pack(fill="both", expand=True)

    brand = tk.Frame(outer, bg=BACKGROUND)
    brand.pack(fill="x", pady=(0, 12))
    try:
        logo = tk.PhotoImage(file=str(RESOURCE_ROOT / "assets" / "nexer-horizontal.png"))
        window.brand_image = logo
        tk.Label(brand, image=logo, bg=BACKGROUND).pack(anchor="w")
    except tk.TclError:
        tk.Label(brand, text="NEXER", bg=BACKGROUND, fg=INK,
                 font=("Segoe UI", 23, "bold")).pack(anchor="w")

    tk.Label(outer, text="Central de controle", bg=BACKGROUND, fg=INK,
             font=("Segoe UI", 17, "bold")).pack(anchor="w")
    tk.Label(outer, text="Gerencie o dashboard e a API local com segurança.",
             bg=BACKGROUND, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(3, 14))

    card = tk.Frame(outer, bg=WHITE, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=14)
    card.pack(fill="x")
    status = tk.StringVar(value="Verificando API local...")
    status_color = tk.Label(card, text="●", bg=WHITE, fg=MUTED, font=("Segoe UI", 14))
    status_color.pack(side="left")
    status_label = tk.Label(card, textvariable=status, bg=WHITE, fg=INK, font=("Segoe UI", 10, "bold"))
    status_label.pack(side="left", padx=(8, 0))
    buttons = []
    busy = False

    def set_status(message: str, color: str):
        status.set(message)
        status_color.configure(fg=color)

    def task(action: str, open_dashboard: bool = False):
        nonlocal busy
        if busy:
            return
        if action in ("stop", "restart") and not messagebox.askyesno(
            "Confirmar operação",
            "A API será encerrada. A sessão do Nexer será interrompida e gravações ativas podem ser perdidas. Continuar?",
            parent=window,
        ):
            return
        busy = True
        for button in buttons:
            button.configure(state="disabled")
        set_status("Executando operação...", MUTED)

        def worker():
            try:
                output = control(action)
                def success():
                    nonlocal busy
                    busy = False
                    set_status("API ativa" if "API_RUNNING" in output else "API finalizada",
                               GREEN if "API_RUNNING" in output else MUTED)
                    for button in buttons:
                        button.configure(state="normal")
                    if open_dashboard:
                        webbrowser.open(DASHBOARD)
                window.after(0, success)
            except Exception as exc:
                detail = str(exc)
                def failed():
                    nonlocal busy
                    busy = False
                    set_status("Não foi possível concluir a operação", RED)
                    for button in buttons:
                        button.configure(state="normal")
                    messagebox.showerror("Nexer", detail, parent=window)
                window.after(0, failed)
        threading.Thread(target=worker, daemon=True).start()

    def add_button(text: str, action: str, *, primary: bool = False, open_dashboard: bool = False):
        bg = INK if primary else WHITE
        fg = WHITE if primary else INK
        button = tk.Button(outer, text=text, bg=bg, fg=fg, activebackground="#303036" if primary else "#edf2f8",
                           activeforeground=WHITE if primary else INK, relief="flat", bd=0, cursor="hand2",
                           highlightthickness=1, highlightbackground=INK if primary else BORDER,
                           font=("Segoe UI", 11, "bold" if primary else "normal"),
                           pady=11, command=lambda: task(action, open_dashboard))
        button.pack(fill="x", pady=(12 if primary else 6, 0))
        buttons.append(button)

    add_button("Abrir dashboard  →", "start", primary=True, open_dashboard=True)
    add_button("↻   Reiniciar API", "restart")
    add_button("■   Finalizar API", "stop")

    tk.Label(outer, text="Ambiente local  •  Sem worker de relatórios",
             bg=BACKGROUND, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="center", pady=(17, 0))
    window.after(150, lambda: task("status"))
    window.mainloop()


if __name__ == "__main__":
    main()
