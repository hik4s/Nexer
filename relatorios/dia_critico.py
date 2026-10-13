from playwright.async_api import expect

from datetime import datetime

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

print("DIA CRITICO IMPORTADO")


def obter_ano_mes(periodo_inicio):

    data = datetime.strptime(
        periodo_inicio,
        "%d/%m/%Y %H:%M:%S"
    )

    meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro"
    }

    return (
        str(data.year),
        meses[data.month]
    )


async def selecionar_ano(
    page,
    ano
):

    dropdown = page.locator(
        "p-dropdown"
    ).nth(0)

    await dropdown.click()

    await page.get_by_text(
        str(ano),
        exact=True
    ).click()
    await expect(
        dropdown.locator("span[role='combobox']")
    ).to_have_text(str(ano))

    print(
        f"Ano selecionado: {ano}"
    )


async def selecionar_mes(
    page,
    mes
):

    dropdown = page.locator(
        "p-dropdown"
    ).nth(1)

    await dropdown.click()

    await page.get_by_text(
        mes,
        exact=True
    ).click()
    await expect(
        dropdown.locator("span[role='combobox']")
    ).to_have_text(mes)

    print(
        f"Mês selecionado: {mes}"
    )


async def abrir_relatorio_dia_critico(
    page
):

    aba = page.get_by_role(
        "tab",
        name="Dia Crítico #0"
    )

    await aba.wait_for(
        state="visible"
    )

    await aba.click()

    print(
        "[OK] Aba Dia Crítico #0 aberta."
    )


async def processar(
    page,
    info,
    periodo_inicio,
    periodo_fim
):

    print(
        "=== DIA CRITICO ==="
    )

    ano, mes = obter_ano_mes(
        periodo_inicio
    )

    print(
        "1- Selecionando Ano"
    )

    await selecionar_ano(
        page,
        ano
    )

    print(
        "2- Selecionando Mês"
    )

    await selecionar_mes(
        page,
        mes
    )

    print(
        "3- Pesquisando"
    )

    await pesquisar(page)

    await aguardar_fim_carregamento(
        page
    )

    print(
        "3.1- Abrindo aba Dia Crítico"
    )

    await abrir_relatorio_dia_critico(
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