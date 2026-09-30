import json
import os
import signal
import subprocess
import time
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from auth import (
    ler_credenciais_env,
    salvar_credenciais
)

from core.app_control import (
    solicitar_encerramento
)

from core.file_manager import (
    arquivo_existe_no_servidor
)


# =====================================================
# CAMINHOS DO PROJETO
# =====================================================

RAIZ = Path(
    __file__
).resolve().parent.parent

CAMINHO_ENV = (
    RAIZ
    / ".env"
)

PASTA_STATUS = (
    RAIZ
    / "status"
)

CAMINHO_STATUS = (
    PASTA_STATUS
    / "status.json"
)

CAMINHO_PID_WORKER = (
    PASTA_STATUS
    / "worker.pid"
)

PASTA_DOWNLOADS = (
    RAIZ
    / "downloads"
)

PASTA_LOGS = (
    RAIZ
    / "logs"
)

CAMINHO_LOG_WORKER = (
    PASTA_LOGS
    / "worker.log"
)

WORKER = (
    RAIZ
    / "worker.py"
)

PYTHON_WORKER = (
    RAIZ
    / "venv"
    / "Scripts"
    / "python.exe"
)


# =====================================================
# LOGS PRESERVADOS
# =====================================================

NOMES_LOGS_PRESERVADOS = {
    "streamlit.log"
}


# =====================================================
# CRIAÇÃO DAS PASTAS
# =====================================================

PASTA_STATUS.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_DOWNLOADS.mkdir(
    parents=True,
    exist_ok=True
)

PASTA_LOGS.mkdir(
    parents=True,
    exist_ok=True
)


# =====================================================
# CONFIGURAÇÃO DO STREAMLIT
# =====================================================

