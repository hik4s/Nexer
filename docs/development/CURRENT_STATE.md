# RelatPy — Estado Atual

> Fonte operacional para retomada do desenvolvimento. Não substitui o Master Plan.

## Snapshot

- Produto: RelatPy
- Trilha: Etapa 1 — Fundação, documentação e núcleo executável
- Branch de desenvolvimento: `feat/etapa1-foundation`
- Legado: permanece em `master`; não alterar durante a migração
- Ambiente operacional final: Windows local
- Arquitetura alvo: React + TypeScript + Vite → FastAPI → SQLite + SSE → Worker → Runtime → Playwright/Edge

## Concluído nesta branch

### Base e governança
- Scaffold isolado em `apps/`
- documentação de arquitetura inicial
- pipeline CI Windows
- testes smoke
- baseline de governança

### Backend
- FastAPI mínimo
- configuração tipada
- erros padronizados
- CORS de desenvolvimento
- health/version/metrics
- SQLAlchemy + SQLite
- Alembic e migration inicial
- automations API
- executions API
- SSE persistido com `Last-Event-ID`
- entidades de execução, eventos, artefatos e checkpoints
- migration `0002_worker_registry`

### Worker
- pacote separado em `apps/worker`
- registro ONLINE/OFFLINE
- heartbeat
- limite de concorrência
- claim atômico de execução
- proteção contra dupla coleta
- metadados `worker_id` + `claimed_at`
- evento persistido de claim

## Evidência de testes

- Worker suite: 3 testes, todos OK no Windows
- CI associado ao commit anterior da branch: sucesso confirmado
- Toda conclusão futura deve repetir a verificação completa antes de ser registrada aqui

## Próximo bloco obrigatório

1. estabilizar Worker como processo executável;
2. definir schema de receita v1;
3. validar receita e resolver variáveis;
4. criar ActionRegistry;
5. implementar ações mínimas do Runtime;
6. integrar Worker → Runtime;
7. criar primeira receita manual;
8. criar diagnóstico básico;
9. fechar frontend React inicial;
10. executar piloto de ponta a ponta.

## Regras de continuidade

- nunca sobrescrever `master`/legado;
- aplicar TDD em funcionalidade nova;
- testar no Windows quando houver comportamento específico do sistema;
- registrar evidência antes de marcar microtarefa como concluída;
- atualizar este arquivo e `HANDOFF.md` ao fechar um bloco relevante.
