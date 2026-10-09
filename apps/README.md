# Nova arquitetura do Nexer

Esta árvore pertence à nova versão do Nexer e é desenvolvida de forma isolada do aplicativo legado existente na raiz.

## Regra de isolamento
- O legado permanece preservado e operacional.
- A nova arquitetura evolui por branches e microtarefas.
- Nenhum arquivo legado é substituído como parte da fundação.
- A integração com o legado só ocorrerá mediante decisão explícita e validação.

## Direção
- frontend: React + TypeScript + Vite
- backend: FastAPI
- worker/runtime: Python
- persistência: SQLite
- eventos: SSE
- automação: Playwright + Edge no runtime Windows

## Autenticação local do backend

O backend valida as credenciais no servidor e emite um cookie de sessão `HttpOnly`, `SameSite=Strict`, com expiração. As rotas de negócio ficam bloqueadas quando a autenticação não está configurada; `/`, `/health`, `/version`, `/metrics` e `/auth/*` são as exceções públicas.

1. Na raiz do repositório, execute `python scripts/setup_auth.py`.
2. Informe um usuário e uma senha com pelo menos 12 caracteres no prompt seguro. A senha não é exibida nem gravada em texto claro.
3. O script grava `NEXER_AUTH_USERNAME` e um hash PBKDF2 em `.env`, arquivo ignorado pelo Git.
4. Reinicie o backend para carregar a configuração e entre pela tela de login.

As sessões são mantidas apenas na memória do backend e são invalidadas quando ele reinicia. O tempo padrão de sessão é de 8 horas. Em HTTPS, configure `NEXER_AUTH_COOKIE_SECURE=true`. Nunca execute o backend com `NEXER_ENVIRONMENT=test` fora dos testes: esse modo desativa a barreira de autenticação para permitir os testes de integração.