st.set_page_config(
    page_title="RelatPy",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st_autorefresh(
    interval=3000,
    key="relatpy_autorefresh"
)


# =====================================================
# ESTILO
# =====================================================

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    div[data-testid="metric-container"] {
        background-color: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 14px;
    }

    div[data-testid="stAlert"] {
        border-radius: 10px;
    }

    div.stButton > button {
        border-radius: 8px;
        min-height: 42px;
    }

    div.stDownloadButton > button {
        border-radius: 8px;
        min-height: 42px;
    }

    .relatpy-caption {
        color: #94a3b8;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =====================================================
# NOMES AMIGÁVEIS
# =====================================================

NOMES_RELATORIOS = {
    "compensacao": "Compensação",
    "reclamacao": "Reclamações",
    "interrupcoes_cliente": "Interrupções por Cliente",
    "interrupcoes_evento": "Eventos",
    "todas_ocorrencias": "Ocorrências",
    "inconsistentes": "Inconsistências",
    "tarefas": "Tarefas",
    "dia_critico": "Dia Crítico",
    "iqos_resultados": "IQOS",
}


ORDEM_RELATORIOS = [
    "compensacao",
    "reclamacao",
    "interrupcoes_cliente",
    "interrupcoes_evento",
    "todas_ocorrencias",
    "inconsistentes",
    "tarefas",
    "dia_critico",
    "iqos_resultados",
]

OPCOES_RELATORIOS = {
    modulo: NOMES_RELATORIOS.get(
        modulo,
        modulo
    )
    for modulo in ORDEM_RELATORIOS
}


# =====================================================
# MANIPULAÇÃO SEGURA DO STATUS.JSON
# =====================================================

def gravar_json_atomico(
    caminho,
    dados
):
    """
    Grava o JSON utilizando um arquivo temporário.

    Isso evita que o Streamlit leia o status durante
    uma escrita feita por outro processo.
    """

    caminho = Path(
        caminho
    )

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    caminho_temporario = caminho.with_suffix(
        caminho.suffix + ".tmp"
    )

    with open(
        caminho_temporario,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            dados,
            arquivo,
            ensure_ascii=False,
            indent=4
        )

        arquivo.flush()

        os.fsync(
            arquivo.fileno()
        )

    os.replace(
        caminho_temporario,
        caminho
    )


def garantir_status_json():
    """
    Cria o status.json vazio somente se ele ainda
    não existir.

    Não apaga os dados ao atualizar ou reabrir a aba.
    """

    if CAMINHO_STATUS.exists():

        return

    gravar_json_atomico(
        CAMINHO_STATUS,
        {}
    )


def limpar_status_json():
    """
    Zera o status somente antes de uma nova execução.
    """

    gravar_json_atomico(
        CAMINHO_STATUS,
        {}
    )


garantir_status_json()


# =====================================================
# LOGIN
# =====================================================

def env_possui_credenciais():

    try:

        usuario, senha = ler_credenciais_env()

        return bool(
            usuario
            and senha
        )

    except Exception:

        return False


def exibir_tela_login():

    st.title(
        "🔐 Primeiro acesso"
    )

    st.info(
        "O arquivo .env não existe ou está incompleto. "
        "Informe as credenciais de acesso ao SGIND e ao IQOS."
    )

    usuario_login = st.text_input(
        "Usuário",
        key="login_usuario",
        autocomplete="username",
        placeholder="Informe o usuário"
    )

    senha_login = st.text_input(
        "Senha",
        type="password",
        key="login_senha",
        autocomplete="current-password",
        placeholder="Informe a senha"
    )

    salvar_login = st.button(
        "💾 Salvar credenciais",
        use_container_width=True,
        type="primary"
    )

    if salvar_login:

        usuario_login = (
            usuario_login.strip()
        )

        if not usuario_login:

            st.error(
                "Informe o usuário."
            )

        elif not senha_login:

            st.error(
                "Informe a senha."
            )

        else:

            try:

                salvar_credenciais(
                    usuario_login,
                    senha_login
                )

                usuario_salvo, senha_salva = (
                    ler_credenciais_env()
                )

                if (
                    not usuario_salvo
                    or not senha_salva
                ):

                    raise RuntimeError(
                        "As credenciais foram salvas, "
                        "mas não puderam ser carregadas."
                    )

                st.success(
                    "Credenciais salvas com sucesso."
                )

                st.session_state.pop(
                    "login_usuario",
                    None
                )

                st.session_state.pop(
                    "login_senha",
                    None
                )

                st.rerun()

            except Exception as erro:

                st.error(
                    "Não foi possível salvar as credenciais: "
                    f"{type(erro).__name__}: {erro}"
                )

    st.caption(
        "As credenciais serão armazenadas no arquivo "
        ".env localizado na raiz do projeto."
    )


if not env_possui_credenciais():

    exibir_tela_login()

    st.stop()


# =====================================================
# LEITURA DO STATUS.JSON
# =====================================================

def carregar_status():
    """
    Carrega e normaliza os dados do status.json.
    """

    if not CAMINHO_STATUS.exists():

        return {}

    try:

        conteudo = CAMINHO_STATUS.read_text(
            encoding="utf-8"
        ).strip()

        if not conteudo:

            return {}

        dados = json.loads(
            conteudo
        )

        if not isinstance(
            dados,
            dict
        ):

            return {}

        status_validado = {}

        for modulo, informacoes in dados.items():

            if not isinstance(
                informacoes,
                dict
            ):

                continue

            status_validado[
                modulo
            ] = {
                "status": informacoes.get(
                    "status",
                    "PENDENTE"
                ),
                "detalhe": informacoes.get(
                    "detalhe"
                ),
                "arquivo_local": informacoes.get(
                    "arquivo_local"
                ),
                "arquivo_rede": informacoes.get(
                    "arquivo_rede"
                ),
                "ultima_atualizacao": informacoes.get(
                    "ultima_atualizacao"
                )
            }

        return status_validado

    except json.JSONDecodeError:

        return {}

    except UnicodeDecodeError as erro:

        st.error(
            "O status.json não está em UTF-8: "
            f"{erro}"
        )

        return {}

    except OSError as erro:

        st.error(
            "Não foi possível acessar o status.json: "
            f"{erro}"
        )

        return {}

    except Exception as erro:

        st.error(
            "Erro inesperado ao carregar status.json: "
            f"{type(erro).__name__}: {erro}"
        )

        return {}


# =====================================================
# CONTROLE DO WORKER
# =====================================================

def ler_pid_worker():

    if not CAMINHO_PID_WORKER.exists():

        return None

    try:

        conteudo = CAMINHO_PID_WORKER.read_text(
            encoding="utf-8"
        ).strip()

        if not conteudo:

            return None

        return int(
            conteudo
        )

    except (
        OSError,
        ValueError
    ):

        return None


def remover_pid_worker():

    try:

        CAMINHO_PID_WORKER.unlink(
            missing_ok=True
        )

    except OSError:

        pass


def worker_esta_ativo_windows(
    pid
):
    """
    Confirma se o PID pertence realmente ao worker.py.
    """

    comando_powershell = (
        "$processo = Get-CimInstance Win32_Process "
        f"-Filter \"ProcessId = {pid}\"; "
        "if ($null -eq $processo) { "
        "exit 1 "
        "} "
        "$linha = [string]$processo.CommandLine; "
        "if ($linha -match 'worker\\.py') { "
        "Write-Output 'WORKER'; "
        "exit 0 "
        "} "
        "exit 2"
    )

    try:

        resultado = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                comando_powershell
            ],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        return (
            resultado.returncode == 0
            and "WORKER" in resultado.stdout
        )

    except (
        subprocess.SubprocessError,
        OSError
    ):

        return False


def worker_esta_ativo(
    pid
):

    if not pid:

        return False

    if os.name == "nt":

        return worker_esta_ativo_windows(
            pid
        )

    try:

        os.kill(
            pid,
            0
        )

        return True

    except OSError:

        return False


def execucao_ativa():
    """
    Verifica o worker atual.

    Caso o PID seja obsoleto, remove o worker.pid
    automaticamente.
    """

    pid = ler_pid_worker()

    ativo = worker_esta_ativo(
        pid
    )

    if (
        not ativo
        and CAMINHO_PID_WORKER.exists()
    ):

        remover_pid_worker()

    return ativo


# =====================================================
# LIMPEZA DOS LOGS
# =====================================================

def limpar_logs_antigos():
    """
    Remove os logs antigos antes de iniciar uma nova
    execução.

    O streamlit.log é preservado porque pode estar
    aberto pelo launcher e pelo servidor Streamlit.
    """

    PASTA_LOGS.mkdir(
        parents=True,
        exist_ok=True
    )

    avisos = []

    nomes_preservados = {
        nome.lower()
        for nome in NOMES_LOGS_PRESERVADOS
    }

    try:

        caminhos = list(
            PASTA_LOGS.rglob("*")
        )

    except OSError as erro:

        return [
            f"Não foi possível listar os logs: {erro}"
        ]

    for caminho in caminhos:

        if not caminho.is_file():

            continue

        if caminho.name.lower() in nomes_preservados:

            continue

        try:

            caminho.unlink()

        except OSError as erro:

            avisos.append(
                "Não foi possível apagar o log "
                f"{caminho.name}: {erro}"
            )

    pastas = sorted(
        [
            caminho
            for caminho in PASTA_LOGS.rglob("*")
            if caminho.is_dir()
        ],
        key=lambda caminho: len(
            caminho.parts
        ),
        reverse=True
    )

    for pasta in pastas:

        try:

            pasta.rmdir()

        except OSError:

            pass

    return avisos


def preparar_log_worker(
    periodo_inicio,
    periodo_fim,
    modulos_selecionados
):
    """
    Cria um worker.log novo e registra imediatamente
    o cabeçalho da execução.
    """

    PASTA_LOGS.mkdir(
        parents=True,
        exist_ok=True
    )

    log = open(
        CAMINHO_LOG_WORKER,
        "w",
        encoding="utf-8",
        buffering=1
    )

    log.write(
        "Relatórios selecionados:\n"
    )

    for modulo in modulos_selecionados:

        nome = NOMES_RELATORIOS.get(
            modulo,
            modulo
        )

        log.write(
            f"- {nome}\n"
        )

    log.write(
        "=" * 70
        + "\n"
    )

    log.write(
        "RELATPY - NOVA EXECUÇÃO\n"
    )

    log.write(
        "Início do processo: "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
    )

    log.write(
        f"Período inicial: {periodo_inicio}\n"
    )

    log.write(
        f"Período final: {periodo_fim}\n"
    )

    log.write(
        "=" * 70
        + "\n\n"
    )

    log.flush()

    return log


# =====================================================
# INICIAR EXECUÇÃO
# =====================================================



# =====================================================
# LIMPEZA DOS DOWNLOADS
# =====================================================


def limpar_downloads_antigos():
    """Exclui o conteúdo de downloads e preserva a pasta principal."""
    PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)

    pasta_downloads = PASTA_DOWNLOADS.resolve()
    pasta_raiz = RAIZ.resolve()

    try:
        pasta_downloads.relative_to(pasta_raiz)
    except ValueError as erro:
        raise RuntimeError(
            "A pasta de downloads está fora da raiz do projeto. "
            "A limpeza foi bloqueada por segurança."
        ) from erro

    if pasta_downloads == pasta_raiz:
        raise RuntimeError(
            "A pasta de downloads não pode ser igual à raiz do projeto."
        )

    arquivos_excluidos = 0
    diretorios_excluidos = 0
    avisos = []

    try:
        caminhos = sorted(
            PASTA_DOWNLOADS.rglob("*"),
            key=lambda caminho: len(caminho.parts),
            reverse=True,
        )
    except OSError as erro:
        return {
            "arquivos_excluidos": 0,
            "diretorios_excluidos": 0,
            "avisos": [
                f"Não foi possível listar a pasta de downloads: {erro}"
            ],
        }

    for caminho in caminhos:
        try:
            if caminho.is_symlink() or caminho.is_file():
                caminho.unlink()
                arquivos_excluidos += 1
            elif caminho.is_dir():
                caminho.rmdir()
                diretorios_excluidos += 1
        except OSError as erro:
            avisos.append(
                f"Não foi possível apagar '{caminho}': {erro}"
            )

    return {
        "arquivos_excluidos": arquivos_excluidos,
        "diretorios_excluidos": diretorios_excluidos,
        "avisos": avisos,
    }


