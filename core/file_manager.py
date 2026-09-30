import os
import shutil
from datetime import datetime
from pathlib import Path


# =====================================================
# CONFIGURACOES
# =====================================================

FORMATO_PERIODO = "%d/%m/%Y %H:%M:%S"
PASTA_DOWNLOADS = Path("downloads")


# =====================================================
# PASTAS DA REDE
# =====================================================

PASTAS_SERVIDOR = {
    "compensacao": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\COMPENSACAO DETALHAMENTO"
    ),
    "reclamacao": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\RECLAMACOES"
    ),
    "interrupcoes_cliente": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\INTERRUPÇÕES POR CLIENTE"
    ),
    "interrupcoes_evento": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\EVENTOS"
    ),
    "todas_ocorrencias": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\OCORRENCIAS"
    ),
    "inconsistentes": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\INCONSISTENTES"
    ),
    "tarefas": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\TAREFAS"
    ),
    "dia_critico": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\DIA CRITICO"
    ),
    "iqos_resultados": (
        r"\\fs-ess.scl.corp\dados$\DEOP\DEOP-CPQE"
        r"\00_PÓS OPERAÇÃO\01_BOLETIM_DIÁRIO"
        r"\BI_IQOS_SGIND\Atendimentos Emergencial - TMA"
        r"\IQOS - TMA"
    ),
}


# =====================================================
# NOMES DOS MESES
# =====================================================

MESES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Marco",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


# =====================================================
# VALIDACOES
# =====================================================

def converter_periodo(periodo_inicio):
    """Converte e valida o periodo recebido pelo projeto."""
    try:
        return datetime.strptime(
            periodo_inicio,
            FORMATO_PERIODO,
        )
    except (TypeError, ValueError) as erro:
        raise ValueError(
            "Periodo inicial invalido. Formato esperado: "
            "dd/mm/aaaa hh:mm:ss. "
            f"Valor recebido: {periodo_inicio!r}"
        ) from erro


def validar_modulo(modulo):
    """Confirma que o modulo possui destino de rede autorizado."""
    if modulo not in PASTAS_SERVIDOR:
        raise ValueError(
            f"Destino nao configurado para o modulo: {modulo}"
        )


def validar_arquivo_origem(caminho_arquivo):
    """Valida o arquivo local antes da copia para a rede."""
    origem = Path(caminho_arquivo).resolve()

    if not origem.is_file():
        raise FileNotFoundError(
            f"Arquivo local nao encontrado: {origem}"
        )

    if origem.stat().st_size == 0:
        raise ValueError(
            f"O arquivo local esta vazio: {origem}"
        )

    return origem


# =====================================================
# NOMES DOS ARQUIVOS
# =====================================================

def gerar_nome_final(
    modulo,
    periodo_inicio,
):
    """Gera o nome final do arquivo no servidor."""
    validar_modulo(modulo)
    data = converter_periodo(periodo_inicio)
    prefixo = data.strftime("%m_%Y")

    nomes = {
        "compensacao": (
            f"{prefixo}_eventos_compensacao_detalhamento.csv"
        ),
        "dia_critico": (
            f"{prefixo}_dia_critico.csv"
        ),
        "interrupcoes_evento": (
            f"{prefixo}_eventos.csv"
        ),
        "reclamacao": (
            f"{prefixo}_reclamacoes.csv"
        ),
        "todas_ocorrencias": (
            f"{prefixo}_ocorrencias.csv"
        ),
        "interrupcoes_cliente": (
            f"{prefixo}_interrupcoes_por_cliente.csv"
        ),
        "inconsistentes": (
            f"{prefixo}_Inconsistentes.csv"
        ),
        "tarefas": (
            f"{prefixo}_tarefas.csv"
        ),
    }

    if modulo == "iqos_resultados":
        nome_mes = MESES[data.month]
        return (
            f"{prefixo}_eventos_"
            f"{nome_mes}_cheio.csv"
        )

    nome = nomes.get(modulo)

    if not nome:
        raise ValueError(
            f"Nome final nao configurado para o modulo: {modulo}"
        )

    return nome


# =====================================================
# DESTINO FINAL DA REDE
# =====================================================

