import os
import re
from datetime import datetime

from playwright.async_api import expect

from relatorios.compensacao import (
    exportar,
    apertar_ok,
    atualizar_pagina,
)


print("IQOS RESULTADOS IMPORTADO")


MESES_IQOS = {
    1: "JAN",
    2: "FEV",
    3: "MAR",
    4: "ABR",
    5: "MAI",
    6: "JUN",
    7: "JUL",
    8: "AGO",
    9: "SET",
    10: "OUT",
    11: "NOV",
    12: "DEZ",
}


def obter_mes_iqos(periodo_inicio):
    data = datetime.strptime(
        periodo_inicio,
        "%d/%m/%Y %H:%M:%S",
    )
    return MESES_IQOS[data.month]


async def desmarcar_somente_oficial(page):
    try:
        checkbox = page.locator("#somenteOficial")
        await checkbox.wait_for(
            state="attached",
            timeout=0,
        )

        if await checkbox.is_checked():
            await checkbox.click(timeout=0)
            await expect(checkbox).not_to_be_checked(
                timeout=0,
            )
            print("[OK] Somente Oficial desmarcado.")
        else:
            print(
                "[INFO] Somente Oficial já estava "
                "desmarcado."
            )

    except Exception as erro:
        raise RuntimeError(
            f"Erro ao alterar Somente Oficial: {erro}"
        ) from erro


async def clicar_listar(page):
    botao_listar = page.get_by_role(
        "button",
        name="Listar",
    )

    await botao_listar.wait_for(
        state="visible",
        timeout=0,
    )
    await expect(botao_listar).to_be_enabled(timeout=0)
    await botao_listar.click(timeout=0)

    primeira_linha = page.locator("tr").filter(
        has_text="ATENDIMENTO_CHEIO"
    ).first

    await primeira_linha.wait_for(
        state="visible",
        timeout=0,
    )

    print("[OK] Listagem carregada.")


async def expandir_item_indice(
    page,
    texto,
    indice=0,
    proximo_texto=None,
    proximo_indice=0,
):
    linhas = page.locator("tr").filter(
        has_text=texto
    )
    linha = linhas.nth(indice)

    await linha.wait_for(
        state="visible",
        timeout=0,
    )

    botao = linha.locator(
        "button.p-treetable-toggler"
    ).first

    await botao.wait_for(
        state="visible",
        timeout=0,
    )
    await expect(botao).to_be_enabled(timeout=0)
    await botao.scroll_into_view_if_needed()

    print(
        f"[INFO] Expandindo: {texto} "
        f"(índice={indice})"
    )

    await botao.click(timeout=0)

    if proximo_texto is not None:
        proxima_linha = page.locator("tr").filter(
            has_text=proximo_texto
        ).nth(proximo_indice)

        await proxima_linha.wait_for(
            state="visible",
            timeout=0,
        )

        print(
            f"[OK] Expandido: {texto}. "
            f"Próximo item visível: {proximo_texto} "
            f"(índice={proximo_indice})"
        )
    else:
        print(
            f"[OK] Clique de expansão realizado: "
            f"{texto} (índice={indice})"
        )


async def abrir_insumos_resultado(page):
    linha_resultado = page.locator("tr").filter(
        has_text="RESULTADO"
    ).first

    await linha_resultado.wait_for(
        state="visible",
        timeout=0,
    )

    texto = await linha_resultado.inner_text()
    print(f"[DEBUG] Resultado encontrado:\n{texto}")

    dropdown = linha_resultado.locator(
        "button.p-splitbutton-dropdown"
    ).first

    await dropdown.wait_for(
        state="visible",
        timeout=0,
    )
    await expect(dropdown).to_be_enabled(timeout=0)
    await dropdown.scroll_into_view_if_needed()
    await dropdown.click(timeout=0)

    menu_insumos = page.get_by_text(
        "Insumos",
        exact=True,
    )

    await menu_insumos.wait_for(
        state="visible",
        timeout=0,
    )
    await menu_insumos.click(timeout=0)

    print("[OK] Insumos selecionado.")


async def abrir_aba_insumos(page):
    aba = page.locator('[role="tab"]').filter(
        has_text="Insumos [ATENDIMENTO_CHEIO]"
    ).first

    await aba.wait_for(
        state="visible",
        timeout=0,
    )
    await aba.click(timeout=0)
    await expect(aba).to_have_attribute(
        "aria-selected",
        "true",
        timeout=0,
    )

    print("[OK] Aba Insumos aberta.")


async def abrir_downloads_iqos(page):
    try:
        popover = page.locator(
            "div.p-popover-content"
        ).first

        if await popover.is_visible():
            print(
                "[INFO] Central Downloads IQOS já está "
                "aberta."
            )
            return

        envelope = page.locator(
            "div.notification-wrapper"
        )

        await envelope.wait_for(
            state="visible",
            timeout=0,
        )
        await expect(envelope).to_be_enabled(timeout=0)
        await envelope.scroll_into_view_if_needed()
        await envelope.click(timeout=0)

        await popover.wait_for(
            state="visible",
            timeout=0,
        )

        print("[OK] Central Downloads IQOS aberta.")

    except Exception as erro:
        raise RuntimeError(
            f"Erro ao abrir Central Downloads IQOS: {erro}"
        ) from erro


