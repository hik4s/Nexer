import asyncio
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from main import executar_relatorios


# =====================================================
# CONFIGURAÇÃO DOS MÓDULOS
# =====================================================

MODULOS_PADRAO = [
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


FORMATO_PERIODO = "%d/%m/%Y %H:%M:%S"


# =====================================================
# CAMINHOS
# =====================================================

RAIZ = Path(
    __file__
).resolve().parent

PASTA_STATUS = (
    RAIZ
    / "status"
)

CAMINHO_PID = (
    PASTA_STATUS
    / "worker.pid"
)


PASTA_STATUS.mkdir(
    parents=True,
    exist_ok=True,
)


# =====================================================
# SELEÇÃO DOS RELATÓRIOS
# =====================================================

def obter_modulos_selecionados():
    """
    Lê os módulos enviados pelo dashboard.

    Argumentos esperados:

    sys.argv[0] = worker.py
    sys.argv[1] = período inicial
    sys.argv[2] = período final
    sys.argv[3] = JSON com os módulos selecionados

    Quando o quarto argumento não existe, todos os
    relatórios são executados para manter compatibilidade
    com chamadas mais antigas.
    """

    if len(sys.argv) < 4:
        return MODULOS_PADRAO.copy()

    argumento_modulos = sys.argv[3]

    try:
        dados = json.loads(
            argumento_modulos
        )

    except json.JSONDecodeError as erro:
        raise ValueError(
            "A lista de relatórios enviada ao worker "
            "não contém um JSON válido."
        ) from erro

    if not isinstance(
        dados,
        list,
    ):
        raise TypeError(
            "A seleção de relatórios deve ser uma lista."
        )

    modulos_validos = set(
        MODULOS_PADRAO
    )

    selecionados = []

    for modulo in dados:

        if not isinstance(
            modulo,
            str,
        ):
            continue

        modulo = modulo.strip()

        if (
            modulo in modulos_validos
            and modulo not in selecionados
        ):
            selecionados.append(
                modulo
            )

    if not selecionados:
        raise ValueError(
            "Nenhum relatório válido foi enviado "
            "para o worker."
        )

    return selecionados


# =====================================================
# VALIDAÇÃO DO PERÍODO
# =====================================================

def validar_periodo(
    periodo_inicio,
    periodo_fim,
):
    """
    Valida o formato e a ordem das datas recebidas.
    """

    try:
        inicio = datetime.strptime(
            periodo_inicio,
            FORMATO_PERIODO,
        )

    except ValueError as erro:
        raise ValueError(
            "O período inicial possui formato inválido. "
            "Formato esperado: dd/mm/aaaa hh:mm:ss. "
            f"Valor recebido: {periodo_inicio}"
        ) from erro

    try:
        fim = datetime.strptime(
            periodo_fim,
            FORMATO_PERIODO,
        )

    except ValueError as erro:
        raise ValueError(
            "O período final possui formato inválido. "
            "Formato esperado: dd/mm/aaaa hh:mm:ss. "
            f"Valor recebido: {periodo_fim}"
        ) from erro

    if inicio > fim:
        raise ValueError(
            "A data inicial não pode ser maior "
            "que a data final."
        )

    return inicio, fim


# =====================================================
# CONTROLE DO PID
# =====================================================

def registrar_pid():
    """
    Registra o PID do worker atual de forma atômica.

    O dashboard normalmente já registra esse PID,
    mas esta função também permite executar o worker
    diretamente pelo terminal.
    """

    caminho_temporario = (
        CAMINHO_PID.with_suffix(
            CAMINHO_PID.suffix + ".tmp"
        )
    )

    caminho_temporario.write_text(
        str(os.getpid()),
        encoding="utf-8",
    )

    os.replace(
        caminho_temporario,
        CAMINHO_PID,
    )


def remover_pid():
    """
    Remove o worker.pid somente se o arquivo pertencer
    ao processo atual.

    Isso impede que um processo antigo remova o PID
    correspondente a uma execução mais recente.
    """

    if not CAMINHO_PID.exists():
        return

    try:
        conteudo = CAMINHO_PID.read_text(
            encoding="utf-8"
        ).strip()

        if not conteudo:
            return

        pid_registrado = int(
            conteudo
        )

        if pid_registrado == os.getpid():
            CAMINHO_PID.unlink(
                missing_ok=True
            )

    except (
        OSError,
        ValueError,
    ):
        pass


# =====================================================
# EXECUÇÃO PRINCIPAL
# =====================================================

def main():
    """
    Valida os argumentos e inicia o fluxo assíncrono
    dos relatórios selecionados.
    """

    print(
        "[WORKER] Processo iniciado.",
        flush=True,
    )

    print(
        f"[WORKER] PID: {os.getpid()}",
        flush=True,
    )

    if len(sys.argv) < 3:
        raise ValueError(
            "Uso esperado:\n"
            "worker.py "
            "\"dd/mm/aaaa hh:mm:ss\" "
            "\"dd/mm/aaaa hh:mm:ss\" "
            "\"[\\\"modulo_1\\\", \\\"modulo_2\\\"]\""
        )

    if len(sys.argv) > 4:
        raise ValueError(
            "O worker recebeu argumentos além do esperado. "
            "São aceitos o período inicial, o período final "
            "e, opcionalmente, o JSON dos relatórios."
        )

    periodo_inicio = sys.argv[1]
    periodo_fim = sys.argv[2]

    modulos_selecionados = (
        obter_modulos_selecionados()
    )

    print(
        "[WORKER] Período selecionado: "
        f"{periodo_inicio} até {periodo_fim}",
        flush=True,
    )

    print(
        "[WORKER] Relatórios selecionados: "
        + ", ".join(
            modulos_selecionados
        ),
        flush=True,
    )

    validar_periodo(
        periodo_inicio,
        periodo_fim,
    )

    print(
        "[WORKER] Período validado.",
        flush=True,
    )

    registrar_pid()

    asyncio.run(
        executar_relatorios(
            periodo_inicio,
            periodo_fim,
            modulos_selecionados,
        )
    )

    print(
        "[WORKER] Execução concluída.",
        flush=True,
    )


# =====================================================
# PONTO DE ENTRADA
# =====================================================

if __name__ == "__main__":

    codigo_saida = 0

    try:
        main()

    except KeyboardInterrupt:
        codigo_saida = 130

        print(
            "\n[WORKER] Execução interrompida.",
            flush=True,
        )

    except Exception as erro:
        codigo_saida = 1

        print(
            "[WORKER] Falha durante a execução: "
            f"{type(erro).__name__}: {erro}",
            flush=True,
        )

        traceback.print_exc()

    finally:
        remover_pid()

    sys.exit(
        codigo_saida
    )