def iniciar_execucao(
    periodo_inicio,
    periodo_fim,
    modulos_selecionados
):
    if execucao_ativa():

        raise RuntimeError(
            "Já existe uma execução em andamento."
        )

    if not WORKER.is_file():

        raise FileNotFoundError(
            f"worker.py não encontrado: {WORKER}"
        )

    if not PYTHON_WORKER.is_file():

        raise FileNotFoundError(
            "Python do ambiente virtual não encontrado: "
            f"{PYTHON_WORKER}"
        )

    if not env_possui_credenciais():

        raise RuntimeError(
            "As credenciais não estão configuradas."
        )
    modulos_validos = set(
        ORDEM_RELATORIOS
    )

    modulos_selecionados = [
        modulo
        for modulo in modulos_selecionados
        if modulo in modulos_validos
    ]

    if not modulos_selecionados:

        raise ValueError(
            "Nenhum relatório válido foi selecionado."
        )


    resultado_downloads = limpar_downloads_antigos()
    avisos_downloads = resultado_downloads["avisos"]

    if avisos_downloads:
        detalhes = "\n".join(
            f"- {aviso}" for aviso in avisos_downloads
        )
        raise RuntimeError(
            "A nova execução foi cancelada porque alguns downloads "
            f"anteriores não puderam ser excluídos:\n{detalhes}"
        )

    avisos_logs = limpar_logs_antigos()

    limpar_status_json()

    ambiente = os.environ.copy()

    ambiente[
        "PYTHONUTF8"
    ] = "1"

    ambiente[
        "PYTHONIOENCODING"
    ] = "utf-8"

    ambiente[
        "PYTHONUNBUFFERED"
    ] = "1"

    modulos_json = json.dumps(
    modulos_selecionados,
    ensure_ascii=False
)

    comando = [
    str(PYTHON_WORKER),

    "-u",

    str(WORKER),
    periodo_inicio,
    periodo_fim,
    modulos_json ]

    log = preparar_log_worker(
    periodo_inicio,
    periodo_fim,
    modulos_selecionados
    )

    configuracao = {
        "cwd": str(RAIZ),
        "stdin": subprocess.DEVNULL,
        "stdout": log,
        "stderr": subprocess.STDOUT,
        "close_fds": True,
        "env": ambiente
    }

    if os.name == "nt":

        startupinfo = subprocess.STARTUPINFO()

        startupinfo.dwFlags |= (
            subprocess.STARTF_USESHOWWINDOW
        )

        startupinfo.wShowWindow = (
            subprocess.SW_HIDE
        )

        configuracao[
            "startupinfo"
        ] = startupinfo

        configuracao[
            "creationflags"
        ] = subprocess.CREATE_NO_WINDOW

    try:

        processo = subprocess.Popen(
            comando,
            **configuracao
        )

    except Exception as erro:

        try:

            log.write(
                "\n[ERRO] Não foi possível iniciar "
                f"o worker: {type(erro).__name__}: {erro}\n"
            )

            log.flush()

        finally:

            log.close()

        raise

    finally:

        # O subprocesso já recebeu o identificador do
        # arquivo. O dashboard pode fechar sua referência.
        try:

            log.close()

        except OSError:

            pass

    CAMINHO_PID_WORKER.write_text(
        str(processo.pid),
        encoding="utf-8"
    )

    return {
        "pid": processo.pid,
        "avisos_logs": avisos_logs,
        "arquivos_excluidos": resultado_downloads[
            "arquivos_excluidos"
        ],
        "diretorios_excluidos": resultado_downloads[
            "diretorios_excluidos"
        ]
    }