def obter_destino_rede(modulo):
    """Retorna a pasta de rede configurada para o modulo."""
    return PASTAS_SERVIDOR.get(modulo)


def gerar_caminho_final_rede(
    modulo,
    periodo_inicio,
):
    """Monta o caminho completo esperado na rede."""
    pasta = obter_destino_rede(modulo)

    if not pasta:
        return None

    nome = gerar_nome_final(
        modulo,
        periodo_inicio,
    )

    return os.path.join(
        pasta,
        nome,
    )


# =====================================================
# LOCALIZAR ARQUIVO LOCAL
# =====================================================

def localizar_arquivo(
    nome_arquivo,
    pasta_base=PASTA_DOWNLOADS,
):
    """Localiza um arquivo pelo nome dentro de downloads."""
    nome_seguro = Path(nome_arquivo).name
    pasta = Path(pasta_base)

    if not pasta.is_dir():
        return None

    for caminho in pasta.rglob(nome_seguro):
        if caminho.is_file():
            return str(caminho.resolve())

    return None


# =====================================================
# RENOMEAR ARQUIVO LOCAL
# =====================================================

def renomear_arquivo(
    origem,
    novo_nome,
):
    """Renomeia um arquivo local sem permitir subdiretorios no nome."""
    caminho_origem = validar_arquivo_origem(origem)
    nome_seguro = Path(novo_nome).name

    if nome_seguro != novo_nome:
        raise ValueError(
            "O novo nome deve conter somente o nome do arquivo."
        )

    destino = caminho_origem.with_name(nome_seguro)

    if destino.exists() and destino != caminho_origem:
        destino.unlink()

    caminho_origem.replace(destino)
    return str(destino)


# =====================================================
# COPIAR PARA SERVIDOR
# =====================================================

def copiar_relatorio_para_servidor(
    modulo,
    caminho_arquivo,
    periodo_inicio,
):
    """
    Copia o relatorio para a rede com o nome final.

    A copia e feita primeiro para um arquivo temporario.
    O destino final so e substituido depois da copia completa.
    """
    validar_modulo(modulo)
    origem = validar_arquivo_origem(caminho_arquivo)

    pasta_destino = Path(
        obter_destino_rede(modulo)
    )

    if not pasta_destino.is_dir():
        raise FileNotFoundError(
            f"Pasta de rede nao encontrada: {pasta_destino}"
        )

    nome_final = gerar_nome_final(
        modulo,
        periodo_inicio,
    )

    destino = pasta_destino / nome_final
    temporario = pasta_destino / f".{nome_final}.tmp"

    try:
        if temporario.exists():
            temporario.unlink()

        shutil.copy2(
            origem,
            temporario,
        )

        if not temporario.is_file():
            raise FileNotFoundError(
                "O arquivo temporario nao foi criado na rede: "
                f"{temporario}"
            )

        if temporario.stat().st_size != origem.stat().st_size:
            raise IOError(
                "O tamanho do arquivo copiado nao corresponde "
                "ao arquivo local."
            )

        os.replace(
            temporario,
            destino,
        )

    except Exception:
        try:
            temporario.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    print(
        f"[OK] Arquivo enviado para rede: {destino}",
        flush=True,
    )

    return str(destino)


# =====================================================
# VALIDACAO DE ARQUIVO NA REDE
# =====================================================

def arquivo_existe_no_servidor(
    modulo,
    periodo_inicio,
):
    """Confirma a existencia do arquivo final esperado na rede."""
    try:
        caminho = gerar_caminho_final_rede(
            modulo,
            periodo_inicio,
        )

        if not caminho:
            return False

        arquivo = Path(caminho)

        return (
            arquivo.is_file()
            and arquivo.stat().st_size > 0
        )

    except (
        OSError,
        TypeError,
        ValueError,
    ):
        return False


# =====================================================
# TESTE LOCAL DE NOMES E DESTINOS
# =====================================================

if __name__ == "__main__":
    periodo = "01/09/2026 00:00:00"

    for modulo in PASTAS_SERVIDOR:
        print(
            modulo,
            "->",
            gerar_caminho_final_rede(
                modulo,
                periodo,
            ),
        )
