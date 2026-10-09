import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

PORTA = 8501
URL = f"http://127.0.0.1:{PORTA}"
PYTHON_MINIMO = (3, 10)


def pasta_launcher():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def arquivo_requisitos(raiz):
    for nome in ("requisitos.txt", "requirements.txt"):
        caminho = raiz / nome
        if caminho.is_file():
            return caminho
    return None


def localizar_raiz():
    inicial = pasta_launcher()
    atual = Path.cwd().resolve()
    candidatos = [inicial, *inicial.parents, atual, *atual.parents]
    verificados = []

    for candidato in candidatos:
        candidato = candidato.resolve()
        if candidato in verificados:
            continue
        verificados.append(candidato)
        if (
            (candidato / "ui" / "streamlit_app.py").is_file()
            and arquivo_requisitos(candidato) is not None
        ):
            return candidato

    lista = "\n".join(str(item) for item in verificados)
    raise FileNotFoundError(
        "Nao foi possivel localizar a raiz do Nexer.\n\n"
        "Arquivos obrigatorios:\n"
        "- ui\\streamlit_app.py\n"
        "- requisitos.txt ou requirements.txt\n\n"
        f"Pastas verificadas:\n{lista}"
    )


RAIZ = localizar_raiz()
REQUISITOS = arquivo_requisitos(RAIZ)
VENV = RAIZ / "venv"
PYTHON_VENV = VENV / "Scripts" / "python.exe"
APP = RAIZ / "ui" / "streamlit_app.py"
LOGS = RAIZ / "logs"
STATUS = RAIZ / "status"
LOG = LOGS / "streamlit.log"
PID = STATUS / "streamlit.pid"
PEDIDO_ENCERRAMENTO = STATUS / "encerrar_streamlit.json"
HASH_REQUISITOS = VENV / ".nexer_dependencies.sha256"
ICONE = RAIZ / "assets" / "logo.ico"

LOGS.mkdir(parents=True, exist_ok=True)
STATUS.mkdir(parents=True, exist_ok=True)


def log(mensagem):
    momento = time.strftime("%d/%m/%Y %H:%M:%S")
    try:
        with LOG.open("a", encoding="utf-8") as arquivo:
            arquivo.write(f"[{momento}] [LAUNCHER] {mensagem}\n")
    except OSError:
        pass


def flags_ocultas():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def executar(comando, descricao, ambiente=None):
    log(f"Iniciando: {descricao}")
    try:
        resultado = subprocess.run(
            [str(item) for item in comando],
            cwd=str(RAIZ),
            env=ambiente,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags_ocultas(),
        )
    except FileNotFoundError as erro:
        raise RuntimeError(
            f"Nao foi possivel {descricao}. Comando nao encontrado: {comando[0]}"
        ) from erro
    except subprocess.CalledProcessError as erro:
        detalhes = erro.stderr or erro.stdout or "Sem detalhes."
        log(f"Falha em {descricao}: {detalhes}")
        raise RuntimeError(
            f"Nao foi possivel {descricao}.\n\n{detalhes.strip()}\n\n"
            f"Consulte: {LOG}"
        ) from erro

    if resultado.stdout.strip():
        log(resultado.stdout.strip())
    log(f"Concluido: {descricao}")
    return resultado


