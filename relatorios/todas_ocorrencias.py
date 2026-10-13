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

print("TODAS OCORRENCIAS IMPORTADO")


async def selecionar_empresa_todas_ocorrencias(
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


async def preencher_datas_todas_ocorrencias(
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


async def abrir_relatorio_todas_ocorrencias(
    page
):

    aba = page.get_by_role(
        "tab",
        name="Todas as Ocorrências #0"
    )

    await aba.wait_for(
        state="visible"
    )

    await aba.click()

    print(
        "[OK] Aba Todas as Ocorrências #0 aberta."
    )


async def processar(
    page,
    info,
    periodo_inicio,
    periodo_fim
):

    print(
        "=== TODAS OCORRENCIAS ==="
    )

    print(
        "1- Selecionando Empresa"
    )

    await selecionar_empresa_todas_ocorrencias(
        page,
        info["empresa_desejada"]
    )


    print(
        "2- Preenchendo datas"
    )

    await preencher_datas_todas_ocorrencias(
        page,
        periodo_inicio,
        periodo_fim
    )

    print(
        "3- Pesquisando"
    )

    await pesquisar(page)

    await aguardar_fim_carregamento(
        page
    )

    print(
        "3.1- Abrindo aba Todas as Ocorrências"
    )

    await abrir_relatorio_todas_ocorrencias(
        page
    )

    print(
        "4- Exportando"
    )

    await exportar(page)

    print(
        "5- Confirmando"
    )

    await apertar_ok(page)

    print(
        "6- Atualizando página"
    )

    await atualizar_pagina(page)

    print(
        "7- Abrindo downloads"
    )

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

    return {
        "status": "CONCLUIDO",
        "arquivo": arquivo_baixado
    }