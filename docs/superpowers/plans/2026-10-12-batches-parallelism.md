# Lotes e paralelismo real — implementation plan

**Goal:** Selecionar vários fluxos, iniciar lote e acompanhar/cancelar cada fluxo enquanto execuções reais ocorrem em paralelo.

**Architecture:** Um lote agrupa execuções independentes da API existente, com snapshots próprios de versões e perfis. Um supervisor inicia processos worker isolados com capabilities distintas; reservas atômicas e revogação mantêm filas e credenciais vinculadas ao worker correto.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Delegação de implementação somente quando autorizada pelo usuário ou por instrução aplicável. Steps use checkbox (`- [ ]`) syntax for tracking.

**Tech Stack:** React/TypeScript/Vite, FastAPI, SQLAlchemy/Alembic/SQLite, SSE, Playwright/Edge e Python em Windows.

**Spec:** ../specs/2026-10-12-nexer-reusable-flows-design.md

## Global Constraints

- Credenciais entram somente na execução, em envelope efêmero separado de inputs; nunca em DB, receita, logs ou arquivos.
- HTTP é reservado a fixtures loopback; sites reais usam HTTPS e política de origens explícita.
- Cada fluxo usa processo/contexto/workspace próprio; não compartilhar Playwright síncrono entre threads.
- SGIND/IQOS mantêm gates fechados até validação real no ambiente autorizado.
- Testes sintéticos não provam compatibilidade universal. Preservar o legado e as mudanças locais existentes.
- Não fazer merge, force-push ou publicar implantação como efeito incidental destes planos.

## Review Focus

- Falha no item n de um lote: validação e binding atômicos, sem enfileirar parte inadvertidamente.
- Reenvio/duplo clique: idempotência sem criar execuções duplicadas ou aceitar segredo de outro lote.
- Conta/arquivo com mesmo nome em dois fluxos: sessão e workspace nunca cruzam.
- Cancelar um fluxo enquanto outro executa: encerrar somente processo/contexto correto.
- Processo morre após claim: estados recuperáveis, capacidade revogada e sem retry cego de ação não idempotente.

### Task 1: Lotes transacionais e snapshot por fluxo

**Files:** Create `apps/backend/app/schemas_batch.py`, `apps/backend/app/api/execution_batches.py`, `apps/backend/tests/test_execution_batches_api.py`; Modify `apps/backend/app/models.py`, `apps/backend/app/main.py`, `apps/backend/app/api/executions.py`; próxima migration Alembic disponível após perfis.

**Interfaces:** `POST /execution-batches` recebe nome, idempotency_key e items=[{automation_id, version, inputs, flags}], envelope de credenciais separado. Cria ExecutionBatch e uma Execution por fluxo; GET devolve resultados individuais; cancel solicita parada dos itens não terminais. Reusar serviço de criação de execução refatorado para não fazer commit por item.

- [ ] Testes de lote com dois fluxos, parâmetros diferentes, versão antiga inválida, rollback no binding e reenvio idempotente; observar RED.
- [ ] Separar validação/preparação da execução do commit existente; confirmar teste da API individual inalterado.
- [ ] Fixar receita/perfil/version na criação e criar lote+execuções em uma transação; revogar bindings temporários em qualquer falha.
- [ ] Testar agregações sucesso total/parcial/falha/cancelamento e cancelamento sem reabrir estado terminal.

### Task 2: Canal de capabilities para múltiplos workers

**Files:** Modify `apps/backend/app/worker_channel.py`, `apps/backend/app/execution_credentials.py`, `scripts/run_local.py`, `apps/worker/secure_main.py`; Test `apps/backend/tests/test_worker_channel.py`, `apps/worker/tests/test_launcher.py`.

**Interfaces:** Registro de worker por identidade/incarnation/capability; configurar um novo worker não revoga todos os outros. Binding e claim precisam concordar com worker autorizado; capability de A não resolve credencial de B.

- [ ] Testes de duas identidades simultâneas, revogação de uma, expiração, restart e claim de execução vinculada; observar RED.
- [ ] Generalizar mapas por worker e sessão, sem colocar capabilities em env/args/DB/logs. Bootstrap por stdin permanece.
- [ ] Garantir redistribuição de fila sem credenciais vinculadas ao worker perdido; solicitar novas credenciais quando necessária, sem desbloqueio implícito.

### Task 3: Supervisor com slots de processo

**Files:** Modify `scripts/run_local.py`, `apps/worker/main.py`; Create `apps/backend/tests/test_parallel_launcher_e2e.py` e fixture de processo correspondente; usar service/loop serial existente dentro de cada processo.

**Interfaces:** Configuração inicial 2 slots, validada entre 1 e 4, cada processo com worker_id/capability próprios. --api-only continua sem processar fila. stop_worker continua restrito à árvore criada pelo supervisor.

- [ ] Teste real com dois processos e Edge em bancos/workspaces temporários, medindo sobreposição de intervalos; observar RED.
- [ ] Iniciar slot isolado por processo com driver/DB/contexto próprios; não envolver Playwright síncrono compartilhado em ThreadPool.
- [ ] Shutdown solicita parada de todos e aguarda dentro de orçamento global; fallback Windows encerra cada árvore conhecida.
- [ ] Testar parent-loss, timeout, um processo morto e um saudável, excesso de fila e reinício. Capability perdida não é reaproveitada.

