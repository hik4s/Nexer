import re

from playwright.async_api import expect

from relatorios.compensacao import (
    apertar_ok,
    atualizar_pagina,
    abrir_downloads,
    aguardar_processamento,
    baixar_arquivo,
)


print("TAREFAS IMPORTADO")


async def selecionar_empresa_tarefas(
    page,
    empresa="ESS",
):
    """Seleciona a empresa no painel Filtros Hierarquia."""
    painel_hierarquia = page.locator("p-panel").filter(
        has_text="Filtros Hierarquia"
    ).first

    await painel_hierarquia.wait_for(
        state="visible",
        timeout=0,
    )

    empresa_select = painel_hierarquia.locator(
        "app-dd-empresas p-select"
    ).first

    valor_empresa = empresa_select.locator(
        "span[role='combobox']"
    ).first

    await empresa_select.wait_for(
        state="visible",
        timeout=0,
    )

    valor_atual = (
        await valor_empresa.inner_text()
    ).strip()

    if valor_atual != empresa:
        await empresa_select.click(timeout=0)

        opcao_empresa = page.get_by_role(
            "option",
            name=empresa,
            exact=True,
        )

        if await opcao_empresa.count() == 0:
            opcao_empresa = page.get_by_text(
                empresa,
                exact=True,
            )

        await opcao_empresa.first.wait_for(
            state="visible",
            timeout=0,
        )
        await opcao_empresa.first.click(timeout=0)

    await expect(valor_empresa).to_have_text(
        empresa,
        timeout=0,
    )

    print(
        f"[OK] Empresa selecionada: {empresa}",
        flush=True,
    )


async def preencher_campo_data(
    campo,
    valor,
    nome_campo,
):
    """Preenche um campo PrimeNG simulando digitação real."""
    await campo.wait_for(
        state="visible",
        timeout=0,
    )

    await expect(campo).to_be_editable(
        timeout=0,
    )

    await campo.scroll_into_view_if_needed()
    await campo.click(timeout=0)
    await campo.press("Control+A")
    await campo.press("Backspace")
    await campo.press_sequentially(
        valor,
        delay=50,
    )
    await campo.press("Tab")

    valor_preenchido = (
        await campo.input_value()
    ).strip()

    if valor_preenchido != valor:
        raise RuntimeError(
            f"O campo {nome_campo} não foi preenchido corretamente. "
            f"Esperado: '{valor}'. "
            f"Encontrado: '{valor_preenchido}'."
        )

    print(
        f"[OK] {nome_campo}: {valor_preenchido}",
        flush=True,
    )


async def preencher_datas_tarefas(
    page,
    data_inicio,
    data_fim,
):
    """Preenche Data Inicial e Data Final no painel Tarefas."""
    data_inicio = str(data_inicio).strip()[:16]
    data_fim = str(data_fim).strip()[:16]

    painel_tarefas = page.locator("p-panel").filter(
        has_text="Tarefas"
    ).filter(
        has_text="Data Inicial"
    ).filter(
        has_text="Data Final"
    ).first

    await painel_tarefas.wait_for(
        state="visible",
        timeout=0,
    )

    campos = painel_tarefas.locator(
        "p-datepicker input.p-datepicker-input"
    )

    await expect(campos).to_have_count(
        2,
        timeout=0,
    )

    await preencher_campo_data(
        campos.nth(0),
        data_inicio,
        "Data Inicial",
    )

    await preencher_campo_data(
        campos.nth(1),
        data_fim,
        "Data Final",
    )

    print(
        "[OK] Período preenchido: "
        f"{data_inicio} até {data_fim}",
        flush=True,
    )


def localizar_aba_resultado_tarefas(page):
    """Localiza a aba Tarefas #0 aceitando ícones adicionais."""
    return page.get_by_role(
        "tab",
        name=re.compile(r"^Tarefas\s*#\s*0"),
    ).first


async def pesquisar_tarefas(page):
    """Executa a pesquisa e aguarda a criação da aba Tarefas #0."""
    painel_tarefas = page.locator("p-panel").filter(
        has_text="Tarefas"
    ).filter(
        has_text="Data Inicial"
    ).filter(
        has_text="Data Final"
    ).first

    botao_pesquisar = painel_tarefas.get_by_role(
        "button",
        name="Pesquisar",
        exact=True,
    )

    await botao_pesquisar.wait_for(
        state="visible",
        timeout=0,
    )

    await expect(botao_pesquisar).to_be_enabled(
        timeout=0,
    )

    print(
        "[INFO] Iniciando pesquisa de Tarefas...",
        flush=True,
    )

    await botao_pesquisar.click(timeout=0)

    aba_resultado = localizar_aba_resultado_tarefas(page)

    print(
        "[AGUARDANDO] Criação da aba Tarefas #0...",
        flush=True,
    )

    await aba_resultado.wait_for(
        state="visible",
        timeout=0,
    )

    spinner = page.locator(
        "ngx-spinner .ngx-spinner-overlay"
    ).first

    if await spinner.count() > 0:
        await spinner.wait_for(
            state="hidden",
            timeout=0,
        )

    print(
        "[OK] Pesquisa concluída. Aba Tarefas #0 criada.",
        flush=True,
    )


