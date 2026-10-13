RELATORIOS = [
    {
        "modulo": "compensacao",              # nome do arquivo em relatorios/ (sem .py)
        "paralelo": True,
        "url": "https://indicadoresenergisaess.scl.corp/sgind/#/relatcompensacao",
        "empresa_desejada": "ESS",
        "periodo_apuracao": "MENSAL",
        "nome_arquivo": "detalhamento_compensacao.csv",
        "formato_data": "datahora"
    },

    {
    "modulo": "reclamacao",
    "paralelo": True,
    "url": "https://indicadoresenergisaess.scl.corp/sgind/#/relatreclamecoes",
    "empresa_desejada": "ESS",
    "nome_arquivo": "Reclamacao.csv",
    "formato_data": "datahora"
    },

    {
    "modulo": "interrupcoes_cliente",
    "paralelo": True,
    "url": "https://indicadoresenergisaess.scl.corp/sgind/#/relatinterrupcoes",
    "empresa_desejada": "ESS",
    "nome_arquivo": "Interrupcoes_Clientes.csv",
    "formato_data": "datahora"
    },

    {
    "modulo": "todas_ocorrencias",
    "paralelo": True,
    "url": "https://indicadoresenergisaess.scl.corp/sgind/#/relatatendtodasocorrencias",
    "empresa_desejada": "ESS",
    "nome_arquivo": "TodasOcorrencias.csv",
    "formato_data": "datahora"
    },

    {
    "modulo": "dia_critico",
    "paralelo": True,
    "nome_arquivo": "Dia_Critico.csv",
    "url": "https://indicadoresenergisaess.scl.corp/sgind/#/relatdiacritico",
    "formato_data": "datahora"
    },

    {
    "modulo": "interrupcoes_evento",
    "paralelo": True,
    "nome_arquivo": "Interrupcoes_Evento.csv",
    "empresa_desejada": "ESS",
    "url": "https://indicadoresenergisaess.scl.corp/sgind/#/relatinterrupevento",
    "formato_data": "datahora"
    },
    {
    "modulo": "iqos_resultados",
    "paralelo": False,
    "url": "https://indicadoresenergisaess.scl.corp/iqos/#/listaresultados",
    "nome_arquivo": "ATENDIMENTO_CHEIO"
    },
    {
    "modulo": "inconsistentes",
    "paralelo": False,
    "url": "https://indicadoresenergisaess.scl.corp/sgind/#/ocorrenciasInconsistentes",
    "nome_arquivo": "OcorrenciaInconsistente.csv",
    "formato_data": "datahora"
    },
    {
    "modulo": "tarefas",
    "formato_data": "datahora",
    "url": ("https://indicadoresenergisaess.scl.corp/sgind/#/relattarefas"),
    "empresa_desejada": "ESS",
    "nome_arquivo": "Relatorio_Tarefas.csv",
    "paralelo": True,
    },
    # --- Exemplo de como adicionar o 2º relatório ---
    # Copie relatorios/_template.py para relatorios/nome_do_relatorio.py,
    # ajuste os seletores dentro dele, e adicione a entrada aqui:
    #
    # {
    #     "modulo": "nome_do_relatorio",
    #     "url": "https://indicadoresenergisaess.scl.corp/sgind/#/outrapagina",
    #     "empresa_desejada": "ESS",          # remova/ajuste se não se aplicar
    #     "periodo_apuracao": "MENSAL",       # remova/ajuste se não se aplicar
    #     "nome_arquivo": "relatorio_2.csv",
    #     "formato_data": "data",             # "data" (dd/mm/yyyy) ou "datahora" (dd/mm/yyyy hh:mm:ss)
    # },

    # ... repita para os relatórios 3 a 7 ...
]