# =====================================================
# CANCELAMENTO DA EXECUÇÃO
# =====================================================

def marcar_execucao_como_cancelada():
    """
    Marca como CANCELADO apenas os relatórios que ainda
    estavam pendentes ou em execução.
    """

    status_atual = carregar_status()

    if not status_atual:

        return

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    for modulo, informacoes in status_atual.items():

        estado = informacoes.get(
            "status",
            "PENDENTE"
        )

        if estado not in {
            "PENDENTE",
            "EXECUTANDO"
        }:

            continue

        informacoes[
            "status"
        ] = "CANCELADO"

        informacoes[
            "detalhe"
        ] = (
            "Execução interrompida manualmente "
            "pelo usuário."
        )

        informacoes[
            "ultima_atualizacao"
        ] = agora

    gravar_json_atomico(
        CAMINHO_STATUS,
        status_atual
    )


def encerrar_worker_windows(
    pid
):
    """
    Encerra o worker e a árvore de processos-filhos,
    incluindo navegadores criados pelo Playwright.
    """

    try:

        resultado = subprocess.run(
            [
                "taskkill",
                "/PID",
                str(pid),
                "/T",
                "/F"
            ],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        return resultado

    except subprocess.TimeoutExpired as erro:

        raise RuntimeError(
            "O Windows não respondeu ao pedido "
            "de encerramento do worker."
        ) from erro

    except OSError as erro:

        raise RuntimeError(
            "Não foi possível executar o taskkill: "
            f"{erro}"
        ) from erro


def encerrar_worker_unix(
    pid
):

    try:

        os.kill(
            pid,
            signal.SIGTERM
        )

    except ProcessLookupError:

        return

    except OSError as erro:

        raise RuntimeError(
            "Não foi possível encerrar o worker: "
            f"{erro}"
        ) from erro


def parar_execucao_atual():
    """
    Interrompe somente o worker registrado atualmente.

    O worker.pid é removido apenas depois da confirmação
    de que o processo foi encerrado.
    """

    pid = ler_pid_worker()

    if not pid:

        remover_pid_worker()

        raise RuntimeError(
            "Nenhuma execução ativa foi encontrada."
        )

    if not worker_esta_ativo(
        pid
    ):

        remover_pid_worker()

        raise RuntimeError(
            "O processo registrado não está mais ativo. "
            "O PID obsoleto foi removido."
        )

    if os.name == "nt":

        resultado = encerrar_worker_windows(
            pid
        )

        if (
            resultado.returncode != 0
            and worker_esta_ativo(pid)
        ):

            mensagem = (
                resultado.stderr.strip()
                or resultado.stdout.strip()
                or "Erro não informado pelo Windows."
            )

            raise RuntimeError(
                "Falha ao encerrar a execução: "
                f"{mensagem}"
            )

    else:

        encerrar_worker_unix(
            pid
        )

    for _ in range(20):

        if not worker_esta_ativo(
            pid
        ):

            break

        time.sleep(
            0.25
        )

    if worker_esta_ativo(
        pid
    ):

        raise RuntimeError(
            "O processo ainda está ativo. "
            "O worker.pid foi preservado."
        )

    remover_pid_worker()

    marcar_execucao_como_cancelada()

    return True


# =====================================================
# VALIDAÇÃO DOS ARQUIVOS
# =====================================================

def obter_caminho_local_absoluto(
    caminho
):

    if not caminho:

        return None

    caminho_objeto = Path(
        caminho
    )

    if not caminho_objeto.is_absolute():

        caminho_objeto = (
            RAIZ
            / caminho_objeto
        )

    return caminho_objeto


def arquivo_local_existe(
    caminho
):

    caminho_objeto = obter_caminho_local_absoluto(
        caminho
    )

    if caminho_objeto is None:

        return False

    try:

        return caminho_objeto.is_file()

    except OSError:

        return False


def arquivo_rede_existe(
    modulo,
    periodo,
    caminho_registrado
):

    try:

        if arquivo_existe_no_servidor(
            modulo,
            periodo
        ):

            return True

    except Exception:

        pass

    if not caminho_registrado:

        return False

    try:

        return Path(
            caminho_registrado
        ).is_file()

    except OSError:

        return False


# =====================================================
# CABEÇALHO
# =====================================================

st.title(
    "📊 RelatPy"
)

st.subheader(
    "Automação SGIND + IQOS"
)

st.caption(
    "Atualizado em: "
    + datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )
)

