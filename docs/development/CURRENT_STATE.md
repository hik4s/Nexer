# RelatPy — Estado Atual

> Fonte operacional para retomada do desenvolvimento. Não substitui o Master Plan.

## Snapshot

- Produto: RelatPy
- Trilha: Etapa 1 — Fundação, documentação e núcleo executável
- Branch de desenvolvimento: `feat/etapa1-foundation`
- Legado: permanece em `master`; não alterar durante a migração
- Ambiente operacional final: Windows local
- Arquitetura alvo: React + TypeScript + Vite → FastAPI → SQLite + SSE → Worker → Runtime → Playwright/Edge

## Implementado

### Governança e continuidade
- baseline de governança
- `CURRENT_STATE.md`, `HANDOFF.md`, `ROADMAP.md`, `DECISIONS.md`
- `scripts/handoff.ps1`
- `scripts/verify.ps1`
- desenvolvimento isolado do legado

### Backend
- FastAPI mínimo
- health, version, metrics e diagnostics
- erros padronizados
- CORS de desenvolvimento
- SQLAlchemy + SQLite + FK
- Alembic migrations `0001`, `0002`, `0003`
- automations API
- automation versions: criar/testar/publicar
- executions API: criar/listar/consultar/cancelar
- snapshot da versão publicada em `execution_automations`
- inputs parametrizados persistidos
- SSE persistido com `Last-Event-ID`
- destinations API inicial + tela frontend de Destinos
- política de segredo: apenas `credential_ref` para variáveis secretas

### Worker
- registro ONLINE/OFFLINE
- heartbeat
- limite de concorrência
- claim atômico com SQLite
- processor de execução
- integração Worker → Runtime
- loop contínuo com shutdown controlado
- cancelamento cooperativo
- integração com Browser Manager

### Runtime
- schema de receita v1
- resolvedor de variáveis
- variáveis secretas via OS credential store/keyring
- ActionRegistry
- navigate/click/fill/select/press/wait_for/wait_for_any/switch_tab/download/validate_file
- checkpoints e eventos
- dry run
- Browser Manager para Edge
- bloqueio de path traversal em workspace
- AuthenticationGuard com tentativa única
- verificação de autenticação antes dos passos
- receita de piloto reproduzível

### Frontend
- Vite + TypeScript + React
- React Query
- React Router
- Dashboard
- catálogo de Automações
- Histórico de Execuções
- detalhe de Execução com SSE
- Nova execução
- Diagnóstico
- typecheck e build
- layout responsivo inicial

## Evidência local atual

- Backend: 29/29 testes OK
- Worker: 9/9 testes OK; E2E real com Edge é opt-in
- Runtime: 30/30 testes OK; E2E real com Edge é opt-in
- Frontend: 9/9 testes OK + typecheck + build
- Edge real: piloto Runtime OK e fluxo Worker → Edge → download → persistência OK
- CI: corrigindo filtro de sintaxe Windows; último run observado ainda estava processando a versão anterior

## Próximos microtasks

1. fechar CI verde para a branch isolada após as últimas correções do harness;
2. integrar AuthenticationGuard ao fluxo de autenticação real;
3. persistir/restaurar estado de sessão autorizado quando necessário;
4. criar diagnóstico de autenticação;
5. criar gestão de destinos no frontend;
6. criar API/frontend para criação e manutenção de receitas;
7. iniciar RelatPy Studio com editor declarativo;
8. ampliar watchdog, retry e checkpoints;
9. migrar uma automação real dos relatórios atuais, somente após piloto sintético estável;
10. preparar o gate formal da Etapa 1.

## Regras de continuidade

- nunca sobrescrever `master`/legado;
- TDD para funcionalidade nova;
- validação Windows para comportamento específico do sistema;
- evidência real antes de marcar microtarefa;
- nenhuma credencial, token ou dado sensível em logs, fixtures ou receitas;
- a conversa é interface; o repositório/Linear são a memória operacional.

## Latest verification - 2026-10-08

- Windows verification ran on `feat/etapa1-foundation` at `87fefaa` before the local fixes.
- Backend: 31/31 tests OK after fixing `scripts/verify.ps1` PYTHONPATH for the integrated Gate test.
- Worker: 9 tests OK (1 E2E real Edge test skipped unless opt-in).
- Runtime: 30 tests OK (1 E2E real Edge test skipped unless opt-in).
- Frontend targeted regression: 3/3 tests OK after wrapping React Query mutation functions.
- Frontend typecheck: OK.
- Frontend production build: OK.
- Fix committed and pushed as `328624db3c17d809584b2ade0e5beeaa9dc7eee9`.
- GitHub Actions run 277 is currently in progress; do not treat CI as green until it finishes.
- Local clone used for validation: `C:\Users\kis\Downloads\RelatPy-Next-Git`.

## Latest dependency/auth verification - 2026-10-08

