# Query Outcomes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Executar uma consulta uma única vez e reconhecer dados atuais, ausência de dados ou erro por correlação verificável.

**Architecture:** Uma ação `query` reúne baseline, clique, confirmação e classificação. Validação pura e execução Playwright ficam separadas; worker e frontend reutilizam status e mensagens existentes. O gravador conserva o clique original e a revisão permite convertê-lo explicitamente.

**Tech Stack:** Python/unittest, Playwright/Edge, FastAPI, React/TypeScript, Vitest.

**Spec:** `docs/superpowers/specs/2026-10-14-query-outcomes-design.md` (aprovada pelo “continue” após sua apresentação).

## Global Constraints

- Base de planejamento: `3fb7062`; worktree `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`. Conferir status antes de editar; preservar alterações novas de terceiros.
- Método B, receita declarativa, inteligência local, sem IA externa obrigatória e sem novas dependências.
- Prazo total de 1000 a 900000 ms, padrão 180000; polling de até 100 ms e operações limitadas a 250 ms pelo prazo restante.
- Seletores até 2048 caracteres, até 16 frames; somente CSS DOM e atributos `data-query-id`/`data-request-id`.
- Identidade ASCII `[A-Za-z0-9_.-]{1,256}`, efêmera; nunca persistir identidade, texto, HTML, parâmetros ou exceção original.
- Clique esquerdo único; `max_attempts: 1`; sem reenvio automático, ramificação, retomada após restart ou migração de banco.
- `data` segue; `empty` interrompe com `QUERY_NO_DATA` e status existente `FAILED`; `error` interrompe com `QUERY_SITE_ERROR`.
- Mensagem de vazio: “Consulta concluída sem dados; etapas seguintes não executadas.”
- Nenhuma execução corporativa, mudança de instalação, banco real, executável, gates ou histórico Git. Edge sintético não valida SGIND/IQOS.

## Review Focus

1. Seletor parametrizado resolve para vazio, inválido ou longo: rejeitar antes do efeito (tarefa 2).
2. ID da confirmação muda novamente enquanto o resultado chega: interromper, nunca aceitar a consulta substituta (tarefa 2).
3. Frame navega mantendo o mesmo seletor: rejeitar novo documento, mesmo se os IDs coincidirem (tarefa 2).
4. Edição de um item limpa indevidamente o estado pendente de outro: avanço permanece bloqueado (tarefa 4).
5. Conversão de clique com opções/retry incompatíveis ou usado por download: rejeitar sem mutar a receita (tarefa 4).

## Preparação e comandos

Executar no worktree acima, sem criar outro checkout. Na execução, ler a skill de worktrees e confirmar que este já é um worktree adequado. Nenhuma instalação é necessária se as dependências existentes continuarem disponíveis.

```powershell
$taskPython='C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe'
$env:PYTHONPATH="$PWD/apps/runtime;$PWD/apps/runtime/tests;$PWD/apps/recorder;$PWD/apps/backend;$PWD/apps/backend/tests;$PWD/apps/worker"
$env:NEXER_RUN_RECORDER_E2E='1'
```

Cada comando unittest abaixo usa `& $taskPython -m unittest discover -s <diretório> -p <arquivo> -v`. Resultado verde exige exit 0 e os testes novos executados, sem skips. Em frontend, cwd é `apps/frontend`; executar `node node_modules/vitest/vitest.mjs run <arquivos> --pool=threads`. Registrar RED por falha pertinente, depois GREEN; erro de ambiente não prova comportamento.

## Tarefa 1 — Contrato puro e validação de receitas

**Files:** criar `apps/runtime/query_contract.py` e `apps/runtime/tests/test_query_recipe.py`; modificar `apps/runtime/recipe.py`.

**Interfaces:** `validate_query_step(step: dict) -> None` lança `ValueError` com código fixo; `SAFE_QUERY_ERRORS: frozenset[str]`; `QUERY_IDENTITY_ATTRIBUTES: frozenset[str]`. `validate_recipe` traduz erro de validação para `RecipeValidationError`, preservando o contrato público existente.

