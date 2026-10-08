# RelatPy — Handoff

Este arquivo é o ponto de retomada quando a conversa atual expirar.

## Bootstrap

Continue o desenvolvimento do RelatPy no repositório `hik4s/RelatPy`. Leia `MASTER_PLAN.md`, `docs/development/CURRENT_STATE.md`, `HANDOFF.md` e consulte GitHub/Linear/CI. Trabalhe exclusivamente na branch isolada da nova arquitetura e não altere o legado em `master`. Use TDD para código funcional, execute os testes e só registre avanço após verificação real.

## Estado atual

Branch: `feat/etapa1-foundation`

A Etapa 1 já possui:
- FastAPI + SQLite + Alembic;
- automations + versionamento/teste/publicação;
- executions + cancelamento + snapshot da versão;
- inputs parametrizados;
- SSE persistido;
- Worker com lifecycle, heartbeat, claim e processor;
- Runtime declarativo v1 + ActionRegistry;
- Edge via Playwright + Browser Manager;
- download/validação de arquivo;
- credenciais via keyring/credential_ref;
- AuthenticationGuard com tentativa única + verificação antes dos passos;
- frontend React/TypeScript com Dashboard, Automações, Execuções, Nova execução, Diagnóstico e Destinos;
- piloto real Worker → Edge → download → persistência no Windows;
- teste de Gate API → Worker → Runtime;
- scripts de continuidade e verificação.

## Evidência

Últimas validações locais:
- backend: 29 testes OK;
- worker: 9 testes OK (E2E real opt-in);
- runtime: 30 testes OK (E2E real opt-in);
- frontend: 9 testes OK + typecheck + build;
- cancelamento cooperativo: OK;
- política de segredo: OK;
- Edge real: OK.

## Trabalho em andamento

1. validar CI verde da branch isolada após correções do filtro Windows e harness frontend;
2. concluir integração de autenticação real, incluindo diagnóstico e restauração de sessão autorizada;
3. frontend de destinos;
4. manutenção/criação de receitas pelo Studio;
5. watchdog, retry, checkpoints e recovery;
6. migração controlada de automação real;
7. gate formal da Etapa 1.

## Regras

- `master` é legado e não deve ser substituído;
- nenhuma credencial/token em código, logs, fixtures ou receitas;
- não considerar código escrito como concluído sem teste e evidência;
- preferir desenvolvimento remoto; usar Windows/Edge real apenas quando a validação do comportamento local exigir;
- ao final de um bloco relevante, atualizar `CURRENT_STATE.md` e este arquivo.

## Latest verification - 2026-10-08

- Backend: 31/31 tests OK after the verification harness PYTHONPATH fix.
- Worker: 9 tests OK; real Edge E2E remains opt-in.
- Runtime: 30 tests OK; real Edge E2E remains opt-in.
- Frontend regression: 3/3 targeted tests OK.
- Frontend typecheck and production build: OK.
- Commit pushed: `328624db3c17d809584b2ade0e5beeaa9dc7eee9`.
- GitHub Actions run 277 is still in progress.