async def abrir_relatorio_tarefas(page):
    """Abre a aba de resultado Tarefas #0."""
    aba = localizar_aba_resultado_tarefas(page)

    print(
        "[AGUARDANDO] Aba Tarefas #0 ficar disponível...",
        flush=True,
    )

    await aba.wait_for(
        state="visible",
        timeout=0,
    )

    spinner = page.locator(
        "ngx-spinner .ngx-spinner-overlay"
    ).first

    if await spinner.count() > 0:
        await spinner.wait_for(
            state="hidden",
            timeout=0,
        )

    selecionada = await aba.get_attribute(
        "aria-selected"
    )

    if selecionada != "true":
        await aba.scroll_into_view_if_needed()
        await aba.click(timeout=0)

    await expect(aba).to_have_attribute(
        "aria-selected",
        "true",
        timeout=0,
    )

    print(
        "[OK] Aba Tarefas #0 aberta.",
        flush=True,
    )


def localizar_botao_exportar_tarefas(page):
    """
    Localiza o botão principal Exportar (.csv)
    dentro do painel de resultado atualmente ativo.
    """
    painel_ativo = page.locator(
        "div[role='tabpanel'][aria-hidden='false']"
    ).last

    rotulo_exportar = painel_ativo.locator(
        "span.p-button-label"
    ).filter(
        has_text="Exportar (.csv)"
    ).first

    return rotulo_exportar.locator(
        "xpath=ancestor::button[1]"
    )


async def exportar_tarefas(page):
    """Clica somente no botão principal Exportar (.csv)."""
    botao_exportar = localizar_botao_exportar_tarefas(page)

    await botao_exportar.wait_for(
        state="visible",
        timeout=0,
    )

    await expect(botao_exportar).to_be_enabled(
        timeout=0,
    )

    classe = (
        await botao_exportar.get_attribute("class")
        or ""
    )

    if "p-splitbutton-button" not in classe:
        raise RuntimeError(
            "O elemento encontrado não é o botão principal "
            "de exportação. "
            f"Classe encontrada: {classe}"
        )

    if "p-splitbutton-dropdown" in classe:
        raise RuntimeError(
            "O seletor encontrou incorretamente "
            "o botão lateral da sanfona."
        )

    await botao_exportar.scroll_into_view_if_needed()

    print(
        "[INFO] Botão principal Exportar (.csv) localizado.",
        flush=True,
    )

    await botao_exportar.click(timeout=0)

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
    """Executa o fluxo completo do relatório Tarefas."""
    empresa = info.get("empresa_desejada")
    nome_arquivo = info.get("nome_arquivo")

    if not empresa:
        raise ValueError(
            "A configuração de Tarefas deve conter "
            "a chave 'empresa_desejada'."
        )

    if not nome_arquivo:
        raise ValueError(
            "A configuração de Tarefas deve conter "
            "a chave 'nome_arquivo'."
        )

    print("=== TAREFAS ===", flush=True)

    print("1- Selecionando empresa", flush=True)
    await selecionar_empresa_tarefas(
        page,
        empresa,
    )

    print("2- Preenchendo datas", flush=True)
    await preencher_datas_tarefas(
        page,
        periodo_inicio,
        periodo_fim,
    )

    print("3- Pesquisando", flush=True)
    await pesquisar_tarefas(page)

    print("4- Abrindo aba Tarefas #0", flush=True)
    await abrir_relatorio_tarefas(page)

    print("5- Exportando", flush=True)
    await exportar_tarefas(page)

    print("6- Confirmando exportação", flush=True)
    await apertar_ok(page)

    print("7- Atualizando página", flush=True)
    await atualizar_pagina(page)

    print("8- Abrindo central de downloads", flush=True)
    await abrir_downloads(page)

    print("9- Aguardando processamento", flush=True)
    status_exportacao = await aguardar_processamento(page)

    if status_exportacao == "REMOVIDO":
        print(
            "[AVISO] Exportação removida pelo sistema.",
            flush=True,
        )

        return {
            "status": "REMOVIDO",
            "arquivo": None,
            "detalhe": "Exportação removida pelo sistema.",
        }

    print("10- Reabrindo central de downloads", flush=True)
    await abrir_downloads(page)

    print("11- Baixando arquivo", flush=True)
    arquivo_baixado = await baixar_arquivo(
        page,
        nome_arquivo,
    )

    if not arquivo_baixado:
        raise FileNotFoundError(
            "O relatório Tarefas não retornou "
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
