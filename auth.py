import json
import os
import sys
from getpass import getpass
from pathlib import Path

from dotenv import dotenv_values


# =====================================================
# CAMINHOS E CONFIGURAÇÕES
# =====================================================

RAIZ_PROJETO = Path(
    __file__
).resolve().parent

CAMINHO_ENV = (
    RAIZ_PROJETO
    / ".env"
)

URL_LOGIN = (
    "https://indicadoresenergisaess.scl.corp/"
    "sgind/#/login"
)


# =====================================================
# EXCEÇÕES
# =====================================================

class LoginError(Exception):
    """
    Erro gerado quando a autenticação não é concluída.
    """


# =====================================================
# UTILIDADES
# =====================================================

def limpar_valor(
    valor
):

    if valor is None:

        return None

    valor = str(
        valor
    ).strip()

    return valor or None


def escapar_valor_env(
    valor
):

    return (
        str(valor)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "")
        .replace("\r", "")
    )


def entrada_interativa_disponivel():
    """
    Retorna True somente quando existe um terminal
    que pode receber input do usuário.
    """

    try:

        return (
            sys.stdin is not None
            and sys.stdin.isatty()
        )

    except Exception:

        return False


def limpar_credenciais_do_ambiente():

    nomes = (
        "SITE_USUARIO",
        "SITE_SENHA",
        "USUARIO",
        "SENHA"
    )

    for nome in nomes:

        os.environ.pop(
            nome,
            None
        )


# =====================================================
# LEITURA DO .ENV
# =====================================================

def carregar_env():
    """
    Carrega as credenciais diretamente do arquivo .env.

    A leitura direta evita reaproveitar credenciais antigas
    que possam ter permanecido em os.environ depois da
    exclusão ou alteração do arquivo.
    """

    if not CAMINHO_ENV.is_file():

        return {}

    try:

        dados = dotenv_values(
            dotenv_path=CAMINHO_ENV,
            encoding="utf-8"
        )

        return dict(
            dados
        )

    except Exception:

        return {}


def ler_credenciais_env():
    """
    Retorna:
        (usuario, senha)

    Variáveis principais:
        SITE_USUARIO
        SITE_SENHA

    As variáveis USUARIO e SENHA são aceitas apenas para
    compatibilidade com arquivos .env criados anteriormente.
    """

    dados = carregar_env()

    usuario = limpar_valor(
        dados.get(
            "SITE_USUARIO"
        )
        or dados.get(
            "USUARIO"
        )
    )

    senha = limpar_valor(
        dados.get(
            "SITE_SENHA"
        )
        or dados.get(
            "SENHA"
        )
    )

    if usuario:

        os.environ[
            "SITE_USUARIO"
        ] = usuario

    if senha:

        os.environ[
            "SITE_SENHA"
        ] = senha

    return usuario, senha


def credenciais_estao_configuradas():

    usuario, senha = ler_credenciais_env()

    return bool(
        usuario
        and senha
    )


# =====================================================
# GRAVAÇÃO DO .ENV
# =====================================================

def salvar_credenciais(
    usuario,
    senha
):
    """
    Grava as credenciais no .env usando os nomes originais
    utilizados pelo Nexer:

        SITE_USUARIO
        SITE_SENHA

    A gravação é atômica para evitar arquivo incompleto.
    """

    usuario = limpar_valor(
        usuario
    )

    senha = limpar_valor(
        senha
    )

    if not usuario:

        raise ValueError(
            "Usuário não informado."
        )

    if not senha:

        raise ValueError(
            "Senha não informada."
        )

    usuario_escapado = escapar_valor_env(
        usuario
    )

    senha_escapada = escapar_valor_env(
        senha
    )

    conteudo = (
        f'SITE_USUARIO="{usuario_escapado}"\n'
        f'SITE_SENHA="{senha_escapada}"\n'
    )

    caminho_temporario = (
        CAMINHO_ENV.parent
        / ".env.tmp"
    )

    caminho_temporario.write_text(
        conteudo,
        encoding="utf-8"
    )

    os.replace(
        caminho_temporario,
        CAMINHO_ENV
    )

    os.environ[
        "SITE_USUARIO"
    ] = usuario

    os.environ[
        "SITE_SENHA"
    ] = senha

    usuario_validado, senha_validada = (
        ler_credenciais_env()
    )

    if (
        usuario_validado != usuario
        or senha_validada != senha
    ):

        raise RuntimeError(
            "As credenciais foram gravadas, "
            "mas não puderam ser validadas."
        )

    return str(
        CAMINHO_ENV
    )


def salvar_env(
    usuario,
    senha
):
    """
    Mantém compatibilidade com chamadas antigas.
    """

    return salvar_credenciais(
        usuario,
        senha
    )


def remover_env():

    try:

        CAMINHO_ENV.unlink(
            missing_ok=True
        )

    except OSError as erro:

        print(
            f"[AVISO] Não foi possível remover o .env: {erro}"
        )

    limpar_credenciais_do_ambiente()


# =====================================================
# ENTRADA INTERATIVA
# =====================================================

def pedir_senha_confirmada():
    """
    Usado somente quando o Nexer é executado diretamente
    em um terminal interativo.
    """

    while True:

        senha = getpass(
            "Senha: "
        )

        confirmacao = getpass(
            "Confirme a senha: "
        )

        if senha == confirmacao:

            if not senha:

                print(
                    "A senha não pode ficar vazia.\n"
                )

                continue

            return senha

        print(
            "As senhas não coincidem. "
            "Tente novamente.\n"
        )