### Task 4: Preparação e acompanhamento de lote no dashboard

**Files:** Create `apps/frontend/src/pages/NewBatchPage.tsx`, `apps/frontend/src/pages/BatchDetailPage.tsx` e testes; Modify `apps/frontend/src/pages/Dashboard.tsx`, `apps/frontend/src/lib/api.ts`, `apps/frontend/src/App.tsx`; extrair formulário comum de parâmetros de NewExecutionPage sem duplicar contrato.

**Interfaces:** Seleção múltipla de fluxos; Executar lote; cards de parâmetros por fluxo; credenciais por perfil fora do cache; BatchDetail com links de execução, progresso e cancelar individual/lote.

- [ ] Testes de dois fluxos com campo company distinto, uma credencial por perfil e envelope isolado; observar RED.
- [ ] Impedir submissão antes de preparar/validar todos; mostrar itens na fila quando slots ocupados.
- [ ] Consumir SSE existente por execução e agregar no lote; reconectar com Last-Event-ID e não duplicar eventos.
- [ ] Testar cancelamento individual, sucesso parcial, falha de submissão idempotente e sessão expirada. Inspecionar desktop/mobile.

### Task 5: Aceite de isolamento e paralelismo

- [ ] Dois fluxos com cookies/contas diferentes e download de mesmo nome: provar resultados distintos em workspaces distintos.
- [ ] Cancelar fluxo A em ação bloqueada enquanto B conclui; depois cancelar um lote ativo e comprovar limpeza dos filhos.
- [ ] Verificar segredo-canário ausente em DB/receitas/eventos/arquivos e credenciais revogadas ao terminal.
- [ ] Executar suites, build, revisão e handoff. Não afirmar simultaneidade usando somente contadores RUNNING ou concurrency_limit.

## Ledger de execução — 2026-10-13

- Implementação inline no checkout autorizado; preservar diffs anteriores, sem commits/push/merge.
- Task1: modelos/migration0006/API transacional e idempotente implementados; testes batch API GREEN3, parâmetros separados, invaliditem rollback, chave conflitante e cancelamento individual/lote.
- Task2: canal multiworker com capabilities/incarnations distintas, escolhaRR e claim vinculado. Testes capabilitycruzada/revogação isolada/restart RED→GREEN; cofre original e sessões preservados. Execução QUEUED vinculada a worker OFFLINE REDrecovered0 → GREENFAILED sem redistribuir credencial.
- Task3: supervisor --workers1..4/default2, bootstrap privado por stdin, monitor de morte revoga somente identidade correspondente, shutdown orçamento global. Unitlauncher GREEN4. Contenção Windows real GREEN4(um worker); não extrapolar todos os cenários para pool.
- Task4: seleção de cartões/dashboard, NewBatchPage campos/tipos/regras por fluxo e um acesso por perfil fora dos caches, preparação bloqueada se catálogos indisponíveis; BatchDetail SSE/status/cancelamento. Frontend testes parâmetros independentes, credencial compartilhada, peer terminal e busca preservando seleção GREEN. SSE replayduplicado RED2 → GREEN1, limpeza/buffer500.
- Final: fixed loading de catálogo travado após editar durante request — regressão REDbotãoCarregando permanente → GREENrecarregar disponível; invalidação de resposta obsoleta preservada.
- Task5: teste real dois processos + Edge em DB/workspaces temporários GREEN. Downloads ficam bloqueados simultaneamente no servidor, provando sobreposição; cancelarA e liberar resultaA CANCELLED/B SUCCEEDED. Segundo lote com duas contas e same.txt resultaSUCCEEDED, bytes específicos e diretórios diferentes. Canário ausente emdumpDB. Shutdown concluído.
- Prévia visual: Desktop1440/celular390, dashboard/lote/Studio/login inspecionados; logo carregado, busca/seleção/navigation verificadas, sem overflow oupageerrors.
- Ruling: manter seletores/renderização compartilhados via RecipeField, sem refatorar toda página de execução antiga nesta rodada — limita regressões da UI existente; custo se errado: parsing pode divergir, coberto por validação de tipos API/runtime e testes por página. Extração completa de parsing fica para simplificação posterior.
- Ruling: --workers não muda concurrency interna — um driver/contexto/loop serial por processo; custo se errado: overhead de memória, em troca de isolamento. Evidência mede sobreposição real.
- Ruling: preview de design em servidor local separado com dados sintéticos/POST bloqueado — usuário acompanha aparência sem migrar banco/iniciar fila real; custo se errado: resultados da prévia não representam validação de execução real.
- Suitefinal: backend107 OK(12skips), worker32 OK(1skip), runtime107 OK(10skips), frontend38 OK, buildGREEN. Caso worker perdido usava PID10 arbitrário; fixture agora declara processo morto e não depende de reuse Windows.
- Critérios ampliados de parent-loss/restart de dois workers, excesso de fila e cancelamento de lote inteiro ativo ainda devem ser expandidos. Gate corporativo continua fechado. Handoff CONTINUAR_NEXER_2026-10-13.md registra limites sem declarar Etapa1 encerrada.
