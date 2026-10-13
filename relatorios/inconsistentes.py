from playwright.async_api import expect

from relatorios.compensacao import (
    apertar_ok,
    atualizar_pagina,
    abrir_downloads,
    aguardar_processamento,
    baixar_arquivo,
)


print(
    "INCONSISTENTES IMPORTADO"
)


async def preencher_campo_data(
    campo,
    valor,
    nome_campo,
):
    """
    Preenche um campo de data PrimeNG simulando
    a digitação real da pessoa usuária.
    """

    await campo.wait_for(
        state="visible",
        timeout=0,
    )

    await expect(
        campo
    ).to_be_editable(
        timeout=0,
    )

    await campo.scroll_into_view_if_needed()

    await campo.click(
        timeout=0,
    )

    await campo.press(
        "Control+A"
    )

    await campo.press(
        "Backspace"
    )

    await campo.press_sequentially(
        valor,
        delay=50,
    )

    await campo.press(
        "Tab"
    )

    valor_preenchido = (
        await campo.input_value()
    ).strip()

    if valor_preenchido != valor:
        raise RuntimeError(
            f"O campo {nome_campo} não foi preenchido "
            "corretamente. "
            f"Esperado: '{valor}'. "
            f"Encontrado: '{valor_preenchido}'."
        )

    print(
        f"[OK] {nome_campo}: {valor_preenchido}",
        flush=True,
    )


async def preencher_datas_inconsistentes(
    page,
    data_inicio,
    data_fim,
):
    """
    Preenche Data Hora Início e Data Hora Fim.

    A página utiliza componentes diferentes:
    - p-datepicker para a data inicial;
    - p-calendar para a data final.
    """

    data_inicio = str(
        data_inicio
    ).strip()[:16]

    data_fim = str(
        data_fim
    ).strip()[:16]

    painel = page.locator(
        "p-panel"
    ).filter(
        has_text="Data Hora Início"
    ).filter(
        has_text="Data Hora Fim"
    ).first

    await painel.wait_for(
        state="visible",
        timeout=0,
    )

    campo_inicio = painel.locator(
        "p-datepicker "
        "input.p-datepicker-input"
    ).first

    campo_fim = painel.locator(
        "p-calendar "
        "input.p-datepicker-input"
    ).first

    await campo_inicio.wait_for(
        state="visible",
        timeout=0,
    )

    await campo_fim.wait_for(
        state="visible",
        timeout=0,
    )

    print(
        "[INFO] Preenchendo Data Hora Início...",
        flush=True,
    )

    await preencher_campo_data(
        campo_inicio,
        data_inicio,
        "Data Hora Início",
    )

    print(
        "[INFO] Preenchendo Data Hora Fim...",
        flush=True,
    )

    await preencher_campo_data(
        campo_fim,
        data_fim,
        "Data Hora Fim",
    )

    print(
        "[OK] Período preenchido: "
        f"{data_inicio} até {data_fim}",
        flush=True,
    )


async def pesquisar_inconsistentes(
    page,
):
    """
    Executa a pesquisa e aguarda o ciclo real
    de carregamento da página.

    Fluxo:
    1. botão Pesquisar fica disponível;
    2. clique em Pesquisar;
    3. spinner aparece;
    4. spinner desaparece;
    5. botão Exportar (.csv) fica disponível.
    """

    botao_pesquisar = page.get_by_role(
        "button",
        name="Pesquisar",
        exact=True,
    )

    spinner = page.locator(
        "ngx-spinner .ngx-spinner-overlay"
    ).first

    botao_exportar = page.get_by_role(
        "button",
        name="Exportar (.csv)",
        exact=True,
    )

    await botao_pesquisar.wait_for(
        state="visible",
        timeout=0,
    )

    await expect(
        botao_pesquisar
    ).to_be_enabled(
        timeout=0,
    )

    print(
        "[INFO] Iniciando pesquisa...",
        flush=True,
    )

    await botao_pesquisar.click(
        timeout=0,
    )

    print(
        "[AGUARDANDO] Carregamento iniciar...",
        flush=True,
    )

    await spinner.wait_for(
        state="visible",
        timeout=0,
    )

    print(
        "[AGUARDANDO] Carregamento finalizar...",
        flush=True,
    )

    await spinner.wait_for(
        state="hidden",
        timeout=0,
    )

    print(
        "[AGUARDANDO] Botão Exportar (.csv)...",
        flush=True,
    )

    await botao_exportar.wait_for(
        state="visible",
        timeout=0,
    )

    await expect(
        botao_exportar
    ).to_be_enabled(
        timeout=0,
    )

    print(
        "[OK] Pesquisa concluída. "
        "Botão Exportar (.csv) disponível.",
        flush=True,
    )


