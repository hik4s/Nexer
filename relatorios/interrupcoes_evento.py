from playwright.async_api import expect

from relatorios.compensacao import (
    pesquisar,
    aguardar_fim_carregamento,
    exportar,
    apertar_ok,
    atualizar_pagina,
    abrir_downloads,
    aguardar_processamento,
    baixar_arquivo
)

print("INTERRUPCOES EVENTO IMPORTADO")


async def selecionar_empresa_interrupcoes_evento(
    page,
    empresa="ESS"
):

    empresa_select = page.locator(
        "app-dd-empresas p-select"
    ).first

    await empresa_select.click()

    await page.get_by_text(
        empresa,
        exact=True
    ).click()

    await expect(
        empresa_select.locator(".p-select-label")
    ).to_have_text(empresa)

    print(
        f"Empresa selecionada: {empresa}"
    )


async def preencher_datas_interrupcoes_evento(
    page,
    data_inicio,
    data_fim
):

    data_inicio = data_inicio[:16]
    data_fim = data_fim[:16]

    campos = page.locator(
        "input.p-datepicker-input"
    )

    total = await campos.count()

    print(
        f"Datepickers encontrados: {total}"
    )

    if total < 2:

        raise Exception(
            "Não foram encontrados os campos de data."
        )

    campo_inicio = campos.nth(0)
    campo_fim = campos.nth(1)

    await campo_inicio.click()
    await campo_inicio.press("Control+A")
    await campo_inicio.fill(data_inicio)
    await campo_inicio.press("Tab")

    print(
        "Campo início:",
        await campo_inicio.input_value()
    )

    await campo_fim.click()
    await campo_fim.press("Control+A")
    await campo_fim.fill(data_fim)
    await campo_fim.press("Tab")

    print(
        "Campo fim:",
        await campo_fim.input_value()
    )


async def desativar_candidato_calculo(
    page
):

    try:

        switch = page.locator(
            "p-inputswitch"
        ).first

        checkbox = switch.locator(
            'input[role="switch"]'
        )

        marcado = await checkbox.is_checked()

        if marcado:

            await switch.click()
            await expect(checkbox).not_to_be_checked()

            print(
                "[OK] Cand. ao cálculo desativado."
            )

        else:

            print(
                "[INFO] Cand. ao cálculo já estava desativado."
            )

    except Exception as erro:

        raise Exception(
            f"Erro ao alterar Cand. ao cálculo: {erro}"
        )


async def aguardar_spinner_finalizar(page):
    spinner = page.locator("ngx-spinner .ngx-spinner-overlay")

    if await spinner.count() > 0:
        await spinner.first.wait_for(
            state="hidden",
            timeout=0
        )


async def abrir_relatorio_interrupcoes_evento(
    page
):

    aba = page.get_by_role(
        "tab",
        name="Interrupções por Evento #0"
    )

    await aba.wait_for(
        state="visible",
        timeout=0
    )

    await aguardar_spinner_finalizar(page)
    await aba.click(timeout=0)
    await expect(aba).to_have_attribute(
        "aria-selected",
        "true",
        timeout=0
    )

    print(
        "[OK] Aba Interrupções por Evento #0 aberta."
    )


async def processar(
    page,
    info,
    periodo_inicio,
    periodo_fim
):

    print(
        "=== INTERRUPCOES EVENTO ==="
    )

    print(
        "1- Selecionando Empresa"
    )

    await selecionar_empresa_interrupcoes_evento(
        page,
        info["empresa_desejada"]
    )


    print(
        "2- Preenchendo Datas"
    )

    await preencher_datas_interrupcoes_evento(
        page,
        periodo_inicio,
        periodo_fim
    )

    print(
        "3- Desativando Cand. ao cálculo"
    )

    await desativar_candidato_calculo(
        page
    )

    print(
        "4- Pesquisando"
    )

    await pesquisar(page)

    await aguardar_fim_carregamento(
        page
    )

    print(
        "5- Abrindo aba Interrupções por Evento"
    )

    await abrir_relatorio_interrupcoes_evento(
        page
    )

    print(
        "6- Exportando"
    )

    await exportar(page)

    print(
        "7- Confirmando"
    )

    await apertar_ok(page)

    print(
        "8- Atualizando página"
    )

    await atualizar_pagina(page)

    print(
        "9- Abrindo downloads"
    )

    await abrir_downloads(page)

    print(
        "10- Aguardando processamento"
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
        "11- Reabrindo downloads"
    )

    await abrir_downloads(page)

    print(
        "12- Baixando arquivo"
    )

    arquivo_baixado = await baixar_arquivo(
    page,
    info["nome_arquivo"]
    )

    return {
        "status": "CONCLUIDO",
        "arquivo": arquivo_baixado
    }