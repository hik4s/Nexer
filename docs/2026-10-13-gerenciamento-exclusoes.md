# Nexer — gerenciamento de exclusões (13/10/2026)

## Contrato seguro implementado

- `DELETE /automations/{id}`: exclui fisicamente fluxo sem histórico nem rotina; se houver execuções encerradas ou rotinas que o referenciem, muda status para `ARCHIVED` e preserva receitas/histórico. Bloqueia (`409 AUTOMATION_IN_USE`) enquanto qualquer execução do fluxo estiver pendente ou ativa. Resposta 200 com `{"archived": true|false}`.
- `DELETE /executions/{id}`: exige status terminal (SUCCEEDED, PARTIAL, FAILED, CANCELLED), rejeita execuções pertencentes a lote e apaga somente registros (itens, eventos, checkpoints, metadados de arquivos). Não toca no filesystem; nenhum arquivo físico é removido. 204.
- `DELETE /execution-batches/{id}`: exige sessão proprietária e que TODOS os jobs do lote estejam terminados. Apaga registros de todos os jobs e lote em uma transação. Arquivos físicos preservados. 204.
- `DELETE /access-groups/{id}`: bloqueia grupos associados a perfis; devem ser desvinculados antes. 204.
- `DELETE /routines/{id}` e exclusão de perfil já existiam; as telas receberam confirmação/controle.
- `ExecutionRead.batch_id` incluído na API para que a interface não proponha excluir isoladamente uma execução pertencente a um lote.
- Nenhuma migração de banco nova foi necessária.

## Interface

- Dashboard (Meus fluxos): Excluir fluxo, Excluir rotina, com confirmação e atualização da lista.
- Catálogo de automações: Excluir fluxo; itens arquivados ficam identificados.
- Histórico de execuções: Excluir execução finalizada ou lote finalizado (com confirmação), bloqueado para itens ativos.
- Detalhes de execução e lote: botões correspondentes após encerramento; retorno para Histórico.
- Acessos: excluir grupo de acesso com confirmação; perfis associados precisam ser desvinculados.
- As confirmações indicam a preservação dos arquivos físicos e o arquivamento de fluxos vinculados.

## Testes e limitações

- `apps/backend/tests/test_deletion_api.py`: cenários de FK, arquivos preservados, histórico, lote, grupo e bloqueio em andamento.
- `apps/frontend/src/pages/ExecutionsPage.delete.test.tsx`, `Dashboard.reports.test.tsx`: confirmação, limitações de estado e atualização.
- Frontend: 69 testes em 20 arquivos e build TypeScript/Vite passaram nesta rodada.
- Backend segmentado: 17 testes passaram; suíte completa: 143 testes, 13 ignorados, zero falhas (PYTHONPATH inclui apps/worker).
- Não foi executada gravação, download corporativo, worker real nem migração do banco de produção.
- O diretório de trabalho é uma **cópia exportada sem .git**: não foram feitos commit, push ou merge. Preservar alterações e reintroduzi-las numa cópia Git legítima após auditoria.
