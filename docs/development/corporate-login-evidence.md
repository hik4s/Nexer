# Evidências do formulário de login corporativo

Fonte: URLs e trechos HTML fornecidos pelo usuário em 09/10/2026.
Os seletores abaixo foram derivados do HTML; ainda não foram exercitados em login real nesta etapa. Não contêm credenciais.

| Sistema | URL de login | Formulário | Usuário | Senha | Enviar |
| --- | --- | --- | --- | --- | --- |
| IQOS | https://indicadoresenergisaess.scl.corp/iqos/#/login | form[name="form"] | form[name="form"] input[name="cre_username"] | form[name="form"] input[name="cre_password"][type="password"] | form[name="form"] button[type="submit"] |
| SGIND | https://indicadoresenergisaess.scl.corp/sgind/#/login | form#idFormLogin | form#idFormLogin input[name="cre_username"] | form#idFormLogin input[name="cre_password"][type="password"] | form#idFormLogin button[type="submit"] |

Ambos exibem o rótulo Logar no botão real. Ambos os campos de senha têm minlength="6".
IQOS: versão informada no trecho 3.4.0.2. SGIND: versão informada 2.4.0.2.
Atributos Angular _ngcontent, pc4/pc5/pc6 e classes ng-dirty/ng-valid/ng-touched não são seletores estáveis e não devem ser usados.

## Evidência após login — 09/10/2026
Usuário forneceu URLs SGIND https://indicadoresenergisaess.scl.corp/sgind/#/home e IQOS https://indicadoresenergisaess.scl.corp/iqos/#/home após login manual, e trechos HTML com app-home-page e fundo home-bg.
Indicador combinado: URL home exata do sistema, app-home-page visível e formulário de login ausente. A classe ng-valid e atributos Angular temporários não comprovam autenticação.
Probe real com Edge headless, TLS padrão e contextos NOVOS sem estado/cookies: navegar diretamente à home de SGIND e IQOS terminou em /#/login do próprio sistema, com input cre_username visível e app-home-page ausente. Processo exit0. Não foram preenchidas ou enviadas credenciais; nenhuma sessão existente foi usada.
corporate_auth.py define URLs/seletores imutáveis e matches_authenticated_home para avaliar a combinação. O matcher não faz login nem verifica sessão no servidor por si só; deverá receber observações da página real no fluxo integrado.
validate_corporate_url permite cada sistema somente no próprio prefixo /sgind/ ou /iqos/, HTTPS/host exatos, porta443/padrão, sem userinfo, whitespace, backslash ou segmentos de traversal. Caminhos percent-encoded são rejeitados nesta política restrita.
A política de execução/require_validated_adapter continua bloqueada enquanto login/contexto/lifecycle do worker não estão integrados. Não solicitar senha, token ou cookie no chat nem salvar estado autenticado.
Pendências: fluxo automático de credenciais, interceptação de destinos externos, restrição de scripts/receitas no contexto autenticado, revogação durante ações, teste de login real submetido pelo usuário na dashboard. Mensagem de senha incorreta ainda não inspecionada; usar erro constante/timeouts sem copiar textos do navegador.