- [x] Escrever testes parametrizados com a receita completa de exemplo da spec, incluindo `schema_version: 1`, `name`, `variables: {}` e `output: {type: 'none'}`. Asserções: ação `query` preservada; limites 1000/900000 aceitos; 999/900001 e booleanos rejeitados; dois atributos aceitos; atributo arbitrário rejeitado; retry 2 rejeitado; estruturas com campos extras, outcomes faltantes/iguais, frames >16 e seletor >2048 rejeitados. Exemplo: `self.assertEqual(validate_recipe(recipe)['steps'][0]['action'], 'query')`.
- [x] Executar `test_query_recipe.py` e confirmar RED pela ação/validador inexistente.
- [x] Implementar validador sem imports de navegador. Campos específicos da ação: `confirmation`, `result`; subestruturas estritas conforme spec. Preservar os metadados comuns já aceitos pelo schema, mas rejeitar opções exclusivas de outras ações (`button`, `click_count`, `generation`, `baseline`, `value`, `selectors`). Usar `QUERY_CONFIG_INVALID` e `QUERY_RETRY_FORBIDDEN` para erros de receita, separados da allowlist de erros de execução definida na spec. Registrar `query` nas ações permitidas e ajustar seu intervalo de prazo sem mudar outras ações.
- [x] Executar `test_query_recipe.py`, `test_recipe.py` e `test_download_generation_recipe.py`: exit 0.
- [x] Revisar diff e criar commit limitado aos arquivos desta tarefa: `feat: validate correlated query recipes`.

## Tarefa 2 — Protocolo de navegador e integração do runner

**Files:** criar `apps/runtime/query_execution.py`, `apps/runtime/tests/test_query_execution.py`, `apps/runtime/tests/test_query_execution_edge.py`; modificar `apps/runtime/actions.py` e, para propagação de cancelamento, `apps/runtime/runner.py`.

**Interfaces:** consumir tarefa 1; `QueryExecutionError(RuntimeError)` contém somente código fixo; `execute_query(step: dict, context: ExecutionContext) -> None`. Registrar diretamente em `create_default_registry`. Sucesso retorna None; empty/error lançam código permitido. Cancelamento lança `EXECUTION_CANCELLED`; runner converte esse erro tipado em `RunResult(cancelled=True)` e checkpoint `CANCELLED`, sem retry. Não alterar a classificação de exceções arbitrárias de outras ações por comparação livre de texto.

- [x] Escrever teste `test_empty_stops_before_next_step`: executar query e uma ação sentinela; `self.assertEqual(result.error, 'QUERY_NO_DATA')`, `self.assertEqual(sentinel_calls, [])`. Cobrir erro, dados e dry-run (nenhum acesso DOM/afirmação de resultado real).
- [x] Escrever fixtures Edge locais com `page.set_content` e JS interno de teste; classe protegida pelo opt-in sintético existente. Contador de cliques deve ser 1 em sucesso e timeout. Testar resultado antigo visível, confirmação antiga oculta, dados idênticos com geração nova, confirmação síncrona e resultado atrasado, cada outcome, dois outcomes visíveis, duplicidades ocultas, baseline ausente e ID inválido.
- [x] Adicionar testes dos focos 1–3 e de recriação do container, mudança de confirmação, resultado com ID estranho, navegação de página/frame, cancelamento/revogação durante preparação/espera/aceitação. Assertar código específico e ausência de passo seguinte. Usar guards/eventos controlados para evitar testes baseados apenas em sleeps.
- [x] Rodar os dois arquivos novos: confirmar RED pertinente.
- [x] Implementar baseline e um único deadline monotônico. Resolver e revalidar configurações antes de qualquer efeito. Fixar documento/frame com handles; revalidar identidade após autorização. Instalar observação limitada antes do clique, sem guardar textos nem histórico ilimitado. Capturar ID de confirmação síncrono; resultado só é aceito com confirmação ainda válida e ID correspondente. Consultar identidade, conexão e outcomes no mesmo evaluate. Mapear duplicidade a `QUERY_OUTCOME_AMBIGUOUS`, confirmação ausente ao prazo de confirmação, resultado antigo ao prazo de resultado e geração concorrente a `QUERY_SUPERSEDED`.
- [x] Limitar operações pelo prazo restante e checar cancelamento/autorização entre elas; remover observadores/handles em finally. Após tentativa de clique, nunca repetir mesmo que falhe. Envolver exceções desconhecidas em `QUERY_EXECUTION_FAILED` sem encadear conteúdo sensível.
- [x] Testar deadline consumido pela preparação, ausência de reset por mutações e limpeza em todos os caminhos. Injetar ID e texto sentinelas nos fixtures e assertar que não aparecem em eventos, `RunResult`, mensagens de exceção ou checkpoints. Dados temporários só em memória da ação; não adicionar estado persistido.
- [x] Rodar `test_query_execution.py`, `test_query_execution_edge.py`, `test_query_recipe.py` e suíte runtime completa. Confirmar casos novos Edge executados e documentar skips preexistentes separadamente.
- [x] Revisar diff e commit: `feat: execute queries with correlated outcomes`.

