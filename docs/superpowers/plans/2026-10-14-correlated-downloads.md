# Downloads correlacionados em central compartilhada — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans, execução nativa preservada da escolha do usuário. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Vincular cada download ao nome/protocolo de sua solicitação, mesmo com central compartilhada e disponibilização fora de ordem.

**Architecture:** Receitas adicionam snapshot e solicitação com confirmação DOM; o runtime guarda baseline/chave em memória e baixa somente candidato correlacionado único. A revisão frontend configura o vínculo; worker expõe apenas códigos de diagnóstico conhecidos. O adaptador real SGIND permanece dependente de evidência do portal.

**Tech Stack:** Python, Playwright/Edge, React/TypeScript/Vitest, FastAPI existente. Sem novas dependências ou migrations.

**Spec:** [Contrato genérico](../specs/2026-10-14-fresh-downloads-design.md).

## Global Constraints

- Reutilizar `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`, branch `codex/smart-recorder-foundation`, preservando a primeira entrega e seus diffs.
- Sem commit/push/merge, serviços reais, migração de banco existente ou autenticação corporativa nesta entrega.
- Inteligência local: sem modelo/serviço externo e sem dados da demonstração persistidos.
- Valores de baseline/confirmacão existem somente em `ExecutionContext.download_state`, com `repr=False`; máximo 50 snapshots de até 1000 identidades, limpeza antes e depois de cada run.
- Coleções declaradas `shared: true` exigem correlação. Padrão/novidade/ordem não identificam propriedade da solicitação.
- Confirmação por texto ou `data-job-id`, `data-report-id`, `data-download-id`; valor não vazio, novo em relação ao marcador anterior, único/visível e `[A-Za-z0-9_.-]{1,256}`.
- `snapshot_downloads`: orçamento padrão 30000 ms. `request_download` e download correlacionado: padrão 180000 ms, faixa 60000–900000 ms. Polling até 250 ms; cancelamento/autorização antes das leituras e do clique.
- Snapshot imediatamente antes da geração; download após geração; mesmos frames, índice de aba e coleção. Clique esquerdo simples; retry automático proibido na geração/obtenção correlacionada.
- Resultados antigos e múltiplos candidatos correlacionados não iniciam download. Revalidar a identidade no clique, evitando locators posicionais que possam mudar de alvo.

## Review Focus

- A central pode reconstruir/reordenar linhas entre varredura e clique: fixar elemento verificado ou voltar ao polling, nunca clicar pelo índice antigo.
- Um resultado de B aparece enquanto A aguarda, com o mesmo padrão: identidade diferente nunca é selecionada por A.
- Confirmação antiga/duplicada ou nome reaproveitado sem protocolo: não reenviar geração nem aceitar marcador obsoleto.
- Falha/cancelamento/reuso de contexto: nenhum token fica acessível à execução seguinte, em evento ou repr.
- UI recebe receita importada com vínculos existentes: editar/desativar modo mantém passos/IDs consistentes; não remover geração compartilhada por outro download sem diagnóstico.

## Preparação

- [x] Confirmar isolamento/branch e registrar baseline dos testes pertinentes. Usar Python existente em `C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe` com PYTHONPATH absoluto do checkout.
- [x] Para frontend, comparar package/lock com o checkout principal antes de reutilizar `node_modules` por junction; não instalar dependências incidentalmente.
- [x] Ledger próprio em `temp/correlated-downloads/progress.md`; aprovações e evidências resumidas neste plano. Não repetir a primeira entrega.

## Task 1: Contrato e memória efêmera

**Files:** Create `apps/runtime/download_generation.py`, `apps/runtime/tests/test_download_generation_recipe.py`; Modify `apps/runtime/recipe.py`, `apps/runtime/context.py`, `apps/runtime/runner.py`.

**Interfaces:**
- `validate_generation_steps(steps: list[dict]) -> None`: tipos, chaves, limites e referências ordenadas/contextos, levantando erro constante.
- `ExecutionContext.download_state: dict`: estados efêmeros por step ID, excluídos de repr; não usar `variables`/inputs.
- `RecipeRunner.run(recipe, context)` limpa esse campo em início e finally, inclusive falhas de validação/cancelamento.

- [x] Escrever testes: receita válida snapshot→request→download aceita; referência futura/inexistente, outra aba/frame, coleção divergente, source com atributo proibido, retry e shared sem vínculo recusados; receitas antigas seguem válidas. Contexto repr e segunda execução não contêm canário de chave.
- [x] Observar RED com `python -m unittest test_download_generation_recipe -v` (PYTHONPATH inclui apps/runtime/tests).
- [x] Implementar contratos estritos das novas ações e campos, evitando imports cíclicos com `recipe.py` e `actions.py`. Não mudar limites das ações antigas.
- [x] Observar GREEN e executar `test_recipe`, `test_recorded_controls`, `test_runner` para compatibilidade.

