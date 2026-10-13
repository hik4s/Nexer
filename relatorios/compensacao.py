from playwright.async_api import expect

import os

print("COMPENSACAO IMPORTADO")


async def processar(
    page,
    info,
    periodo_inicio,
    periodo_fim
):
    """
    Ponto de entrada padrão chamado pelo downloader.py.
    Executa toda a sequência específica do relatório de Compensação.
    """

    print("1- Selecionando Empresa")

    await selecionar_empresa(
        page,
        info["empresa_desejada"]
    )

    print("2- Preenchendo datas")

    await preencher_datas_compensacao(
        page,
        periodo_inicio,
        periodo_fim
    )

    print("3- Preenchendo período")

    await selecionar_periodo_apuracao(
        page,
        info["periodo_apuracao"]
    )

    print(
        "[OK] Empresa, datas e período preenchidos."
    )

    print("4- Pesquisando")

    await pesquisar(page)

    await aguardar_fim_carregamento(
        page
    )

    await abrir_relatorio(page)

    await selecionar_relatorio(page)

    await abrir_detalhamento(page)

    await abrir_aba_detalhamento_compensacao(
        page
    )

    await exportar(page)

    await apertar_ok(page)

    await atualizar_pagina(page)

    await abrir_downloads(page)

    print(
        "8- Aguardando processamento"
    )

    status_exportacao = await aguardar_processamento(
        page
    )

    if status_exportacao == "REMOVIDO":

        print(
            "[ERRO] Exportação removida pelo sistema."
        )

        return {
            "status": "REMOVIDO",
            "arquivo": info["nome_arquivo"]
        }

    print(
        "9- Reabrindo downloads"
    )

    await abrir_downloads(page)

    print(
        "10- Baixando arquivo"
    )

    arquivo_baixado = await baixar_arquivo(
        page,
        info["nome_arquivo"]
    )

    print(
        "[OK] Relatório finalizado."
    )

    return {
        "status": "CONCLUIDO",
        "arquivo": arquivo_baixado
    }


async def selecionar_empresa(page, empresa="ESS"):
    await page.locator("p-select").first.click()

    await page.get_by_text(empresa, exact=True).click()

    valor = await page.locator(
        "p-select span[role='combobox']"
    ).first.inner_text()

    print(f"Empresa selecionada: {valor}")


async def preencher_datas_compensacao(page, data_inicio, data_fim):
    campos = page.locator("p-datepicker input.p-datepicker-input")

    campo_inicio = campos.nth(0)
    campo_fim = campos.nth(1)

    await campo_inicio.click()
    await campo_inicio.press("Control+A")
    await campo_inicio.fill(data_inicio)
    await campo_inicio.press("Tab")

    print("Campo início:", await campo_inicio.input_value())

    await campo_fim.click()
    await campo_fim.press("Control+A")
    await campo_fim.fill(data_fim)
    await campo_fim.press("Tab")

    print("Campo fim:", await campo_fim.input_value())


async def selecionar_periodo_apuracao(page, periodo="MENSAL"):
    """
    Seleciona o período de apuração:
    MENSAL / TRIMESTRAL / ANUAL_ACUMULADO
    """
    await page.locator("p-multiselect").click()

    opcao = page.locator(
        f'li[role="option"][aria-label="{periodo}"]'
    )
    await opcao.wait_for(state="visible")
    await opcao.click()
    await expect(opcao).to_have_attribute("aria-selected", "true")

    await page.keyboard.press("Escape")


async def pesquisar(page):
    botao = page.get_by_role("button", name="Pesquisar")
    await botao.click()
    print("[OK] Pesquisa executada.")

async def aguardar_fim_carregamento(page):
    spinner = page.locator("ngx-spinner .ngx-spinner-overlay")

    if await spinner.count() > 0:
        await spinner.first.wait_for(
            state="hidden",
            timeout=0
        )

    print("[OK] Carregamento finalizado.")


async def abrir_relatorio(page):
    await page.get_by_role(
        "tab", name="Relatório de Compensação #0"
    ).click()
    print("[OK] Relatório de Compensação aberto.")


async def selecionar_relatorio(page):
    linha = page.locator('tr[data-p-selectable-row="true"]').first
    await linha.click(button="right")
    print("[OK] Menu de contexto aberto.")