## Tarefa 3 — Worker, privacidade e publicação

**Files:** modificar `apps/worker/nexer_worker/processor.py`; criar `apps/worker/tests/test_query_error_policy.py`; ampliar `apps/worker/tests/test_processor.py` e `apps/backend/tests/test_automation_versions_api.py`.

**Interfaces:** consumir `SAFE_QUERY_ERRORS`, `RunResult` e `validate_recipe`. Worker aceita união das allowlists query/download em `_mark_failed`; demais detalhes continuam `AUTOMATION_FAILED`. Nenhum campo, status ou endpoint novo.

- [x] Escrever testes para cada código da allowlist e texto desconhecido sensível. Asserções: código conhecido persistido; texto desconhecido vira `AUTOMATION_FAILED`; IDs/HTML ausentes em dados persistidos. Testar empty/error como FAILED sem continuar, data como sucesso e cancelamento como CANCELLED.
- [x] Escrever round-trip de versão de automação com query: publicar e ler preserva `confirmation`, `result`, `frames` e prazo; versão inválida é rejeitada pelo validador. Usar os bancos temporários e helpers existentes do teste de API, sem banco real.
- [x] Executar os três arquivos pertinentes e registrar RED para suporte ainda ausente, distinguindo testes que já passam por reutilização do validador.
- [x] Implementar somente allowlist e ajustes de integração demonstrados pelos testes. Se o backend já preservar corretamente os campos, manter seu código de produção sem alteração.
- [x] Rodar os três arquivos e suíte worker completa: exit 0. Conferir que cancelamento não chega ao histórico como erro de consulta.
- [x] Revisar diff e commit: `feat: report safe query outcomes in executions`.

## Tarefa 4 — Revisão de consulta e mensagens do histórico

**Files:** criar `apps/frontend/src/lib/queryOutcome.ts`, `queryOutcome.test.ts`, `apps/frontend/src/components/QueryOutcomeEditor.tsx`, `QueryOutcomeEditor.test.tsx`, `apps/frontend/src/lib/executionErrors.ts`; modificar `apps/frontend/src/pages/NewFlowPage.tsx`, `NewFlowPage.test.tsx`, `ExecutionDetailPage.tsx`, `ExecutionDetailPage.cancel.test.tsx`.

**Interfaces:** `QueryOutcomeConfig = {confirmationSelector: string; confirmationAttribute: string; container: string; resultAttribute: string; dataSelector: string; emptySelector: string; errorSelector: string; timeoutMs: number}`. Helpers puros `configureQuery(input: Recipe, stepId: string, config: QueryOutcomeConfig): Recipe`, `removeQuery(input: Recipe, stepId: string): Recipe`; Recipe e Step seguem `Record<string, unknown>` com `steps: Step[]`. `QueryOutcomeEditor({recipe, stepId, onChange, onDirty})` segue o contrato do editor de download. `executionErrorMessage(code: string | null): string` traduz query e delega os demais códigos ao `downloadErrorMessage` existente.

