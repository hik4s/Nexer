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

## Latest dependency/auth verification - 2026-10-08

- Local `.venv` created and all declared Python dependencies installed successfully; `pip check` passed.
- Frontend dependencies installed; lockfile generated; npm audit: 0 high-severity vulnerabilities found.
- Backend 31/31, Worker 11/11, Runtime 39/39, legacy smoke 4/4 passed.
- Real Edge Runtime pilot + Worker E2E: 2/2 passed.
- Authentication foundation now restores/persists Playwright session state through OS keyring and supports controlled form renewal without exposing secrets.
- Python `pip-audit` was attempted but did not complete; keep security audit open until CI/local audit finishes.

## CI blocker found and fixed - 2026-10-08

- CI run 281 exposed a pre-existing syntax error in the legacy `splash.py` (truncated file).
- The missing splash/bootstrap tail was restored on the feature branch.
- Exact CI-style syntax check now passes for 98 Python files; legacy smoke remains 4/4.

## Authentication diagnostics - 2026-10-08

Added non-sensitive authentication configuration counters to `/diagnostics` and surfaced them in the frontend. Backend full suite is 32/32; runtime 43/43, worker 11/11, legacy smoke 4/4; frontend targeted diagnostic test 1/1.

## Destination CRUD - 2026-10-08

- Backend Destinations now supports create/list/get/update/delete.
- Update validates duplicate codes and required path references.
- Frontend Destinations now supports create/edit/enable-disable/delete with confirmation.
- Frontend API helper now handles HTTP 204 responses correctly.
- Destination backend tests: 6/6 passed.
- Frontend full suite: 8 files / 14 tests passed.
- Frontend typecheck: OK.
- Frontend production build: OK.
- Integrated verification: backend 35/35, worker 11/11 (1 real Edge test skipped without opt-in), runtime 43/43 (1 real Edge test skipped without opt-in).
- GitHub Actions run 289 for commit a1979b7 is green, including Python dependency security audit and frontend dependency audit.
- Local pip-audit did not complete on this Windows executor; do not claim the local audit green.

## Latest continuation - 2026-10-08

- Remote branch confirmed: `feat/etapa1-foundation`.
- Current remote HEAD before the Studio changes: `e76618a93d7566befc089ef63680cc2b1d1b89e2`.
- GitHub Actions run 293 (`37821114007`) is **green** for that commit; Python and frontend jobs passed, including dependency audits.
- Added Studio foundation: create automation → edit declarative JSON recipe → save version → test → publish.
- Added `/studio` frontend route/navigation and API helpers.
- Studio regression: 1/1; frontend full suite: 9 files / 15 tests; typecheck/build: OK.
- Next recommended work remains resilience/recovery and then controlled real-automation migration, while keeping the formal E1 gate explicit.
