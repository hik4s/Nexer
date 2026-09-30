import importlib
import os

from playwright.async_api import async_playwright

from auth import tentar_login
from config import RELATORIOS

from core.executor import (
    atualizar_arquivo,
    executar_lote,
    executar_relatorio,
    inicializar_status,
)

from core.file_manager import (
    copiar_relatorio_para_servidor,
)


# =====================================================
# CONFIGURAÇÕES
# =====================================================

PASTA_DOWNLOADS = "downloads"

RESULTADOS_RELATORIOS = []


os.makedirs(
    PASTA_DOWNLOADS,
    exist_ok=True,
)


# =====================================================
# FILTRO DOS RELATÓRIOS
# =====================================================

def filtrar_relatorios_selecionados(
    relatorios,
    modulos_selecionados=None,
):
    """
    Retorna somente os relatórios selecionados.

    Quando nenhuma seleção for informada,
    todos os relatórios serão executados.
    """

    if modulos_selecionados is None:
        return list(relatorios)

    if not isinstance(
        modulos_selecionados,
        (list, tuple, set),
    ):
        raise TypeError(
            "modulos_selecionados deve ser uma "
            "lista, tupla ou conjunto."
        )

    modulos_configurados = {
        item["modulo"]
        for item in relatorios
        if item.get("modulo")
    }

    modulos_solicitados = {
        modulo.strip()
        for modulo in modulos_selecionados
        if (
            isinstance(modulo, str)
            and modulo.strip()
        )
    }

    if not modulos_solicitados:
        raise ValueError(
            "Nenhum relatório foi selecionado."
        )

    modulos_desconhecidos = (
        modulos_solicitados
        - modulos_configurados
    )

    if modulos_desconhecidos:
        raise ValueError(
            "Os seguintes relatórios não existem "
            "na configuração: "
            + ", ".join(
                sorted(modulos_desconhecidos)
            )
        )

    relatorios_execucao = [
        item
        for item in relatorios
        if item.get("modulo")
        in modulos_solicitados
    ]

    if not relatorios_execucao:
        raise ValueError(
            "Nenhum relatório válido foi selecionado."
        )

    return relatorios_execucao


# =====================================================
# RESUMO FINAL
# =====================================================

def exibir_resumo_final():
    """
    Exibe no log um resumo dos relatórios processados.
    """

    print(
        "\n"
    )

    print(
        "=" * 60
    )

    print(
        "RESUMO FINAL DOS RELATÓRIOS"
    )

    print(
        "=" * 60
    )

    concluidos = 0
    removidos = 0
    cancelados = 0
    erros = 0

    if not RESULTADOS_RELATORIOS:
        print(
            "\nNenhum resultado foi registrado."
        )

    for item in RESULTADOS_RELATORIOS:

        status = item.get(
            "status",
            "ERRO",
        )

        relatorio = item.get(
            "relatorio",
            "desconhecido",
        )

        arquivo = item.get(
            "arquivo",
        )

        if status == "CONCLUIDO":

            concluidos += 1

            print(
                f"\n✅ {relatorio}"
            )

            print(
                "   Status: CONCLUÍDO"
            )

            print(
                f"   Arquivo: {arquivo or 'não informado'}"
            )

        elif status == "REMOVIDO":

            removidos += 1

            print(
                f"\n🚫 {relatorio}"
            )

            print(
                "   Status: REMOVIDO"
            )

            print(
                f"   Arquivo: {arquivo or 'não gerado'}"
            )

        elif status == "CANCELADO":

            cancelados += 1

            print(
                f"\n⏹ {relatorio}"
            )

            print(
                "   Status: CANCELADO"
            )

        else:

            erros += 1

            print(
                f"\n⚠️ {relatorio}"
            )

            print(
                "   Status: ERRO"
            )

            print(
                "   Motivo: "
                f"{item.get('erro', 'Erro não informado.')}"
            )

    print(
        "\n"
        + "=" * 60
    )

    print(
        f"Concluídos: {concluidos}"
    )

    print(
        f"Removidos: {removidos}"
    )

    print(
        f"Cancelados: {cancelados}"
    )

    print(
        f"Erros: {erros}"
    )

    print(
        "=" * 60
    )


# =====================================================
# EXECUÇÃO DE UM RELATÓRIO
# =====================================================

