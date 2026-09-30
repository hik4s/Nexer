import asyncio
import json
import sys
from datetime import datetime

from auth import obter_credenciais
from downloader import baixar_todos_os_relatorios


FORMATO_PERIODO = "%d/%m/%Y %H:%M:%S"


def pedir_data_hora(
    mensagem
):
    """
    Solicita uma data e hora pelo terminal até que
    o formato informado seja válido.
    """

    while True:

        texto = input(
            mensagem
        ).strip()

        try:

            datetime.strptime(
                texto,
                FORMATO_PERIODO
            )

            return texto

        except ValueError:

            print(
                "Formato inválido! "
                "Use dd/mm/aaaa hh:mm:ss."
            )


def capturar_periodo():
    """
    Solicita e valida o período da execução manual.
    """

    print(
        "=== Período para extração dos relatórios ==="
    )

    while True:

        inicio = pedir_data_hora(
            "Data/hora INÍCIO "
            "(dd/mm/aaaa hh:mm:ss): "
        )

        fim = pedir_data_hora(
            "Data/hora FIM "
            "(dd/mm/aaaa hh:mm:ss): "
        )

        dt_inicio = datetime.strptime(
            inicio,
            FORMATO_PERIODO
        )

        dt_fim = datetime.strptime(
            fim,
            FORMATO_PERIODO
        )

        if dt_inicio > dt_fim:

            print(
                "A data inicial não pode ser "
                "maior que a final."
            )

            continue

        return inicio, fim


def validar_modulos_selecionados(
    modulos_selecionados
):
    """
    Valida a estrutura da seleção recebida.

    None significa executar todos os relatórios.
    """

    if modulos_selecionados is None:

        return None

    if not isinstance(
        modulos_selecionados,
        list
    ):

        raise TypeError(
            "modulos_selecionados deve ser "
            "uma lista ou None."
        )

    modulos_validos = []

    for modulo in modulos_selecionados:

        if not isinstance(
            modulo,
            str
        ):

            continue

        modulo = modulo.strip()

        if (
            modulo
            and modulo not in modulos_validos
        ):

            modulos_validos.append(
                modulo
            )

    if not modulos_validos:

        raise ValueError(
            "Nenhum relatório válido foi selecionado."
        )

    return modulos_validos


async def executar_relatorios(
    periodo_inicio,
    periodo_fim,
    modulos_selecionados=None
):
    """
    Obtém as credenciais e inicia os relatórios.

    Quando modulos_selecionados for None,
    todos os relatórios configurados serão executados.
    """

    modulos_selecionados = (
        validar_modulos_selecionados(
            modulos_selecionados
        )
    )

    print(
        "[MAIN] Obtendo credenciais.",
        flush=True
    )

    usuario, senha = obter_credenciais()

    if (
        not usuario
        or not senha
    ):

        raise RuntimeError(
            "As credenciais não estão configuradas."
        )

    print(
        "[MAIN] Período: "
        f"{periodo_inicio} até {periodo_fim}",
        flush=True
    )

    if modulos_selecionados is None:

        print(
            "[MAIN] Todos os relatórios "
            "serão executados.",
            flush=True
        )

    else:

        print(
            "[MAIN] Relatórios selecionados: "
            + ", ".join(
                modulos_selecionados
            ),
            flush=True
        )

    await baixar_todos_os_relatorios(
        usuario,
        senha,
        periodo_inicio,
        periodo_fim,
        modulos_selecionados
    )

    print(
        "[MAIN] Execução dos relatórios finalizada.",
        flush=True
    )


def obter_modulos_argumento():
    """
    Permite informar módulos ao executar main.py
    diretamente pelo terminal.

    O argumento opcional deve ser um JSON:

    ["inconsistentes", "iqos_resultados"]
    """

    if len(sys.argv) < 4:

        return None

    try:

        modulos = json.loads(
            sys.argv[3]
        )

    except json.JSONDecodeError as erro:

        raise ValueError(
            "A seleção de relatórios não contém "
            "um JSON válido."
        ) from erro

    return validar_modulos_selecionados(
        modulos
    )


def main():
    """
    Entrada para execução manual pelo terminal.

    Sem argumentos, solicita o período interativamente.

    Com argumentos:
        main.py periodo_inicio periodo_fim modulos_json
    """

    if len(sys.argv) == 1:

        periodo_inicio, periodo_fim = (
            capturar_periodo()
        )

        modulos_selecionados = None

    elif len(sys.argv) in {
        3,
        4
    }:

        periodo_inicio = sys.argv[1]
        periodo_fim = sys.argv[2]

        # Valida o formato recebido pelo terminal.
        inicio = datetime.strptime(
            periodo_inicio,
            FORMATO_PERIODO
        )

        fim = datetime.strptime(
            periodo_fim,
            FORMATO_PERIODO
        )

        if inicio > fim:

            raise ValueError(
                "A data inicial não pode ser "
                "maior que a data final."
            )

        modulos_selecionados = (
            obter_modulos_argumento()
        )

    else:

        raise ValueError(
            "Uso esperado:\n"
            "python main.py\n\n"
            "ou:\n"
            "python main.py "
            "\"dd/mm/aaaa hh:mm:ss\" "
            "\"dd/mm/aaaa hh:mm:ss\" "
            "\"[\\\"modulo_1\\\", \\\"modulo_2\\\"]\""
        )

    print(
        "\nIniciando download dos relatórios...\n",
        flush=True
    )

    asyncio.run(
        executar_relatorios(
            periodo_inicio,
            periodo_fim,
            modulos_selecionados
        )
    )

    print(
        "\nProcesso concluído.",
        flush=True
    )


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nExecução interrompida pelo usuário.",
            flush=True
        )

        raise SystemExit(
            130
        )

    except Exception as erro:

        print(
            "\nFalha na execução: "
            f"{type(erro).__name__}: {erro}",
            flush=True
        )

        raise SystemExit(
            1
        )