st.divider()


# =====================================================
# FILTROS
# =====================================================

coluna_inicio, coluna_fim = st.columns(
    2
)

with coluna_inicio:

    data_inicio = st.date_input(
        "Data Inicial",
        value=date.today(),
        format="DD/MM/YYYY"
    )

with coluna_fim:

    data_fim = st.date_input(
        "Data Final",
        value=date.today(),
        format="DD/MM/YYYY"
    )

# =====================================================
# SELEÇÃO DOS RELATÓRIOS
# =====================================================

st.subheader(
    "Relatórios da execução"
)

selecionar_todos = st.checkbox(
    "Selecionar todos os relatórios",
    value=True,
    disabled=execucao_ativa(),
    key="selecionar_todos_relatorios"
)

nomes_disponiveis = [
    OPCOES_RELATORIOS[
        modulo
    ]
    for modulo in ORDEM_RELATORIOS
]

if selecionar_todos:

    nomes_selecionados = nomes_disponiveis

    st.multiselect(
        "Relatórios selecionados",
        options=nomes_disponiveis,
        default=nomes_disponiveis,
        disabled=True,
        key="relatorios_todos_visualizacao"
    )

else:

    nomes_selecionados = st.multiselect(
        "Escolha um ou mais relatórios",
        options=nomes_disponiveis,
        default=[],
        disabled=execucao_ativa(),
        placeholder="Selecione os relatórios",
        key="relatorios_individuais"
    )