async def exportar_inconsistentes(
    page,
):
    """
    Clica somente no botão principal Exportar (.csv).

    Não clica na seta lateral da sanfona e não utiliza
    o botão Exportar TXT número Ocorrências.
    """

    botao_exportar = page.get_by_role(
        "button",
        name="Exportar (.csv)",
        exact=True,
    )

    await botao_exportar.wait_for(
        state="visible",
        timeout=0,
    )

    await expect(
        botao_exportar
    ).to_be_enabled(
        timeout=0,
    )

    await botao_exportar.scroll_into_view_if_needed()

    await botao_exportar.click(
        timeout=0,
    )

    print(
        "[OK] Exportar (.csv) acionado.",
        flush=True,
    )


async def processar(
    page,
    info,
    periodo_inicio,
    periodo_fim,
):
    """
    Executa o fluxo completo do relatório
    de inconsistências.
    """

    nome_arquivo = info.get(
        "nome_arquivo"
    )

    if not nome_arquivo:
        raise ValueError(
            "A configuração do relatório inconsistentes "
            "deve conter a chave 'nome_arquivo'."
        )

    print(
        "=== INCONSISTENTES ===",
        flush=True,
    )

    print(
        "1- Preenchendo datas",
        flush=True,
    )

    await preencher_datas_inconsistentes(
        page,
        periodo_inicio,
        periodo_fim,
    )

    print(
        "2- Pesquisando",
        flush=True,
    )

    await pesquisar_inconsistentes(
        page
    )

    print(
        "3- Exportando",
        flush=True,
    )

    await exportar_inconsistentes(
        page
    )

    print(
        "4- Confirmando exportação",
        flush=True,
    )

    await apertar_ok(
        page
    )

    print(
        "5- Atualizando página",
        flush=True,
    )

    await atualizar_pagina(
        page
    )

    print(
        "6- Abrindo central de downloads",
        flush=True,
    )

    await abrir_downloads(
        page
    )

    print(
        "7- Aguardando processamento",
        flush=True,
    )

    status_exportacao = await aguardar_processamento(
        page
    )

    if status_exportacao == "REMOVIDO":
        print(
            "[AVISO] Exportação removida pelo sistema.",
            flush=True,
        )

        return {
            "status": "REMOVIDO",
            "arquivo": None,
            "detalhe": (
                "Exportação removida pelo sistema."
            ),
        }

    print(
        "8- Reabrindo central de downloads",
        flush=True,
    )

    await abrir_downloads(
        page
    )

    print(
        "9- Baixando arquivo",
        flush=True,
    )

    arquivo_baixado = await baixar_arquivo(
        page,
        nome_arquivo,
    )

    if not arquivo_baixado:
        raise FileNotFoundError(
            "O relatório de inconsistências não retornou "
            "o caminho do arquivo baixado."
        )

    print(
        f"[OK] Relatório finalizado: {arquivo_baixado}",
        flush=True,
    )

    return {
        "status": "CONCLUIDO",
        "arquivo": arquivo_baixado,
    }