- [x] Escrever testes de helper: input não mutado, IDs/frames/metadados mantidos, conversão de clique simples e reversão removendo campos query. Para desfazer exatamente a conversão nesta sessão, editor conserva snapshot do clique em estado local, nunca na receita; query importada volta a clique simples com metadados comuns. Rejeitar clique direito, duplo, retry >1, referências de download incompatíveis e configuração inválida sem alteração parcial.
- [x] Escrever testes do editor para configuração incompleta, limites de prazo, aplicação, cancelamento de edição e reversão. Texto deve explicar identificação da consulta e interrupção sem dados. Campos técnicos permanecem no editor de revisão, sem aparecer na execução diária.
- [x] Escrever testes de NewFlow com dois editores pendentes e com query mais download: salvar um não libera avanço enquanto o outro estiver pendente. Usar mapa de dirty por ID/tipo no pai, removendo entradas ao remover etapas; não reutilizar um boolean global que um filho possa limpar.
- [x] Escrever testes do histórico: `QUERY_NO_DATA` mostra exatamente a mensagem da spec, demais erros query mostram frases fixas, download mantém mensagem e código desconhecido não ecoa texto original.
- [x] Rodar os quatro arquivos de teste frontend desta tarefa e registrar RED.
- [x] Implementar helpers, editor e integração na etapa Campos de NewFlow. Oferecer conversão apenas em cliques elegíveis; query existente abre editor para alteração. Preservar a captura do gravador como clique, sem adicionar inferência de negócio nem modificar compiler.
- [x] Rodar testes direcionados; depois suíte frontend completa, `node node_modules/typescript/bin/tsc -b` e `node node_modules/vite/bin/vite.js build`: exit 0.
- [x] Inspecionar editor em 1280 e 390 px com API/receita sintética, usando ferramentas e skill de UI disponíveis na execução. Verificar labels, mensagens, dirty state e ausência de overflow; salvar evidências locais ignoradas, sem dados reais.
- [x] Revisar diff e commit: `feat: configure and explain query outcomes`.

## Verificação final e continuidade

- [x] Executar uma vez as suítes completas runtime, recorder, worker, backend e frontend com ambiente acima, além de typecheck/build. Registrar contagens, skips e exit codes; não repetir suítes sem mudanças ou motivo novo.
- [x] Revisar integração completa contra os 12 critérios da spec e os cinco Review Focus. Usar a revisão prevista pelo método de execução escolhido; corrigir achados com regressão específica antes de repetir verificações afetadas.
- [x] Atualizar `HANDOFF.md`, `apps/runtime/README.md`, `README.md` e criar `docs/2026-10-14-query-outcomes.md` com evidências, limitações e estado Git. Não dizer que SGIND funciona sem inspeção real.
- [x] Rodar `git diff --check`, revisar arquivos staged e registrar documentação. Push/PR/merge não fazem parte deste plano; uma autorização posterior pode ampliar o escopo.

## Revisão do plano

Cobertura conferida: validação/compatibilidade (1), estado/prazo/privacidade/cancelamento (2), persistência/publicação (3), revisão/histórico (4), regressão e documentação (final). Interfaces usam a mesma ação `query` e os códigos da spec. Testes não foram executados na elaboração original. Checkboxes atualizados ao concluir a execução; desvios/evidências e revisão estão em `docs/2026-10-14-query-outcomes.md`.

Método recomendado: execução pelo próprio agente nesta conversa, em sequência, com revisão independente ao final conforme a skill de execução. As quatro tarefas compartilham contrato e fixtures; delegar cada uma acrescentaria transferência de contexto. Plano e método inline aprovados pelo usuário em “Continue. Concedo permissão para tudo”. Execução concluída com revisão independente e regressões dos achados; branch/worktree preservados localmente.
