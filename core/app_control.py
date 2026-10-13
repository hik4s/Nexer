import json
import os
import signal
from pathlib import Path


RAIZ = Path(
    __file__
).resolve().parent.parent

PASTA_STATUS = (
    RAIZ
    / "status"
)

ARQUIVO_STREAMLIT_PID = (
    PASTA_STATUS
    / "streamlit.pid"
)

ARQUIVO_ENCERRAMENTO = (
    PASTA_STATUS
    / "encerrar_streamlit.json"
)


def preparar_controle():

    PASTA_STATUS.mkdir(
        parents=True,
        exist_ok=True
    )


def registrar_streamlit_pid(
    pid
):

    preparar_controle()

    ARQUIVO_STREAMLIT_PID.write_text(
        str(pid),
        encoding="utf-8"
    )


def ler_streamlit_pid():

    if not ARQUIVO_STREAMLIT_PID.exists():

        return None

    try:

        return int(
            ARQUIVO_STREAMLIT_PID.read_text(
                encoding="utf-8"
            ).strip()
        )

    except (
        OSError,
        ValueError
    ):

        return None


def solicitar_encerramento():

    preparar_controle()

    dados = {
        "encerrar": True
    }

    caminho_temporario = (
        ARQUIVO_ENCERRAMENTO
        .with_suffix(".tmp")
    )

    caminho_temporario.write_text(
        json.dumps(
            dados,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )

    os.replace(
        caminho_temporario,
        ARQUIVO_ENCERRAMENTO
    )


def encerramento_solicitado():

    if not ARQUIVO_ENCERRAMENTO.exists():

        return False

    try:

        dados = json.loads(
            ARQUIVO_ENCERRAMENTO.read_text(
                encoding="utf-8"
            )
        )

        return bool(
            dados.get(
                "encerrar"
            )
        )

    except (
        OSError,
        json.JSONDecodeError
    ):

        return False


def limpar_solicitacao():

    try:

        ARQUIVO_ENCERRAMENTO.unlink(
            missing_ok=True
        )

    except OSError:

        pass


def encerrar_processo(
    pid
):

    if not pid:

        return False

    try:

        if os.name == "nt":

            os.kill(
                pid,
                signal.SIGTERM
            )

        else:

            os.kill(
                pid,
                signal.SIGTERM
            )

        return True

    except OSError:

        return False