modulos_selecionados = [
    modulo
    for modulo in ORDEM_RELATORIOS
    if OPCOES_RELATORIOS[
        modulo
    ] in nomes_selecionados
]


if modulos_selecionados:

    st.caption(
        f"{len(modulos_selecionados)} de "
        f"{len(ORDEM_RELATORIOS)} relatórios selecionados."
    )

else:

    st.warning(
        "Selecione pelo menos um relatório "
        "para iniciar a execução."
    )

em_execucao = execucao_ativa()

coluna_executar, coluna_parar, coluna_atualizar = (
    st.columns(
        [2, 1, 1]
    )
)

with coluna_executar:

    executar = st.button(
        (
            "🟡 Execução em andamento"
            if em_execucao
            else "🚀 Executar Relatórios"
        ),
        use_container_width=True,
        disabled=(em_execucao or not modulos_selecionados),
        type="primary"
    )

with coluna_parar:

    parar_execucao = st.button(
        "⏹ Parar execução",
        use_container_width=True,
        disabled=not em_execucao,
        type="secondary"
    )

with coluna_atualizar:

    atualizar = st.button(
        "🔄 Atualizar Agora",
        use_container_width=True
    )


if atualizar:

    st.rerun()


if parar_execucao:

    try:

        parar_execucao_atual()

        st.success(
            "Execução interrompida com sucesso. "
            "O botão de execução foi liberado."
        )

        st.rerun()

    except Exception as erro:

        st.error(
            "Não foi possível interromper a execução: "
            f"{type(erro).__name__}: {erro}"
        )


# =====================================================
# AÇÃO DE EXECUÇÃO
# =====================================================

if executar:

    if data_inicio > data_fim:

        st.error(
            "A data inicial não pode ser maior "
            "que a data final."
        )

    else:

        periodo_inicio = (
            data_inicio.strftime(
                "%d/%m/%Y"
            )
            + " 00:00:00"
        )

        periodo_fim = (
            data_fim.strftime(
                "%d/%m/%Y"
            )
            + " 23:59:59"
        )

        try:

            resultado_inicio = iniciar_execucao(
                periodo_inicio,
                periodo_fim,
                modulos_selecionados
            )

            pid = resultado_inicio[
                "pid"
            ]

            avisos_logs = resultado_inicio[
                "avisos_logs"
            ]


            arquivos_excluidos = resultado_inicio[
                "arquivos_excluidos"
            ]

            st.success(
                f"Execução iniciada. Processo: {pid}"
            )


            if arquivos_excluidos:
                st.info(
                    f"{arquivos_excluidos} arquivo(s) da execução "
                    "anterior foram excluídos."
                )

            for aviso in avisos_logs:

                st.warning(
                    aviso
                )

            st.rerun()

        except Exception as erro:

            st.error(
                "Não foi possível iniciar a execução: "
                f"{type(erro).__name__}: {erro}"
            )