async def abrir_detalhamento(page):
    await page.get_by_text("Detalhar Compensação", exact=True).click()
    await page.get_by_role(
        "tab", name="Detalhamento Compensação #1"
    ).wait_for(state="visible")
    print("[OK] Detalhamento aberto.")


async def abrir_aba_detalhamento_compensacao(page):
    await page.get_by_role(
        "tab", name="Detalhamento Compensação #1"
    ).click()
    print("[OK] Aba de detalhamento aberta.")


async def exportar(page):
    await page.get_by_role("button", name="Exportar (.csv)").click()
    print("[OK] Exportação solicitada.")


async def apertar_ok(page):
    botao_ok = page.get_by_role("button", name="OK")
    await botao_ok.click()
    await botao_ok.wait_for(state="hidden")
    print("[OK] Confirmação realizada.")


async def atualizar_pagina(page):
    """
    Atualiza a página sem limite de tempo finito.

    Aguarda o DOM principal ser reconstruído, sem depender
    do evento load, que pode nunca terminar em aplicações
    Angular com requisições persistentes.
    """

    url_anterior = page.url

    print(
        "[INFO] Atualizando página...",
        flush=True,
    )

    await page.reload(
        wait_until="domcontentloaded",
        timeout=0,
    )

    await page.wait_for_url(
        url_anterior,
        wait_until="domcontentloaded",
        timeout=0,
    )

    print(
        "[OK] Página atualizada.",
        flush=True,
    )


async def abrir_downloads(page):

    for tentativa in range(5):

        popover = page.locator(
            "div.p-popover"
        )

        if await popover.count() > 0:

            try:

                visivel = await popover.first.is_visible()

                if visivel:

                    print(
                        "[OK] Central de downloads já está aberta."
                    )

                    return

            except Exception:
                pass

        print(
            f"[INFO] Abrindo central de downloads (tentativa {tentativa + 1})..."
        )

        await page.locator(
            "div.notification-btn"
        ).click()

        popover = page.locator(
            "div.p-popover"
        )
        await popover.first.wait_for(state="visible")

        if await popover.count() > 0:

            try:

                visivel = await popover.first.is_visible()

                if visivel:

                    print(
                        "[OK] Central de downloads aberta."
                    )

                    return

            except Exception:
                pass

    raise Exception(
        "Não foi possível manter a central de downloads aberta."
    )


async def aguardar_processamento(page):

    while True:

        cards = page.locator(
            "div.p-card-content"
        )

        total_cards = await cards.count()

        if total_cards == 0:

            print(
                "[INFO] Nenhum card encontrado."
            )

            await atualizar_pagina(page)

            await abrir_downloads(page)

            continue

        texto = await cards.nth(0).inner_text()

        texto_upper = texto.upper()

        if "PROCESSANDO" in texto_upper:

            print(
                "[INFO] Ainda processando..."
            )

            await atualizar_pagina(page)

            await abrir_downloads(page)

            continue

        if "CONCLUÍDO" in texto_upper:

            print(
                "[OK] Processamento concluído."
            )

            return "CONCLUIDO"

        if "REMOVIDO" in texto_upper:

            print(
                "[ERRO] Exportação removida."
            )

            return "REMOVIDO"

        print(
            "[INFO] Status não identificado."
        )

        await atualizar_pagina(page)

        await abrir_downloads(page)


async def baixar_arquivo(
    page,
    nome_arquivo_esperado
):
    os.makedirs("downloads", exist_ok=True)

    texto_busca = nome_arquivo_esperado.removesuffix(".csv")
    print(f"Procurando download contendo: {texto_busca}")

    card = page.locator(
        "div.p-card-content"
    ).filter(
        has_text=texto_busca
    ).filter(
        has_text="CONCLUÍDO"
    ).first

    await card.wait_for(
        state="visible",
        timeout=0
    )

    print(
        "[OK] Card concluído localizado: ",
        await card.inner_text()
    )

    botao = card.locator(
        "button.p-button-secondary.p-button-icon-only, "
        "button.ui-button-secondary.p-button-icon-only"
    ).first

    await botao.wait_for(
        state="visible",
        timeout=0
    )

    await expect(botao).to_be_enabled(timeout=0)

    async with page.expect_download(timeout=0) as download_info:
        await botao.click(timeout=0)

    download = await download_info.value

    caminho = os.path.join(
        "downloads",
        download.suggested_filename
    )

    await download.save_as(caminho)

    print(f"[OK] Arquivo baixado: {caminho}")
    return caminho
