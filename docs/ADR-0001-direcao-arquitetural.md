# ADR-0001 — Direção arquitetural

## Status
Aceito — 2026-10-06

## Contexto
O Master Plan define uma evolução do RelatPy para uma aplicação local Windows com frontend React/TypeScript, backend FastAPI, worker separado, runtime de automações, SQLite e eventos em tempo real.

O repositório atual contém a aplicação legada funcional e não deve ser substituído em um único passo.

## Decisão
A migração será incremental. A aplicação atual permanece preservada enquanto a nova arquitetura é introduzida por etapas, com testes e gates de aceite.

O runtime final permanece local no Windows. O ambiente cloud de desenvolvimento/teste não substitui a validação específica do Windows/Edge.

## Consequências
- Mudanças grandes serão divididas em microtarefas.
- Cada mudança relevante passa pelo CI.
- A compatibilidade do legado será tratada explicitamente durante a migração.
- Segurança, logs e documentação fazem parte do Definition of Done.
