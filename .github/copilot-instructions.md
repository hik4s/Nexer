# Nexer — GitHub Copilot Instructions

## Objetivo

Manter o desenvolvimento da nova arquitetura do Nexer isolado do aplicativo legado e sempre orientado por TDD, segurança e verificação real.

## Arquitetura

- Legado funcional permanece em `master`; nunca substituir ou reescrever `master` como parte da nova arquitetura.
- Desenvolvimento atual: `feat/etapa1-foundation`.
- Frontend: React + TypeScript + Vite em `apps/frontend`.
- Backend: FastAPI + SQLAlchemy + Alembic em `apps/backend`.
- Worker: processo Python separado em `apps/worker`.
- Runtime: Playwright + Edge em `apps/runtime`.
- Persistência: SQLite.
- Eventos: SSE persistido.
- Operação final: Windows local; cloud é somente apoio de desenvolvimento/CI.

## Regras de desenvolvimento

1. Para funcionalidade nova, siga TDD: Red → Green → Refactor.
2. Escreva ou atualize o teste antes da implementação quando o comportamento for novo.
3. Faça alterações pequenas e mantenha cada mudança coerente com uma microtarefa.
4. Não introduza dependências sem necessidade.
5. Não coloque credenciais, tokens, cookies, caminhos corporativos ou dados reais em código, fixtures, logs ou receitas.
6. Segredos de automação devem usar `credential_ref` e o armazenamento seguro do sistema.
7. Mantenha validações de path traversal, subprocessos e importação dinâmica sob controle explícito.
8. Preserve compatibilidade com Windows quando o comportamento depender do sistema operacional.

## Verificação obrigatória

Antes de considerar uma alteração concluída:

- Execute os testes afetados.
- Execute o conjunto de testes do componente alterado.
- Para alterações abrangentes, execute `scripts/verify.ps1 -SkipAudit`.
- Para mudanças de dependências/segurança, execute também as auditorias configuradas.
- Execute typecheck e build do frontend quando o frontend for alterado.
- Inspecione a saída dos comandos; não declare sucesso apenas porque o comando foi iniciado.
- Não marque uma tarefa como concluída sem evidência recente.

## CI e Git

- Toda alteração deve permanecer na branch de desenvolvimento até revisão e Gate formal.
- Não faça merge em `master` sem decisão explícita.
- Mantenha mensagens de commit pequenas e descritivas, preferencialmente no formato `tipo(escopo): descrição`.
- Antes de abrir/atualizar PR, confirme testes locais e CI.
- Use GitHub como fonte de verdade para commits, PRs e CI.

## Continuidade

Antes de iniciar uma tarefa relevante, leia:

- `MASTER_PLAN.md`
- `docs/development/CURRENT_STATE.md`
- `HANDOFF.md`
- `docs/development/ROADMAP.md`
- `docs/development/DECISIONS.md`

Ao concluir um bloco relevante, atualize o estado operacional e registre evidência.

## Definition of Done

Uma mudança só está concluída quando implementação, testes, tratamento de erros, logs/observabilidade, segurança, documentação necessária e evidência de validação estiverem coerentes com o Master Plan.