def python_valido(comando):
    codigo = (
        "import sys; "
        f"raise SystemExit(0 if sys.version_info >= {PYTHON_MINIMO!r} else 1)"
    )
    try:
        resultado = subprocess.run(
            [*comando, "-c", codigo],
            cwd=str(RAIZ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags_ocultas(),
        )
        return resultado.returncode == 0
    except OSError:
        return False


def candidatos_python():
    candidatos = []
    if not getattr(sys, "frozen", False):
        candidatos.append([sys.executable])

    py = shutil.which("py")
    if py:
        candidatos.extend([[py, "-3.12"], [py, "-3"]])

    for nome in ("python", "python3"):
        caminho = shutil.which(nome)
        if caminho:
            candidatos.append([caminho])

    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python"
    for versao in ("Python312", "Python311", "Python310"):
        executavel = local / versao / "python.exe"
        if executavel.is_file():
            candidatos.append([str(executavel)])

    return candidatos


def localizar_python():
    vistos = set()
    for comando in candidatos_python():
        chave = tuple(comando)
        if chave not in vistos and python_valido(comando):
            return comando
        vistos.add(chave)
    return None


def instalar_python():
    winget = shutil.which("winget")
    if not winget:
        raise RuntimeError(
            "Python 3.10 ou superior nao foi encontrado e o winget nao esta "
            "disponivel. Instale o Python em https://www.python.org/downloads/ "
            "marcando 'Add Python to PATH'."
        )

    definir_status("Instalando Python 3.12...")
    executar(
        [
            winget, "install", "--id", "Python.Python.3.12", "--exact",
            "--source", "winget", "--scope", "user", "--silent",
            "--accept-package-agreements", "--accept-source-agreements",
        ],
        "instalar o Python 3.12",
    )


def obter_python():
    comando = localizar_python()
    if comando:
        return comando

    instalar_python()

    # O caminho instalado pelo winget pode ainda nao estar no PATH do processo.
    comando = localizar_python()
    if comando:
        return comando

    raise RuntimeError(
        "O Python foi instalado, mas nao foi localizado. Feche o Nexer e "
        "abra novamente."
    )


def venv_valida():
    if not PYTHON_VENV.is_file():
        return False
    try:
        return subprocess.run(
            [str(PYTHON_VENV), "-c", "import sys"],
            cwd=str(RAIZ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags_ocultas(),
        ).returncode == 0
    except OSError:
        return False


def criar_venv():
    if VENV.exists() and not venv_valida():
        definir_status("Recriando ambiente virtual...")
        shutil.rmtree(VENV)

    if venv_valida():
        return

    definir_status("Criando ambiente virtual...")
    executar([*obter_python(), "-m", "venv", str(VENV)], "criar a venv")

    if not venv_valida():
        raise RuntimeError(f"A venv foi criada, mas esta invalida: {VENV}")


def hash_requisitos():
    return hashlib.sha256(REQUISITOS.read_bytes()).hexdigest()


def dependencias_atualizadas():
    if not HASH_REQUISITOS.is_file():
        return False
    try:
        return HASH_REQUISITOS.read_text(encoding="utf-8").strip() == hash_requisitos()
    except OSError:
        return False


def pip_check():
    try:
        return subprocess.run(
            [str(PYTHON_VENV), "-m", "pip", "check"],
            cwd=str(RAIZ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags_ocultas(),
        ).returncode == 0
    except OSError:
        return False


def instalar_dependencias():
    if dependencias_atualizadas() and pip_check():
        log("Dependencias ja instaladas e atualizadas.")
        return

    definir_status("Atualizando ferramentas do Python...")
    executar(
        [str(PYTHON_VENV), "-m", "pip", "install", "--upgrade",
         "pip", "setuptools", "wheel"],
        "atualizar pip, setuptools e wheel",
    )

    definir_status("Instalando dependencias do Nexer...")
    executar(
        [str(PYTHON_VENV), "-m", "pip", "install",
         "--disable-pip-version-check", "--no-cache-dir",
         "-r", str(REQUISITOS)],
        "instalar as dependencias",
    )
    executar([str(PYTHON_VENV), "-m", "pip", "check"], "validar dependencias")
    HASH_REQUISITOS.write_text(hash_requisitos(), encoding="utf-8")



def obter_diagnostico_streamlit():
    """Retorna versão, pasta e index.html da instalação do Streamlit."""
    codigo = (
        "from importlib.metadata import version; "
        "from pathlib import Path; "
        "import streamlit; "
        "pasta=Path(streamlit.__file__).resolve().parent; "
        "index=pasta/'static'/'index.html'; "
        "print(version('streamlit')); "
        "print(pasta); "
        "print(index); "
        "raise SystemExit(0 if index.is_file() else 2)"
    )

    try:
        resultado = subprocess.run(
            [str(PYTHON_VENV), "-c", codigo],
            cwd=str(RAIZ),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=flags_ocultas(),
        )
    except OSError as erro:
        return {
            "valido": False,
            "versao": None,
            "pasta": None,
            "index": None,
            "erro": str(erro),
        }

    linhas = [
        linha.strip()
        for linha in resultado.stdout.splitlines()
        if linha.strip()
    ]

    return {
        "valido": resultado.returncode == 0,
        "versao": linhas[0] if len(linhas) >= 1 else None,
        "pasta": Path(linhas[1]) if len(linhas) >= 2 else None,
        "index": Path(linhas[2]) if len(linhas) >= 3 else None,
        "erro": resultado.stderr.strip(),
    }


def remover_streamlit_incompleto(diagnostico):
    """Remove resíduos do pacote antes da reinstalação corretiva."""
    pasta = diagnostico.get("pasta")

    if pasta is not None and pasta.is_dir():
        try:
            shutil.rmtree(pasta)
            log(f"Pasta incompleta do Streamlit removida: {pasta}")
        except OSError as erro:
            log(f"Não foi possível remover a pasta incompleta: {erro}")

    site_packages = VENV / "Lib" / "site-packages"
    if site_packages.is_dir():
        for caminho in site_packages.glob("streamlit-*.dist-info"):
            try:
                shutil.rmtree(caminho)
                log(f"Metadados antigos do Streamlit removidos: {caminho}")
            except OSError as erro:
                log(f"Não foi possível remover {caminho}: {erro}")


def reparar_streamlit():
    """Reinstala o mesmo Streamlit sem cache quando os estáticos faltam."""
    diagnostico = obter_diagnostico_streamlit()
    versao = diagnostico.get("versao")

    definir_status("Reparando instalação do Streamlit...")
    log(
        "Instalação incompleta do Streamlit detectada. "
        f"Versão={versao!r}; index={diagnostico.get('index')!s}"
    )

    remover_streamlit_incompleto(diagnostico)

    pacote = f"streamlit=={versao}" if versao else "streamlit"

    executar(
        [
            str(PYTHON_VENV),
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            "--no-cache-dir",
            "--no-deps",
            "--disable-pip-version-check",
            pacote,
        ],
        "reparar a instalação do Streamlit",
    )


def validar_e_reparar_streamlit():
    """Confirma static/index.html e efetua um único reparo automático."""
    diagnostico = obter_diagnostico_streamlit()

    if diagnostico["valido"]:
        log(
            "Streamlit validado: "
            f"{diagnostico['versao']} | {diagnostico['index']}"
        )
        return

    reparar_streamlit()
    diagnostico = obter_diagnostico_streamlit()

    if not diagnostico["valido"]:
        raise RuntimeError(
            "O Streamlit foi reinstalado automaticamente, mas o arquivo "
            "streamlit\\static\\index.html continua ausente.\n\n"
            "A instalação pode estar sendo alterada pelo antivírus, proxy "
            "ou repositório corporativo.\n\n"
            f"Detalhes: {diagnostico.get('erro') or 'não informados'}\n"
            f"Consulte: {LOG}"
        )

    log(
        "Streamlit reparado com sucesso: "
        f"{diagnostico['versao']} | {diagnostico['index']}"
    )


def localizar_edge():
    candidatos = []
    for variavel in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(variavel)
        if base:
            candidatos.append(
                Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            )
    caminho = shutil.which("msedge")
    if caminho:
        candidatos.append(Path(caminho))
    return next((item for item in candidatos if item.is_file()), None)


def validar_playwright_e_edge():
    resultado = subprocess.run(
        [str(PYTHON_VENV), "-c", "import playwright"],
        cwd=str(RAIZ),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags_ocultas(),
    )
    if resultado.returncode != 0:
        raise RuntimeError("Playwright nao foi instalado. Adicione playwright aos requisitos.")

    edge = localizar_edge()
    if edge is None:
        raise RuntimeError(
            "Microsoft Edge nao foi encontrado. Instale o Edge e execute novamente. "
            "O Nexer usa o Edge local para evitar downloads bloqueados pela rede."
        )
    log(f"Microsoft Edge localizado: {edge}")


def preparar_ambiente():
    criar_venv()
    instalar_dependencias()
    validar_e_reparar_streamlit()
    validar_playwright_e_edge()


def porta_ativa():
    try:
        with socket.create_connection(("127.0.0.1", PORTA), timeout=1):
            return True
    except OSError:
        return False


def salvar_pid(pid):
    temporario = PID.with_suffix(".tmp")
    temporario.write_text(str(pid), encoding="utf-8")
    os.replace(temporario, PID)


def limpar_controle():
    for caminho in (PID, PEDIDO_ENCERRAMENTO):
        try:
            caminho.unlink(missing_ok=True)
        except OSError:
            pass


def iniciar_streamlit():
    if porta_ativa():
        log("Streamlit ja estava ativo.")
        return None

    ambiente = os.environ.copy()
    ambiente.update({
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
        "NEXER_BROWSER_CHANNEL": "msedge",
    })

    comando = [
        str(PYTHON_VENV), "-m", "streamlit", "run", str(APP),
        "--server.address", "127.0.0.1",
        "--server.port", str(PORTA),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]

    arquivo_log = LOG.open("a", encoding="utf-8", buffering=1)
    configuracao = {
        "cwd": str(RAIZ),
        "env": ambiente,
        "stdin": subprocess.DEVNULL,
        "stdout": arquivo_log,
        "stderr": arquivo_log,
        "close_fds": True,
    }
    if os.name == "nt":
        configuracao["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        processo = subprocess.Popen(comando, **configuracao)
    finally:
        arquivo_log.close()

    salvar_pid(processo.pid)
    log(f"Streamlit iniciado com PID {processo.pid}.")
    return processo


def encerramento_solicitado():
    try:
        return bool(json.loads(PEDIDO_ENCERRAMENTO.read_text(encoding="utf-8")).get("encerrar"))
    except (OSError, json.JSONDecodeError):
        return False


def encerrar(processo):
    if processo is not None and processo.poll() is None:
        try:
            processo.terminate()
            processo.wait(timeout=10)
        except Exception:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(processo.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
    limpar_controle()


def definir_status(texto, cor="#38BDF8"):
    def aplicar():
        try:
            if janela.winfo_exists():
                status_label.config(text=texto, fg=cor)
        except tk.TclError:
            pass
    janela.after(0, aplicar)


def finalizar_interface():
    def fechar():
        try:
            janela.quit()
            janela.destroy()
        except tk.TclError:
            pass
    janela.after(0, fechar)


def aguardar_dashboard(processo):
    inicio = time.monotonic()
    while True:
        if porta_ativa():
            definir_status("Dashboard iniciado com sucesso.", "#22C55E")
            janela.after(0, progress.stop)
            webbrowser.open_new(URL)
            time.sleep(0.5)
            janela.after(0, janela.withdraw)
            return
        if processo is not None and processo.poll() is not None:
            raise RuntimeError(f"O Streamlit encerrou antes de iniciar. Consulte {LOG}")
        if time.monotonic() - inicio > 180:
            raise RuntimeError(f"O Streamlit nao abriu a porta {PORTA}. Consulte {LOG}")
        time.sleep(0.5)


def monitorar(processo):
    while True:
        if encerramento_solicitado():
            encerrar(processo)
            finalizar_interface()
            return
        if processo is not None and processo.poll() is not None:
            limpar_controle()
            finalizar_interface()
            return
        time.sleep(1)


def exibir_erro(erro):
    def mostrar():
        progress.stop()
        status_label.config(text="Falha ao iniciar o Nexer.", fg="#EF4444")
        messagebox.showerror("Nexer", str(erro))
    janela.after(0, mostrar)


def fluxo_inicial():
    global processo_streamlit
    try:
        definir_status("Preparando ambiente...")
        preparar_ambiente()
        definir_status("Iniciando dashboard...")
        processo_streamlit = iniciar_streamlit()
        aguardar_dashboard(processo_streamlit)
        threading.Thread(target=monitorar, args=(processo_streamlit,), daemon=True).start()
    except Exception as erro:
        log(f"Falha: {type(erro).__name__}: {erro}")
        exibir_erro(erro)


def fechar_splash():
    if messagebox.askyesno("Nexer", "Deseja cancelar a inicializacao?"):
        encerrar(processo_streamlit)
        finalizar_interface()


janela = tk.Tk()
janela.title("Nexer")
janela.geometry("520x260")
janela.resizable(False, False)
janela.configure(bg="#0F172A")
janela.protocol("WM_DELETE_WINDOW", fechar_splash)

if ICONE.is_file():
    try:
        janela.iconbitmap(str(ICONE))
    except Exception:
        pass

tk.Label(
    janela, text="Nexer", font=("Segoe UI", 26, "bold"),
    bg="#0F172A", fg="white",
).pack(pady=(30, 8))

tk.Label(
    janela, text="Automacao SGIND + IQOS", font=("Segoe UI", 12),
    bg="#0F172A", fg="#CBD5E1",
).pack()

status_label = tk.Label(
    janela, text="Preparando ambiente...", font=("Segoe UI", 10),
    bg="#0F172A", fg="#38BDF8", justify="center",
)
status_label.pack(pady=(20, 10))

progress = ttk.Progressbar(janela, mode="indeterminate", length=360)
progress.pack(pady=(10, 20))
progress.start(10)

processo_streamlit = None
janela.after(
    100,
    lambda: threading.Thread(target=fluxo_inicial, daemon=True).start(),
)
janela.mainloop()
