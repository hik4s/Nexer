# Segurança

## Reporte
Não publique credenciais, tokens, cookies, dados de usuários ou evidências sensíveis em issues, PRs ou logs.

Para vulnerabilidades, preserve o mínimo necessário para reproduzir o problema e evite divulgação pública antes da correção.

## Regras do projeto
- Segredos não entram no repositório.
- Logs não devem expor credenciais.
- Caminhos de arquivos devem ser validados.
- Processos externos devem evitar shell arbitrário.
- Receitas de automação são dados não confiáveis e devem ser validadas.
- Dependências devem passar por auditoria no CI.
