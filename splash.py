import os
import sys
import time
import socket
import webbrowser
import subprocess
import tkinter as tk
from threading import Thread


PORTA = 8501
URL = f"http://localhost:{PORTA}"


def servidor_disponivel():
    try:
        with socket.create_connection(
            ("127.0.0.1", PORTA),
            timeout=1
        ):
            return True
    except Exception:
        return False


def iniciar_streamlit():
    raiz = os.path.dirname(os.path.abspath(__file__))
    python_venv = os.path.join(raiz, "venv", "Scripts", "python.exe")
    app_streamlit = os.path.join(raiz, "ui", "streamlit_app.py")
    log_dir = os.path.join(raiz, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "streamlit.log")

    with open(log_file, "a", encoding="utf-8") as log:
        subprocess.Popen(
            [
                python_venv,
                "-m",
                "streamlit",
                "run",
                app_streamlit,
                "--server.headless",
                "true",
            ],
            stdout=log,
            stderr=log,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            ),
        )


def aguardar_servidor(janela):
    inicio = time.time()
    while True:
        if servidor_disponivel():
            webbrowser.open(URL)
            janela.destroy()
            return

        if time.time() - inicio > 120:
            janela.destroy()
            return

        time.sleep(1)


janela = tk.Tk()
janela.title("Nexer")
janela.geometry("500x220")
janela.resizable(False, False)

largura = 500
altura = 220
x = (janela.winfo_screenwidth() // 2) - (largura // 2)
y = (janela.winfo_screenheight() // 2) - (altura // 2)

janela.geometry(f"{largura}x{altura}+{x}+{y}")
janela.configure(bg="#0F172A")

titulo = tk.Label(
    janela,
    text="📊 Nexer",
    font=("Segoe UI", 24, "bold"),
    bg="#0F172A",
    fg="white",
)
titulo.pack(pady=(25, 10))

subtitulo = tk.Label(
    janela,
    text="Preparando ambiente...",
    font=("Segoe UI", 12),
    bg="#0F172A",
    fg="white",
)
subtitulo.pack()

barra = tk.Label(
    janela,
    text="⏳ Carregando dependências",
    font=("Segoe UI", 12),
    bg="#0F172A",
    fg="white",
)
barra.pack(pady=(15, 0))

Thread(
    target=aguardar_servidor,
    args=(janela,),
    daemon=True,
).start()

iniciar_streamlit()
janela.mainloop()