async def baixar_um_relatorio(
    context,
    info,
    periodo_inicio,
    periodo_fim,
):
    """
    Abre uma página individual e executa um relatório.
    """

    modulo_nome = info.get(
        "modulo"
    )

    nome_arquivo = info.get(
        "nome_arquivo"
    )

    url = info.get(
        "url"
    )

    if not modulo_nome:
        raise ValueError(
            "A configuração do relatório não possui "
            "a chave 'modulo'."
        )

    if not nome_arquivo:
        raise ValueError(
            f"O relatório {modulo_nome} não possui "
            "a chave 'nome_arquivo'."
        )

    if not url:
        raise ValueError(
            f"O relatório {modulo_nome} não possui "
            "uma URL configurada."
        )

    page = await context.new_page()

    try:

        print(
            "\n"
            + "=" * 60,
            flush=True,
        )

        print(
            f"Iniciando módulo: {modulo_nome}",
            flush=True,
        )

        print(
            f"Arquivo esperado: {nome_arquivo}",
            flush=True,
        )

        print(
            "=" * 60,
            flush=True,
        )

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=0,
        )

        print(
            f"URL após navegação: {page.url}",
            flush=True,
        )

        if "login" in page.url.lower():
            raise RuntimeError(
                "O relatório foi redirecionado "
                f"para a página de login: {page.url}"
            )

        modulo = importlib.import_module(
            f"relatorios.{modulo_nome}"
        )

        if not hasattr(
            modulo,
            "processar",
        ):
            raise AttributeError(
                f"O módulo relatorios.{modulo_nome} "
                "não contém a função processar()."
            )

        resultado = await modulo.processar(
            page,
            info,
            periodo_inicio,
            periodo_fim,
        )

        if not isinstance(
            resultado,
            dict,
        ):
            raise TypeError(
                f"O módulo {modulo_nome} retornou um "
                "resultado inválido. Era esperado um dicionário."
            )

        status_resultado = resultado.get(
            "status"
        )

        if not status_resultado:
            raise KeyError(
                f"O módulo {modulo_nome} não retornou "
                "a chave obrigatória 'status'."
            )

        status_resultado = str(
            status_resultado
        ).upper()

        if status_resultado not in {
            "CONCLUIDO",
            "REMOVIDO",
            "CANCELADO",
            "ERRO",
        }:
            raise ValueError(
                f"O módulo {modulo_nome} retornou um "
                f"status inválido: {status_resultado}"
            )

        print(
            "\n"
            + "=" * 30,
            flush=True,
        )

        print(
            f"MÓDULO: {modulo_nome}",
            flush=True,
        )

        print(
            "RESULTADO COMPLETO:",
            flush=True,
        )

        print(
            resultado,
            flush=True,
        )

        print(
            "=" * 30
            + "\n",
            flush=True,
        )

        arquivo_local = resultado.get(
            "arquivo"
        )

        print(
            "[DEBUG] arquivo_local recebido: "
            f"{arquivo_local}",
            flush=True,
        )

        arquivo_rede = None

        if status_resultado == "CONCLUIDO":

            if not arquivo_local:
                raise FileNotFoundError(
                    f"O módulo {modulo_nome} foi marcado "
                    "como CONCLUIDO, mas não retornou "
                    "o caminho do arquivo."
                )

            arquivo_local = os.path.abspath(
                arquivo_local
            )

            if not os.path.isfile(
                arquivo_local
            ):
                raise FileNotFoundError(
                    "O arquivo retornado pelo relatório "
                    f"não existe: {arquivo_local}"
                )

            if os.path.getsize(
                arquivo_local
            ) == 0:
                raise RuntimeError(
                    f"O arquivo está vazio: {arquivo_local}"
                )

            try:

                arquivo_rede = (
                    copiar_relatorio_para_servidor(
                        modulo=modulo_nome,
                        caminho_arquivo=arquivo_local,
                        periodo_inicio=periodo_inicio,
                    )
                )

                print(
                    f"[OK] Arquivo local: {arquivo_local}",
                    flush=True,
                )

                print(
                    f"[OK] Arquivo rede: {arquivo_rede}",
                    flush=True,
                )

            except Exception as erro_rede:

                print(
                    "[AVISO] Falha ao enviar para rede: "
                    f"{type(erro_rede).__name__}: "
                    f"{erro_rede}",
                    flush=True,
                )

        atualizar_arquivo(
            modulo_nome,
            arquivo_local,
            arquivo_rede,
        )

        RESULTADOS_RELATORIOS.append(
            {
                "relatorio": modulo_nome,
                "arquivo": arquivo_local,
                "arquivo_rede": arquivo_rede,
                "status": status_resultado,
            }
        )

        print(
            f"[OK] {nome_arquivo} finalizado "
            f"com status {status_resultado}.",
            flush=True,
        )

        return resultado

    except Exception as erro:

        print(
            f"[ERRO] {nome_arquivo}: "
            f"{type(erro).__name__}: {erro}",
            flush=True,
        )

        RESULTADOS_RELATORIOS.append(
            {
                "relatorio": modulo_nome,
                "arquivo": None,
                "status": "ERRO",
                "erro": (
                    f"{type(erro).__name__}: {erro}"
                ),
            }
        )

        raise

    finally:

        try:
            await page.close()

        except Exception as erro_fechamento:
            print(
                "[AVISO] Não foi possível fechar a página "
                f"do relatório {modulo_nome}: "
                f"{erro_fechamento}",
                flush=True,
            )