## Task 2: Solicitação e obtenção correlacionada

**Files:** Modify `apps/runtime/download_generation.py`, `apps/runtime/actions.py`; Create `apps/runtime/tests/test_download_generation_edge.py`.

**Interfaces:**
- `snapshot_downloads(step: dict, context) -> None`: lê coleção completa dentro do orçamento, guarda identities/página/frames sob step.id.
- `request_download(step: dict, context) -> None`: lê confirmação anterior, clica uma vez e aguarda confirmação nova; guarda chave/página/frames sob step.id, vinculada à baseline.
- `correlated_download(step: dict, context) -> Playwright Download`: espera item correspondente à chave e ao padrão, ausente da baseline; revalida antes de clicar e registra resultado conforme política existente.
- `SAFE_DOWNLOAD_ERRORS: frozenset[str]`: códigos constantes para configuração/contexto, baseline, confirmação, ambiguidade e timeout. Exceções não contêm nomes/chaves/URLs/textos.

- [x] Escrever fixture HTTP com central única e confirmações por sessão: A e B usam o mesmo padrão, recebem chaves diferentes e B fica pronto primeiro. Executar dois contextos Playwright independentes, verificar bytes próprios e nenhum download prematuro por A.
- [x] Escrever cenários: arquivo antigo e DOM reconstruído; nome repetido com job distinto; confirmação antiga/duplicada; dois candidatos com chave igual; baseline incompleta; botão desabilitado/múltiplo; reorder antes do clique; cancelamento A/B independente; autorização revogada; espera acima de 2,5 s; modo por nome completo. Nada usa fila/banco real.
- [x] Observar RED com `NEXER_RUN_RECORDER_E2E=1 python -m unittest test_download_generation_edge -v`.
- [x] Implementar orçamento compartilhado por etapa, leitura limitada e autorização/cancelamento frequentes. Para o clique, usar referência do elemento previamente validado; elemento removido volta ao polling somente antes do clique, sem repetir solicitação.
- [x] Integrar registry/actions: caminho antigo preservado quando não há `generation`; caminho novo usa helpers. Snapshot/request em dry-run simulam sem ler navegador ou criar vínculo real.
- [x] Observar GREEN e executar `test_actions`, `test_download_collection` e testes do gravador relacionados a coleções.

## Task 3: Configuração de vínculo e diagnóstico na UI

**Files:** Create `apps/frontend/src/lib/downloadGeneration.ts`, `apps/frontend/src/lib/downloadGeneration.test.ts`, `apps/frontend/src/components/DownloadGenerationEditor.tsx`, `apps/frontend/src/components/DownloadGenerationEditor.test.tsx`, `apps/frontend/src/lib/downloadErrors.ts`; Modify `NewFlowPage.tsx`, `ExecutionDetailPage.tsx`, `NewFlowPage.test.tsx`, `apps/worker/nexer_worker/processor.py`; Create `apps/worker/tests/test_download_error_policy.py`.

**Interfaces:**
- `configureDownloadGeneration(recipe, downloadId, config) -> recipe`: sem mutar entrada; config contém triggerId, confirmation selector/attribute, identityAttribute, shared e timeoutMs. Gera IDs sem colisão, snapshot antes do trigger, converte click em request_download e vincula download.
- `removeDownloadGeneration(recipe, downloadId) -> recipe`: remove somente passos pertencentes ao vínculo; recusa dependências compartilhadas que seriam invalidadas.
- `downloadErrorMessage(code: string | null) -> string`: somente mensagens fixas de allowlist, fallback genérico sem ecoar código/conteúdo desconhecido.
- Worker `_mark_failed` conserva somente `SAFE_DOWNLOAD_ERRORS`; erros brutos continuam mascarados.

- [x] Escrever testes helper/component: adicionar/editar/desativar vínculo; entradas anteriores intactas; IDs únicos; trigger incompatível/retry rejeitado; shared exige configuração completa; importação de vínculo sem perda; prazo por etapa e confirmação somente estrutural, nunca campo com nome/protocolo real da demonstração.
- [x] Escrever teste de publicação no wizard verificando exatamente snapshot/request/referência gerados, sem iniciar execução. Escrever testes worker de código permitido preservado e canário desconhecido mascarado.
- [x] Observar RED nos testes direcionados Vitest/unittest; implementar componente compacto usado na revisão das coleções e diagnóstico na página de execução.
- [x] Observar GREEN; typecheck e build frontend. Inspecionar desktop/mobile com dados sintéticos, sem serviço real.