# =====================================================
# STATUS E MÉTRICAS
# =====================================================

status = carregar_status()

if em_execucao and not status:

    st.warning(
        "Existe uma execução em andamento, mas o painel "
        "ainda não recebeu informações dos relatórios. "
        "Consulte o log da execução abaixo."
    )


concluidos = sum(
    1
    for item in status.values()
    if item.get("status") == "CONCLUIDO"
)

executando = sum(
    1
    for item in status.values()
    if item.get("status") == "EXECUTANDO"
)

erros = sum(
    1
    for item in status.values()
    if item.get("status") == "ERRO"
)

cancelados = sum(
    1
    for item in status.values()
    if item.get("status") in {
        "REMOVIDO",
        "CANCELADO"
    }
)

pendentes = sum(
    1
    for item in status.values()
    if item.get("status") == "PENDENTE"
)


col1, col2, col3, col4, col5 = st.columns(
    5
)

col1.metric(
    "✅ Concluídos",
    concluidos
)

col2.metric(
    "🟡 Executando",
    executando
)

col3.metric(
    "❌ Erros",
    erros
)

col4.metric(
    "🚫 Cancelados",
    cancelados
)

col5.metric(
    "⏳ Pendentes",
    pendentes
)


# =====================================================
# STATUS DETALHADO
# =====================================================

st.divider()

st.header(
    "Status dos Relatórios"
)

if not status:

    st.info(
        (
            "A execução está sendo inicializada."
            if em_execucao
            else "Nenhuma execução registrada."
        )
    )

else:

    periodo_validacao = (
        data_inicio.strftime(
            "%d/%m/%Y"
        )
        + " 00:00:00"
    )

    modulos_ordenados = sorted(
        status.keys(),
        key=lambda modulo: (
            ORDEM_RELATORIOS.index(modulo)
            if modulo in ORDEM_RELATORIOS
            else len(ORDEM_RELATORIOS)
        )
    )

    for modulo in modulos_ordenados:

        info = status[
            modulo
        ]

        nome = NOMES_RELATORIOS.get(
            modulo,
            modulo
        )

        estado = info.get(
            "status",
            "PENDENTE"
        )

        detalhe = info.get(
            "detalhe"
        )

        ultima = (
            info.get(
                "ultima_atualizacao"
            )
            or "-"
        )

        arquivo_local = info.get(
            "arquivo_local"
        )

        arquivo_rede = info.get(
            "arquivo_rede"
        )

        local_ok = arquivo_local_existe(
            arquivo_local
        )

        rede_ok = arquivo_rede_existe(
            modulo,
            periodo_validacao,
            arquivo_rede
        )

        mensagem = (
            f"{nome}\n\n"
            f"Última atualização: {ultima}"
        )

        if estado == "CONCLUIDO":

            if local_ok:

                mensagem += (
                    "\n\n✅ Arquivo local localizado."
                )

            elif arquivo_local:

                mensagem += (
                    "\n\n⚠️ Arquivo local registrado, "
                    "mas não encontrado:\n"
                    f"{arquivo_local}"
                )

            else:

                mensagem += (
                    "\n\n⚠️ Arquivo local não informado."
                )

            if rede_ok:

                mensagem += (
                    "\n\n📤 Arquivo encontrado na rede."
                )

            elif arquivo_rede:

                mensagem += (
                    "\n\n❌ Arquivo de rede registrado, "
                    "mas não encontrado:\n"
                    f"{arquivo_rede}"
                )

            else:

                mensagem += (
                    "\n\n❌ Arquivo não registrado na rede."
                )

            if (
                local_ok
                and rede_ok
            ):

                st.success(
                    mensagem
                )

            else:

                st.warning(
                    mensagem
                )

        elif estado == "EXECUTANDO":

            st.warning(
                mensagem
                + "\n\n🟡 Relatório em execução."
            )

        elif estado == "PENDENTE":

            st.info(
                mensagem
                + "\n\n⏳ Aguardando execução."
            )

        elif estado == "REMOVIDO":

            st.warning(
                mensagem
                + "\n\n🚫 Exportação removida "
                  "ou cancelada pelo sistema."
            )

        elif estado == "CANCELADO":

            st.warning(
                mensagem
                + "\n\n⏹ Execução interrompida "
                  "manualmente pelo usuário."
            )

        elif estado == "ERRO":

            st.error(
                mensagem
                + "\n\n❌ "
                + (
                    detalhe
                    or "Erro não informado."
                )
            )

        else:

            st.info(
                mensagem
                + "\n\nStatus não reconhecido."
            )


