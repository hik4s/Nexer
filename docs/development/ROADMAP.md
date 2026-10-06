# RelatPy — Roadmap de Implementação

## Etapa 1

| Bloco | Estado | Observação |
|---|---|---|
| 1 Governança | Em andamento | baseline criado; PR de governança existente |
| 2 Documentação funcional | Em andamento | Master Plan aprovado; documentação operacional em consolidação |
| 3 Preparação ambiente | Em andamento | CI Windows funcional |
| 4 Estrutura repositório | Parcial | `apps/` criado; recorder ainda inicial |
| 5 Design System | Pendente | começa após base frontend |
| 6 Frontend base | Pendente | React/Vite ainda não implementado |
| 7 Backend base | Parcial/avançado | FastAPI + configuração + erros + health/version/metrics |
| 8 Banco/persistência | Parcial/avançado | SQLAlchemy + Alembic + schema inicial + registry do Worker |
| 9 API inicial | Parcial/avançado | automations, executions, cancelamento e SSE |
| 10 Eventos tempo real | Parcial/avançado | persistência + SSE + Last-Event-ID |
| 11 Worker inicial | Em implementação | lifecycle + claim atômico já testados |
| 12 Runtime mínimo | Próximo | receita v1 + ações universais |
| 13 Autenticação/navegador | Pendente | Browser Manager + Edge |
| 14 Automação piloto | Pendente | será feita depois do Runtime |
| 15 Testes/gate | Contínuo | não fechar Etapa 1 antes dos critérios de aceite |

## Etapa 2

Bloqueada até a demonstração completa do marco oficial da Etapa 1.

## Etapa 3

Bloqueada até a aprovação da Etapa 2.

## Regra

Nenhum avanço de etapa é permitido com falha bloqueante, segredo versionado, documentação crítica desatualizada ou fluxo anterior não demonstrável.
