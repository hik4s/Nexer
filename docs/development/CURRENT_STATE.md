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