# =====================================================
# DOWNLOADS
# =====================================================

st.divider()

st.header(
    "Downloads"
)

arquivos = []

try:

    arquivos = [
        caminho
        for caminho in PASTA_DOWNLOADS.rglob("*")
        if caminho.is_file()
    ]

except OSError as erro:

    st.warning(
        "Não foi possível listar a pasta de downloads: "
        f"{erro}"
    )


if not arquivos:

    st.warning(
        "Nenhum arquivo encontrado."
    )

else:

    try:

        arquivos.sort(
            key=lambda caminho: caminho.stat().st_mtime,
            reverse=True
        )

    except OSError:

        arquivos.sort(
            key=lambda caminho: caminho.name.lower()
        )

    for indice, caminho in enumerate(
        arquivos
    ):

        try:

            dados = caminho.read_bytes()

            st.download_button(
                label=f"📄 {caminho.name}",
                data=dados,
                file_name=caminho.name,
                mime="text/csv",
                use_container_width=True,
                key=(
                    f"download_"
                    f"{indice}_"
                    f"{caminho.name}"
                )
            )

        except OSError as erro:

            st.warning(
                f"Não foi possível abrir "
                f"{caminho.name}: {erro}"
            )


# =====================================================
# DIAGNÓSTICO
# =====================================================

with st.expander(
    "Debug status.json"
):

    st.json(
        status
    )


with st.expander(
    "Log da execução",
    expanded=em_execucao
):

    if CAMINHO_LOG_WORKER.exists():

        try:

            conteudo_log = (
                CAMINHO_LOG_WORKER.read_text(
                    encoding="utf-8",
                    errors="replace"
                )
            )

            if conteudo_log.strip():

                st.code(
                    conteudo_log[-30000:],
                    language="text"
                )

            elif em_execucao:

                st.info(
                    "O processo foi iniciado e ainda não "
                    "produziu mensagens de log."
                )

            else:

                st.info(
                    "O arquivo de log está vazio."
                )

        except PermissionError:

            st.warning(
                "O log está temporariamente ocupado. "
                "Ele será lido na próxima atualização."
            )

        except OSError as erro:

            st.warning(
                "Não foi possível ler o log: "
                f"{erro}"
            )

    elif em_execucao:

        st.info(
            "A execução está sendo inicializada. "
            "O arquivo worker.log ainda será criado."
        )

    else:

        st.info(
            "Nenhum log de execução disponível."
        )


# =====================================================
# ENCERRAMENTO DO RELATPY
# =====================================================

st.divider()

coluna_info, coluna_fechar = st.columns(
    [3, 1]
)

with coluna_info:

    if em_execucao:

        st.caption(
            "Uma execução está ativa. Use Parar execução "
            "antes de encerrar o RelatPy se quiser cancelar "
            "os relatórios."
        )

    else:

        st.caption(
            "Use o botão ao lado para encerrar o servidor "
            "do RelatPy com segurança."
        )


with coluna_fechar:

    fechar_relatpy = st.button(
        "⏻ Fechar RelatPy",
        use_container_width=True,
        type="secondary"
    )


if fechar_relatpy:

    try:

        solicitar_encerramento()

        st.success(
            "Encerramento solicitado. "
            "Esta aba pode ser fechada."
        )

        st.stop()

    except Exception as erro:

        st.error(
            "Não foi possível solicitar o encerramento: "
            f"{type(erro).__name__}: {erro}"
        )


# =====================================================
# RODAPÉ
# =====================================================

st.divider()

st.caption(
    "RelatPy | SGIND + IQOS | Paralelismo habilitado"
)