async def aguardar_processamento_iqos(page):
    await abrir_downloads_iqos(page)

    card_final = page.locator(
        "div.p-card-content"
    ).filter(
        has_text="ATENDIMENTO_CHEIO"
    ).filter(
        has_text=re.compile(
            r"CONCLUÍDO|REMOVIDO",
            re.IGNORECASE,
        )
    ).first

    await card_final.wait_for(
        state="visible",
        timeout=0,
    )

    texto = await card_final.inner_text()
    texto_upper = texto.upper()

    print(f"\n[DEBUG] CARD FINAL\n{texto}\n")

    if "REMOVIDO" in texto_upper:
        print("[ERRO] Exportação removida.")
        return "REMOVIDO"

    print("[OK] Exportação concluída.")
    return "CONCLUIDO"


async def baixar_arquivo_iqos(page):
    card = page.locator(
        "div.p-card-content"
    ).filter(
        has_text="ATENDIMENTO_CHEIO"
    ).filter(
        has_text=re.compile(
            r"CONCLUÍDO",
            re.IGNORECASE,
        )
    ).first

    await card.wait_for(
        state="visible",
        timeout=0,
    )

    botao_download = card.locator(
        "button.p-button-secondary.p-button-icon-only, "
        "button.ui-button-secondary.p-button-icon-only"
    ).first

    await botao_download.wait_for(
        state="visible",
        timeout=0,
    )
    await expect(botao_download).to_be_enabled(timeout=0)

    async with page.expect_download(
        timeout=0,
    ) as download_info:
        await botao_download.click(timeout=0)

    download = await download_info.value

    os.makedirs("downloads", exist_ok=True)
    caminho = os.path.join(
        "downloads",
        download.suggested_filename,
    )

    await download.save_as(caminho)

    print(f"[OK] Arquivo salvo: {caminho}")
    return caminho


async def processar(
    page,
    info,
    periodo_inicio,
    periodo_fim,
):
    print("=== IQOS RESULTADOS ===")

    mes = obter_mes_iqos(periodo_inicio)
    print(f"[INFO] Mês identificado: {mes}")

    print("1- Desmarcando Somente Oficial")
    await desmarcar_somente_oficial(page)

    print("2- Clicando em Listar")
    await clicar_listar(page)

    print("3- Expandindo primeiro ATENDIMENTO_CHEIO")
    await expandir_item_indice(
        page,
        texto="ATENDIMENTO_CHEIO",
        indice=0,
        proximo_texto="ATENDIMENTO_CHEIO",
        proximo_indice=1,
    )

    print("4- Expandindo segundo ATENDIMENTO_CHEIO")
    await expandir_item_indice(
        page,
        texto="ATENDIMENTO_CHEIO",
        indice=1,
        proximo_texto=mes,
        proximo_indice=0,
    )

    print(f"5- Expandindo mês {mes}")
    await expandir_item_indice(
        page,
        texto=mes,
        indice=0,
        proximo_texto="DIARIO",
        proximo_indice=0,
    )

    print("6- Expandindo DIARIO")
    await expandir_item_indice(
        page,
        texto="DIARIO",
        indice=0,
        proximo_texto="CONJ_ELETRICO",
        proximo_indice=0,
    )

    print("7- Expandindo CONJ_ELETRICO")
    await expandir_item_indice(
        page,
        texto="CONJ_ELETRICO",
        indice=0,
        proximo_texto="RESULTADO",
        proximo_indice=0,
    )

    print("8- Abrindo menu Insumos")
    await abrir_insumos_resultado(page)

    print("9- Abrindo aba Insumos")
    await abrir_aba_insumos(page)

    print("10- Exportando CSV")
    await exportar(page)

    print("11- Confirmando")
    await apertar_ok(page)

    print("12- Atualizando página")
    await atualizar_pagina(page)
    await page.wait_for_load_state(
        "networkidle",
        timeout=0,
    )

    print("13- Abrindo central de downloads IQOS")
    await abrir_downloads_iqos(page)

    print("14- Aguardando processamento")
    status_exportacao = await aguardar_processamento_iqos(
        page
    )

    if status_exportacao == "REMOVIDO":
        return {
            "status": "REMOVIDO",
            "arquivo": info["nome_arquivo"],
        }

    print("15- Reabrindo central de downloads")
    await abrir_downloads_iqos(page)

    print("16- Baixando arquivo")
    arquivo_baixado = await baixar_arquivo_iqos(page)

    return {
        "status": "CONCLUIDO",
        "arquivo": arquivo_baixado,
    }