- Created local `.venv` (ignored by Git) with Python 3.12.
- Installed legacy `Requisitos.txt`, backend and runtime dependencies; `pip check` passed.
- Installed frontend dependencies with `npm install`; `package-lock.json` generated and `node_modules/` is now ignored.
- Frontend: 7 test files / 12 tests passed; typecheck passed; production build passed; `npm audit --audit-level=high` reported 0 vulnerabilities.
- Backend: 31/31 tests passed.
- Worker: 11 tests passed; real Edge E2E remains opt-in in the full suite.
- Runtime: 39 tests passed; real Edge E2E remains opt-in in the full suite.
- Legacy smoke: 4/4 passed.
- Real Edge E2E: Runtime pilot + Worker chain 2/2 passed in 11.3s.
- Authentication foundation completed: OS keyring session state, reusable session restoration, generic form renewal, auth guard integration in Worker/Runtime, and session persistence after successful execution.
- Security property: session/credential values are not written to SQLite/logs/error messages.
- `pip-audit` was started but did not finish within the Windows executor window; do not treat Python dependency audit as green yet.

## CI blocker found and fixed - 2026-10-08

- GitHub Actions run 281 reached Python syntax validation and exposed a pre-existing truncated `splash.py` file.
- Local reproduction matched CI: `SyntaxError: '(' was never closed` at `splash.py:194`.
- Restored the missing splash label/bootstrap tail without changing the new architecture.
- Exact CI-style syntax validation now passes for 98 Python files.
- Legacy smoke tests: 4/4 passed.

## Authentication diagnostics - 2026-10-08

- Extended `/diagnostics` with non-sensitive authentication configuration counts.
- Reports the number of recipe versions with authentication configured and the number with form renewal configured.
- Frontend Diagnostics page now displays those counters.
- Backend diagnostics tests: 32/32 passed in the full backend suite.
- Frontend diagnostics regression: 1/1 passed.
- Legacy splash syntax is valid on the current feature branch; CI run 281 failure was from the older pull-request merge result before the splash fix.

## Destination CRUD - 2026-10-08

- Destinations API now exposes create/list/get/update/delete.
- Update enforces unique code and non-blank path reference.
- Frontend Destinations page supports create, edit, active/inactive state, and delete confirmation.
- HTTP client handles 204 No Content responses.
- Destination backend tests: 6/6 passed.
- Frontend full suite: 8 files / 14 tests passed.
- Frontend typecheck: OK.
- Frontend production build: OK.
- Integrated verification: backend 35/35; worker 11/11 with real Edge E2E skipped unless opt-in; runtime 43/43 with real Edge E2E skipped unless opt-in.
- GitHub Actions run 289 for commit a1979b7 completed successfully, including dependency security audit.
- Local pip-audit execution was not completed; do not claim local Python audit green.

## Studio foundation - 2026-10-08

- Added `apps/frontend/src/pages/StudioPage.tsx` and its TDD regression.
- Studio now supports creating an automation, editing a declarative recipe as JSON, saving a version, testing the version and publishing it.
- Added frontend API helpers for automation creation and automation version lifecycle.
- Added `/studio` route and main navigation entry.
- Studio test: 1/1 passed.
- Frontend full suite after the change: 9 files / 15 tests passed.
- Frontend typecheck: OK.
- Frontend production build: OK.

## Current CI evidence - 2026-10-08

- GitHub Actions `RelatPy CI` run 293 (`37821114007`) for commit `e76618a93d7566befc089ef63680cc2b1d1b89e2` completed successfully.
- Python and frontend jobs completed successfully, including Python dependency security audit and frontend dependency audit.

## Final evidence for Studio block - 2026-10-08

- Studio commit: `1d5bd08c6357e202865095f1936cbd1ec69aa658`.
- Local `scripts/verify.ps1 -SkipAudit`: passed; backend 35/35, worker 11/11 with 1 opt-in Edge E2E skipped, runtime 43/43 with 1 opt-in Edge E2E skipped, frontend 9 files / 15 tests, typecheck and build passed.
- Local full audit mode was stopped because the Windows `pip-audit` step remained blocked; this is a local-executor limitation, not a project failure.
- GitHub Actions run 295 (`37822119458`) for the Studio commit completed successfully, including Python dependency security audit and frontend dependency audit.
- Working tree was clean and local HEAD matched `origin/feat/etapa1-foundation` at `1d5bd08c6357e202865095f1936cbd1ec69aa658` before this documentation-only update.

## Resiliência — retry por passo - 2026-10-08

- Added explicit per-step retry policy to Runtime v1.
- Recipe steps may define `retry.max_attempts` (1-5) and `retry.backoff_ms` (0-60000).
- Default remains one attempt, preserving existing behavior when `retry` is absent.
- Runtime emits `step.retrying` before a new attempt.
- Cancellation is checked before retry backoff and returns `CANCELLED` instead of continuing.
- Retry count is bounded and validated; invalid limits are rejected by recipe validation.
- Runtime runner tests: 3/3; recipe validation tests: 6/6; full runtime suite: 46/46 with 1 opt-in Edge E2E skipped.
- Integrated local verification without blocking Windows pip-audit: backend 35/35, worker 11/11 with 1 opt-in Edge E2E skipped, runtime 46/46 with 1 opt-in Edge E2E skipped, frontend 9 files / 15 tests, typecheck/build OK.
- This microblock intentionally does not implement automatic whole-execution retry or crash recovery; those remain the next resilience increment to avoid unsafe duplicate side effects.