## Fechamento

- [x] Rodar suíte completa do gravador com Edge sintético; runtime e worker afetados; protocolo backend de gravação/versões/lote; frontend suíte, typecheck/build. Ler resultados e skips; ampliar verificação só diante de novos problemas.
- [x] Revisão independente conforme skill requesting-code-review, somente leitura e foco em corrida de seleção/cancelamento, dados efêmeros e retrocompatibilidade. Corrigir achados relevantes com RED→GREEN.
- [x] Atualizar README/handoff/ledger com comandos, resultados e limites. SGIND real permanece sem adaptador validado; protocolo/nome disponível na confirmação ainda precisa de evidência.

## Estado

- Método nativo preservado; especificação genérica refinada após a observação de central compartilhada.
- Este plano está pronto para revisão. Implementação deste bloco ainda não iniciada.


## Evidência e rulings de execução (14/10/2026)

- Usuário aprovou execução nativa com “Continue”; worktree existente preservado. Sem nova branch, commit/push/merge, operação corporativa ou banco real. A etapa está implementada localmente; integração Git continua fora do escopo autorizado.
- Separação deliberada: `download_contract.py` mantém validação sem imports de navegador; `download_generation.py` contém I/O. Evita ciclo `recipe -> actions -> recipe`.
- `collection.container` tornou-se obrigatório só no contrato correlacionado: raiz única identifica central vazia versus ausência da central. Limitação DOM/CSS explicitada no spec.
- O helper retorna objeto `Download`, e `actions._download` reutiliza salvamento/preservação de nome/artefatos existentes. Diagnósticos frontend ficaram no mesmo helper de configuração, em vez de novo `downloadErrors.ts`, mantendo uma allowlist de mensagens.
- RED observado em contrato (ação desconhecida/contexto sem memória), Edge (ações ausentes), helper frontend (módulo inexistente) e worker (código permitido mascarado). O componente e seu teste foram criados juntos e o wizard foi acrescentado após integração: não houve RED de comportamento antes dessas duas partes; registrar esse desvio, sem fabricar evidência.
- Corrida sob reconstrução a cada 50 ms reproduziu falha na seleção por elemento/índice. Correção usa raiz fixada e seleção/verificação/clique atômicos no DOM, sem reenvio após clique. Fixture genérica com A/B e mesmo nome confirmou bytes corretos com ordem B→A.
- Revisão independente encontrou P1 confirmação oculta antiga e P1 geração após cancelamento, reproduzidos RED. Encontrou também P2 operações DOM sem limite. Correções e regressões: marcador anterior lido mesmo oculto; prontidão com polling; clique único limitado; leituras com prazo restante; raiz removida não aguarda reaparecer para clicar; cancelamento durante espera de evento; autorização revogada antes de habilitar.
- Segunda revisão independente: 19 testes contrato/Edge passaram; todos os três achados resolvidos, nenhum novo achado material. Janela máxima de despacho nativo até 250 ms após última checagem está dentro do contrato de operações limitadas.
- Evidências ignoradas: `temp/correlated-downloads/{runtime-final,recorder,worker,backend,frontend-final}.log`, screenshots desktop/mobile e `visual_check.py`. Sem serviços persistentes. Um processo de teste travado foi encerrado pelo PID e commandline exatos junto a seus próprios filhos; nenhum processo do usuário foi interrompido.
- Runtime final: 132 coletados, 122 passaram, 10 opt-ins pulados. Gravador: 54 passaram. Worker: 34 coletados, 33 passaram, 1 opt-in pulado. Backend pertinente: 14 coletados, 13 passaram, 1 opt-in pulado. Os opt-ins incluem pilotos/fixture corporativa/login e processos de worker/gravação não habilitados; não são validação SGIND.
- Frontend: suíte completa final 77 passaram (`frontend-final.log`). Integração de mensagens no histórico teve regressão RED→GREEN posterior: 2 testes da página passaram, seguida de `tsc -b` e build Vite. Testes direcionados, `tsc -b` e build Vite passaram. Visual QA: Edge com API simulada em 1280 e 390 px; sem overflow horizontal, controles e textos revisados.
- Fonte completa e próximos limites: `docs/2026-10-14-downloads-correlacionados.md`; adaptação SGIND aguarda evidência estrutural de confirmação da solicitação. Próximo escopo separado: consulta/resultados/erro/sem dados.