# =====================================================
# OBTENÇÃO DAS CREDENCIAIS
# =====================================================

def obter_credenciais():
    """
    Prioridade:

    1. Lê SITE_USUARIO e SITE_SENHA do .env.
    2. Em terminal interativo, solicita as credenciais.
    3. Em worker oculto, gera erro claro e nunca usa input().
    """

    usuario, senha = ler_credenciais_env()

    if usuario and senha:

        return usuario, senha

    if not entrada_interativa_disponivel():

        raise RuntimeError(
            "Arquivo .env não encontrado ou incompleto. "
            "Abra o dashboard do Nexer e informe as "
            "credenciais na tela de primeiro acesso. "
            f"Caminho esperado: {CAMINHO_ENV}"
        )

    print(
        "Arquivo .env não encontrado ou incompleto."
    )

    print(
        "Informe as credenciais para esta "
        "e as próximas execuções:\n"
    )

    usuario = input(
        "Usuário: "
    ).strip()

    if not usuario:

        raise ValueError(
            "Usuário não informado."
        )

    senha = pedir_senha_confirmada()

    salvar_credenciais(
        usuario,
        senha
    )

    print(
        "\n[OK] Credenciais salvas no arquivo .env.\n"
    )

    return usuario, senha


# =====================================================
# LOGIN PLAYWRIGHT
# =====================================================

async def fazer_login(
    context,
    usuario,
    senha
):
    """
    Faz o login em uma página temporária e replica o
    sessionStorage nas páginas novas do mesmo contexto.
    """

    page = await context.new_page()

    try:

        await page.goto(
            URL_LOGIN,
            wait_until="domcontentloaded",
            timeout=120000
        )

        campo_usuario = page.locator(
            '[name="cre_username"]'
        )

        campo_senha = page.locator(
            '[name="cre_password"]'
        )

        await campo_usuario.wait_for(
            state="visible",
            timeout=120000
        )

        await campo_usuario.fill(
            usuario
        )

        await campo_senha.fill(
            senha
        )

        await page.get_by_role(
            "button",
            name="Logar"
        ).click()

        try:

            await page.wait_for_function(
                "() => !window.location.href"
                ".toLowerCase().includes('login')",
                timeout=120000
            )

        except Exception:

            await page.wait_for_timeout(
                5000
            )

        print(
            f"URL após login: {page.url}"
        )

        if "login" in page.url.lower():

            raise LoginError(
                "Login não foi concluído. "
                "Verifique o usuário, a senha e "
                "a disponibilidade do sistema."
            )

        estado_sessao = await page.evaluate(
            """
            () => {
                const dados = {};

                for (
                    let indice = 0;
                    indice < sessionStorage.length;
                    indice++
                ) {
                    const chave = sessionStorage.key(indice);
                    dados[chave] = sessionStorage.getItem(chave);
                }

                return dados;
            }
            """
        )

        estado_sessao_js = json.dumps(
            estado_sessao,
            ensure_ascii=False
        )

        await context.add_init_script(
            f"""
            (() => {{
                try {{
                    const dados = {estado_sessao_js};

                    for (const chave in dados) {{
                        window.sessionStorage.setItem(
                            chave,
                            dados[chave]
                        );
                    }}
                }} catch (erro) {{
                    console.error(
                        "Falha ao restaurar sessionStorage:",
                        erro
                    );
                }}
            }})();
            """
        )

        print(
            "[OK] Login concluído e sessão compartilhada."
        )

    finally:

        if not page.is_closed():

            await page.close()


# =====================================================
# TENTATIVAS DE LOGIN
# =====================================================

async def tentar_login(
    context,
    usuario,
    senha,
    max_tentativas=3
):
    """
    No dashboard/worker oculto:

    - não tenta solicitar credenciais pelo console;
    - remove o .env inválido;
    - encerra com uma mensagem clara;
    - o próximo acesso ao dashboard exibirá novamente
      a tela de credenciais.

    Em terminal interativo:

    - permite informar novas credenciais;
    - repete até o limite configurado.
    """

    for tentativa in range(
        1,
        max_tentativas + 1
    ):

        try:

            await fazer_login(
                context,
                usuario,
                senha
            )

            return True

        except LoginError as erro:

            print(
                f"\n[ERRO] {erro}"
            )

            remover_env()

            if not entrada_interativa_disponivel():

                raise LoginError(
                    "As credenciais salvas não foram aceitas. "
                    "O arquivo .env foi removido. "
                    "Abra novamente o dashboard e informe "
                    "credenciais válidas."
                ) from erro

            if tentativa == max_tentativas:

                raise LoginError(
                    "Login falhou após "
                    f"{max_tentativas} tentativas."
                ) from erro

            print(
                f"Tentativa {tentativa} de "
                f"{max_tentativas} falhou."
            )

            print(
                "Informe novas credenciais.\n"
            )

            usuario, senha = obter_credenciais()

        except Exception as erro:

            if tentativa == max_tentativas:

                raise LoginError(
                    "Falha inesperada durante o login: "
                    f"{type(erro).__name__}: {erro}"
                ) from erro

            print(
                "[AVISO] Falha inesperada no login. "
                f"Nova tentativa será realizada: {erro}"
            )

    raise LoginError(
        "Não foi possível concluir o login."
    )