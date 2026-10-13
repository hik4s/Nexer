import asyncio
import json
import os
import tempfile
from datetime import datetime


STATUS = {}

MAX_PARALELO = 9

SEMAFORO = asyncio.Semaphore(
    MAX_PARALELO
)

PASTA_STATUS = "status"

CAMINHO_STATUS = os.path.join(
    PASTA_STATUS,
    "status.json"
)


def obter_data_hora_atual():

    return datetime.now().strftime(
        "%d/%m/%Y %H:%M:%S"
    )


def salvar_status():

    os.makedirs(
        PASTA_STATUS,
        exist_ok=True
    )

    descritor, caminho_temporario = tempfile.mkstemp(
        prefix="status_",
        suffix=".json",
        dir=PASTA_STATUS,
        text=True
    )

    try:

        with os.fdopen(
            descritor,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                STATUS,
                arquivo,
                ensure_ascii=False,
                indent=4
            )

        os.replace(
            caminho_temporario,
            CAMINHO_STATUS
        )

    except Exception:

        try:

            if os.path.exists(
                caminho_temporario
            ):

                os.remove(
                    caminho_temporario
                )

        except OSError:

            pass

        raise


def limpar_status():

    STATUS.clear()

    os.makedirs(
        PASTA_STATUS,
        exist_ok=True
    )

    salvar_status()


def atualizar_status(
    modulo,
    status,
    detalhe=None
):

    if modulo not in STATUS:

        STATUS[modulo] = {
            "status": "PENDENTE",
            "detalhe": None,
            "arquivo_local": None,
            "arquivo_rede": None,
            "ultima_atualizacao": None
        }

    STATUS[modulo]["status"] = status

    STATUS[modulo]["detalhe"] = detalhe

    STATUS[modulo]["ultima_atualizacao"] = (
        obter_data_hora_atual()
    )

    salvar_status()


def atualizar_arquivo(
    modulo,
    arquivo_local=None,
    arquivo_rede=None
):

    if modulo not in STATUS:

        STATUS[modulo] = {
            "status": "PENDENTE",
            "detalhe": None,
            "arquivo_local": None,
            "arquivo_rede": None,
            "ultima_atualizacao": None
        }

    STATUS[modulo]["arquivo_local"] = (
        arquivo_local
    )

    STATUS[modulo]["arquivo_rede"] = (
        arquivo_rede
    )

    STATUS[modulo]["ultima_atualizacao"] = (
        obter_data_hora_atual()
    )

    salvar_status()


def atualizar_status_completo(
    modulo,
    status,
    detalhe=None,
    arquivo_local=None,
    arquivo_rede=None
):

    STATUS[modulo] = {
        "status": status,
        "detalhe": detalhe,
        "arquivo_local": arquivo_local,
        "arquivo_rede": arquivo_rede,
        "ultima_atualizacao": obter_data_hora_atual()
    }

    salvar_status()


def inicializar_status(
    relatorios
):

    STATUS.clear()

    for item in relatorios:

        modulo = item["modulo"]

        STATUS[modulo] = {
            "status": "PENDENTE",
            "detalhe": None,
            "arquivo_local": None,
            "arquivo_rede": None,
            "ultima_atualizacao": None
        }

    salvar_status()


async def executar_relatorio(
    corrotina,
    modulo
):

    async with SEMAFORO:

        atualizar_status(
            modulo,
            "EXECUTANDO"
        )

        try:

            resultado = await corrotina

            if not isinstance(
                resultado,
                dict
            ):

                raise TypeError(
                    f"O relatório {modulo} não retornou "
                    "um dicionário de resultado."
                )

            status_resultado = resultado.get(
                "status",
                "CONCLUIDO"
            )

            detalhe = resultado.get(
                "detalhe"
            )

            if status_resultado not in {
                "CONCLUIDO",
                "REMOVIDO",
                "CANCELADO",
                "ERRO"
            }:

                status_resultado = "CONCLUIDO"

            atualizar_status(
                modulo,
                status_resultado,
                detalhe
            )

            return resultado

        except Exception as erro:

            atualizar_status(
                modulo,
                "ERRO",
                f"{type(erro).__name__}: {erro}"
            )

            raise


async def executar_lote(
    tarefas
):

    return await asyncio.gather(
        *tarefas,
        return_exceptions=True
    )