# =====================================================
# EXECUÇÃO DE TODOS OS SELECIONADOS
# =====================================================

async def baixar_todos_os_relatorios(
    usuario,
    senha,
    periodo_inicio,
    periodo_fim,
    modulos_selecionados=None,
):
    """
    Executa somente os relatórios selecionados.

    Quando modulos_selecionados for None,
    executa todos os relatórios configurados.
    """

    print(
        "Entrou na função baixar_todos_os_relatorios",
        flush=True,
    )

    RESULTADOS_RELATORIOS.clear()

    relatorios_execucao = (
        filtrar_relatorios_selecionados(
            RELATORIOS,
            modulos_selecionados,
        )
    )

    modulos_execucao = [
        info["modulo"]
        for info in relatorios_execucao
    ]

    print(
        "Relatórios selecionados: "
        + ", ".join(
            modulos_execucao
        ),
        flush=True,
    )

    inicializar_status(
        relatorios_execucao
    )

    relatorios_paralelos = [
        info
        for info in relatorios_execucao
        if info.get(
            "paralelo",
            False,
        )
    ]

    relatorios_sequenciais = [
        info
        for info in relatorios_execucao
        if not info.get(
            "paralelo",
            False,
        )
    ]

    print(
        "PARALELO: "
        + ", ".join(
            info["modulo"]
            for info in relatorios_paralelos
        ),
        flush=True,
    )

    print(
        "SEQUENCIAL: "
        + ", ".join(
            info["modulo"]
            for info in relatorios_sequenciais
        ),
        flush=True,
    )

    canal_navegador = os.environ.get(
        "RELATPY_BROWSER_CHANNEL",
        "msedge",
    )

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch(
            channel=canal_navegador,
            headless=True,
        )

        context = await browser.new_context(
            accept_downloads=True,
        )

        try:

            await tentar_login(
                context,
                usuario,
                senha,
            )

            print(
                "Total de relatórios selecionados: "
                f"{len(relatorios_execucao)}",
                flush=True,
            )

            print(
                "Relatórios paralelos: "
                f"{len(relatorios_paralelos)}",
                flush=True,
            )

            print(
                "Relatórios sequenciais: "
                f"{len(relatorios_sequenciais)}",
                flush=True,
            )

            tarefas = []

            for info in relatorios_paralelos:

                print(
                    "\nAgendando paralelo: "
                    f"{info['modulo']}",
                    flush=True,
                )

                tarefa = executar_relatorio(
                    baixar_um_relatorio(
                        context,
                        info,
                        periodo_inicio,
                        periodo_fim,
                    ),
                    info["modulo"],
                )

                tarefas.append(
                    tarefa
                )

            if tarefas:

                await executar_lote(
                    tarefas
                )

            for info in relatorios_sequenciais:

                print(
                    "\nExecutando sequencial: "
                    f"{info['modulo']}",
                    flush=True,
                )

                try:

                    await executar_relatorio(
                        baixar_um_relatorio(
                            context,
                            info,
                            periodo_inicio,
                            periodo_fim,
                        ),
                        info["modulo"],
                    )

                except Exception as erro:

                    print(
                        "[ERRO] Falha no relatório "
                        f"{info['modulo']}: "
                        f"{type(erro).__name__}: {erro}",
                        flush=True,
                    )

            exibir_resumo_final()

        finally:

            try:
                await context.close()

            except Exception as erro_contexto:
                print(
                    "[AVISO] Não foi possível fechar "
                    f"o contexto: {erro_contexto}",
                    flush=True,
                )

            try:
                await browser.close()

            except Exception as erro_navegador:
                print(
                    "[AVISO] Não foi possível fechar "
                    f"o navegador: {erro_navegador}",
                    flush=True,
                )