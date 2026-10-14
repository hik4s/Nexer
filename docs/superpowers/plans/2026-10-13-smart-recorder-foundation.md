# Inteligência local do gravador — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native execution or superpowers:subagent-driven-development if the user chooses delegated execution. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Gravar alvos que resistam a mudanças de posição e condições de visibilidade/habilitação realmente observadas, preservando receitas parametrizadas e privacidade.

**Architecture:** Um módulo identifica alvos por seletores CSS estruturais; o observador de prontidão acompanha transições por geração de ação; uma função Python valida e normaliza os eventos antes da compilação. Um bundle único instala os módulos na ordem correta, reaproveitado pela CLI e pelos testes Edge.

**Tech Stack:** JavaScript DOM, Python unittest, Playwright/Edge, formato declarativo de receita v1 existente. Sem dependências novas.

**Spec:** [Especificação aprovada](../specs/2026-10-13-smart-recorder-foundation-design.md).

## Global Constraints

- Base: `origin/feat/nexer-smart-recorder`, commit `a414983c85bae70e23837d4934609d9824207db2`.
- Checkout isolado a partir da base; branch pretendida `codex/smart-recorder-foundation`. Os documentos desta conversa devem acompanhar o trabalho.
- Não publicar, fazer commit/push ou integrar históricos sem autorização correspondente. Os passos de commit usuais são substituídos por revisão de diff e ledger nesta sessão.
- Unificar `readiness` como objeto estrito `{"state": "visible" | "enabled"}`.
- Timeout das condições aprendidas: 30 segundos. Observação válida na mesma geração e documento, por até 30 segundos.
- `learning={source: automatic, confidence: high}` indica transição estrutural observada.
- Esperas manuais imediatamente anteriores no mesmo alvo/frame têm precedência.
- Em `download.collection`, preservar o polling existente sem adicionar espera do botão da linha original.
- Nenhuma leitura de valores de inputs, escolhas, conteúdo de downloads, cookies, tokens, screenshots ou payloads de rede é necessária.
- Testes usam exclusivamente páginas sintéticas, canários fictícios e diretórios temporários. Não iniciar fila real, migrar banco existente ou autenticar nos portais corporativos.
- Preservar ações/receitas antigas, o otimizador idempotente e os diagnósticos de contextos não suportados.

## Review Focus

- Seletores nativos não atravessam shadow roots, enquanto Playwright atravessa: verificar a composição por host e a unicidade da expressão final no replay.
- Nova estratégia de seleção pode quebrar o seletor relativo de botão numa coleção: gerar o seletor dentro da linha explicitamente.
- Mutação síncrona do handler pode ocorrer antes do callback do observer: atualizar gerações na captura e consumir as mutações pendentes no ponto de leitura.
- Início HTTPS pode manter baseline e mudanças da preparação: resetar no início confirmado, em cada frame.
- Reinstalar bundle ou abortar captura pode deixar observers/listeners ativos: cancelar a instalação anterior e provar ausência de eventos duplicados.

## Preparação após revisão do plano

- [x] Usar a skill de worktrees e o tool nativo para criar checkout baseado na referência exata. Reutilizar checkout adequado se já houver um anexado; confirmar isolamento, base e estado Git.
- [x] Copiar o documento de foco, a especificação e este plano para o checkout de implementação. Alterações nesses documentos são próprias desta conversa.
- [x] Reutilizar o Python existente em `C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe`, após confirmar imports necessários; não instalar dependências incidentalmente.
- [x] Executar baseline do gravador no checkout isolado com Edge sintético. Registrar resultado antes de alterar produto. Se houver falha, investigar e apresentar o efeito sobre o plano.

## Task 1: Identificação estrutural e seletores relativos

**Files:**
- Create: `apps/recorder/nexer_recorder/selectors.js`.
- Create: `apps/recorder/tests/test_selectors_edge.py`.
- Modify: `apps/recorder/nexer_recorder/capture.js`.

**Interfaces:**
- Produces: `window.__nexerSelectors.forElement(element: Element) -> string | null`.
- Produces: `window.__nexerSelectors.relativeTo(element: Element, scope: Element) -> string | null`.
- Consumes: nenhum conteúdo de campo; somente tag e atributos estruturais expressamente permitidos.
- `capture.js` usa `forElement` para alvos/frames/drag e `relativeTo` para botão de coleção. `window.__nexerStructuralSelector` continua como alias compatível.

**Política padrão:** identificadores são tokens separados por `-` ou `_`, com no máximo 64 caracteres; todos os tokens pertencem ao vocabulário de interface abaixo. Não aceitar números, espaços, Unicode arbitrário ou fragmentos de placeholders. Priorizar `id`, depois `data-testid`, depois `name`, com verificação de unicidade. Não expor mecanismo externo de ampliação do vocabulário nesta entrega.

Vocabulário: `period`, `start`, `end`, `company`, `regional`, `query`, `search`, `filter`, `filters`, `result`, `results`, `export`, `submit`, `apply`, `run`, `download`, `report`, `form`, `table`, `list`, `menu`, `panel`, `tab`, `tabs`, `content`, `main`, `toolbar`, `date`, `input`, `field`, `button`, `select`, `check`, `checkbox`, `radio`, `frame`, `host`.

Atributos de função só aceitam enumerações HTML conhecidas: `input[type]`, roles de controles/estrutura, `aria-haspopup` e `contenteditable` com valores padronizados. Nenhum `aria-label`, texto, classe CSS, URL, valor de opção ou atributo arbitrário entra no seletor automaticamente.

- [x] **Step 1: escrever testes Edge que falham.** `test_recorded_target_survives_inserted_sibling` grava `#search`/`#run`, insere decoy antes de ambos e reproduz com nova entrada; afirmar input correto atualizado e contador do decoy igual a zero. `test_unsafe_or_duplicate_identifiers_are_not_promoted` usa ID duplicado, UUID e identificador canário, afirmando correspondência única e ausência dos identificadores recusados na expressão.
- [x] **Step 2: observar RED.** Executar `python -m unittest discover -s apps/recorder/tests -p test_selectors_edge.py -v` com `PYTHONPATH=apps/recorder;apps/runtime` e `NEXER_RUN_RECORDER_E2E=1`. Esperado: falha por módulo/API ausente ou replay no alvo errado.
- [x] **Step 3: implementar o módulo e integrar seleção em capture.js.** Verificar candidatos no root atual, tentar ancoragem única e só então caminho posicional. Compor shadow hosts recursivamente. Para `relativeTo`, manter caminho limitado à linha e impedir escape de escopo.
- [x] **Step 4: ampliar regressões úteis.** `test_shadow_host_and_frame_target_survive_layout_change`; `test_relative_download_button_matches_each_row` verifica duas linhas e nenhum seletor global para o botão; `test_selector_policy_never_reads_input_value` usa getter-canário que lança ao ler `value`; alvo dentro da toolbar/formulário sensível não deve gerar seletor por captura.
- [x] **Step 5: observar GREEN e revisar diff.** Executar o arquivo novo e testes existentes de captura. Registrar quais expressões continuam posicionais e por quê; não alterar privacidade para aumentar a taxa de seletores estáveis.

## Task 2: Contrato e ciclo de observação de prontidão

**Files:**
- Modify: `apps/recorder/nexer_recorder/intelligence.js`.
- Modify: `apps/recorder/nexer_recorder/capture.js`.
- Create: `apps/recorder/nexer_recorder/readiness.py`.
- Create: `apps/recorder/tests/test_readiness.py`.
- Create: `apps/recorder/tests/test_intelligence_edge.py`.

**Interfaces:**
- Produces: `normalize_readiness(event: dict, previous_step: dict) -> tuple[dict | None, dict]` em `readiness.py`. Retorna espera opcional e evento original sem `readiness`; não muta os argumentos.
- Produces: `window.__nexerIntelligence.install(signal: AbortSignal) -> void`, `reset() -> void`, `recordAction() -> void`, `readinessFor(element: Element) -> {state: 'visible' | 'enabled'} | null`.
- Consumes: `__nexerRecorderActive` e o AbortController do capture; usa a política de exclusão de contexto sensível compatível com captura, incluindo ascendência por shadow host.

- [x] **Step 1: escrever testes unitários que falham.** Objeto de prontidão válido produz espera `timeout_ms=30000`, origem automática/alta, selector e frames iguais. String legada, campos extras, estado inválido, ação não permitida e `readiness: null` são recusados. Os argumentos originais permanecem iguais após normalização. Espera manual anterior e coleção não geram nova espera.
- [x] **Step 2: observar RED.** `python -m unittest discover -s apps/recorder/tests -p test_readiness.py -v`. Esperado: módulo/função ausente.
- [x] **Step 3: implementar normalização estrita.** Verificar tipos e chaves antes de consumir eventos; validar alvo/frames mediante contratos existentes. Nenhum sinal inválido pode ser removido silenciosamente para produzir evento aparentemente válido.
- [x] **Step 4: escrever testes Edge que falham.** `test_sync_enable_and_parent_reveal_emit_readiness` usa mutação síncrona seguida de ação; `test_preparation_changes_are_reset_before_recording` inicia pausado; `test_reinstall_does_not_duplicate_capture` reinstala módulos; `test_expired_and_actionless_changes_emit_no_readiness` usa relógio controlado. `test_shadow_and_sensitive_contexts` testa controle no shadow aberto e formulário de senha ignorado.
- [x] **Step 5: implementar instalação, reset e consumo.** Uma geração por ação aceita, com resets no início/pausa. Consumir `MutationObserver.takeRecords()` antes de consultar prontidão; respeitar janela de 30 segundos. Usar WeakMap para observações. Orçamento de até 200 registros e 250 controles por lote; descarte conservador da inferência do lote quando excedido. Recalcular baseline após descarte sem atribuir prontidão de alta confiança.
- [x] **Step 6: remover observador paralelo legado de capture.js.** Usar um contrato de prontidão e evitar que marcador legado de 90 segundos substitua resultado do observador integrado. Incluir `choose_radio` no caminho de consulta do estado. Sinais de `download.collection` não inserem espera na linha original.
- [x] **Step 7: observar GREEN e revisar lifecycle.** Rodar os dois arquivos novos; testar mutações de `aria-disabled`, classe/estilo do ancestral, reinicialização, teardown e estouro do orçamento. Não atribuir semântica de consulta concluída a esses sinais.

## Task 3: Bundle ordenado e prova do caminho real

**Files:**
- Create: `apps/recorder/nexer_recorder/scripts.py`.
- Modify: `scripts/record_recipe.py`.
- Modify: `apps/recorder/tests/test_capture_edge.py`.
- Modify: `apps/recorder/tests/test_cli_edge.py`.
- Modify: `apps/recorder/tests/test_record_recipe.py`.
- Modify: `apps/recorder/README.md`.
- Modify: `docs/2026-10-13-smart-recorder.md`.
- Modify: `HANDOFF.md` e este plano, para evidências recentes e ledger.

**Interfaces:**
- Produces: `recorder_script() -> str` em `scripts.py`, concatenando `selectors.js`, `intelligence.js` e `capture.js` nesta ordem, sem dependência da ordem entre múltiplos `add_init_script`.
- CLI consome `normalize_readiness(event, recording.steps[-1])` antes de `Recording.accept`; testes e CLI consomem `recorder_script()`.
- Início HTTPS confirmado chama reset do observador em cada frame após ativar captura; instalação/teardown é ligada ao AbortController da captura.

- [x] **Step 1: escrever regressão do caminho CLI e observar RED.** `test_cli_records_readiness_and_replays_after_layout_change` usa servidor HTTP sintético, grava clique que revela/habilita campo e exporta com `--smart-waits`; replay usa atraso diferente e irmão extra. Afirmar espera de alta confiança, novo valor no alvo, decoy intacto e canários ausentes do JSON. `test_cli_without_smart_waits_keeps_observed_readiness` verifica condição observada sem otimizador genérico.
- [x] **Step 2: integrar bundle e normalizador.** Manter correlação de clique/download, troca de abas, coleção e protocolo de início/finalização. Preservar exclusão de valores e comportamento de erro constante.
- [x] **Step 3: atualizar testes para a instalação usada pelo produto.** Substituir leitura isolada de capture.js pelo bundle. Adaptar assertions de seletores quando o comportamento correto mudou; não relaxar assertions de privacidade ou efeito do replay.
- [x] **Step 4: executar verificação pertinente.** Suite completa do gravador com `NEXER_RUN_RECORDER_E2E=1`; runtime `test_recorded_controls.py`, `test_download_collection.py`, `test_recipe.py`, `test_actions.py`; backend `test_flow_recording.py` com banco/fixtures temporários e paths necessários. `node --check` nos três scripts; `git diff --check`. Não ampliar suites após GREEN sem nova mudança ou preocupação concreta.
- [x] **Step 5: documentação e revisão final.** Registrar limites do vocabulário, fallback posicional, significado de confiança, 30 segundos, bundle e evidências realmente observadas. Analisar diff completo contra critérios da spec. Revisão independente só se houver autorização de delegação ou instrução de skill aplicável na etapa de revisão.

## Comandos de referência

No checkout de implementação, configurar `PYTHONPATH` com caminhos absolutos desse checkout: `apps/recorder`, `apps/runtime`, `apps/backend`, `apps/backend/tests`, `apps/worker`. Usar o Python existente com `python -m unittest discover -s ... -p ... -v`; o comando deve apontar para o checkout isolado, não para módulos antigos do checkout principal.

O servidor dos testes liga somente a loopback; não iniciar dashboard/API/worker de produção. Edge fica headless nas fixtures sintéticas. `scripts/verify.ps1` não é necessário para esta fatia, pois pode instalar dependências e cobre módulos que não são modificados.

## Ledger

- Especificação aprovada pelo usuário com “Continue”.
- Plano aprovado pelo usuário com “Continue”; execução nativa concluída nesta conversa.
- Recomendação: execução nativa nesta conversa, pelo próprio agente, porque os três blocos dependem do mesmo contrato de captura e observação.


## Evidências finais desta sessão

- Checkout isolado: `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`; branch `codex/smart-recorder-foundation`, base `a414983`.
- Baseline: suite do gravador com `NEXER_RUN_RECORDER_E2E=1`, 31 testes, OK, exit 0, 49,371 s.
- Task 1: teste novo reproduziu preenchimento do decoy após inserção de irmão; módulo ausente nas verificações de API. Implementação passou 5 testes iniciais; regressões de duplicidade light/shadow e combinadores posicionais adicionadas com RED observado. Arquivo final: 7 testes Edge OK.
- Task 2: módulo de normalização ausente no RED; 4 testes unitários finais OK, incluindo sinais de tipo inválido. Observer passou 10 testes Edge finais, incluindo preparação, reinicialização, sinais expirados, shadow, orçamento, pausa imediata e inicializações obsoletas.
- Task 3: CLI inicialmente exportava zero esperas observadas; ambos os testes novos falharam. Bundle/normalização integrados e os dois cenários CLI passaram, com/sem otimizador, parâmetros novos, atraso maior e alteração de layout.
- Final: `python -m unittest discover -s apps/recorder/tests -p 'test_*.py' -q`, com Edge sintético habilitado: **54 testes, OK, zero skips, exit 0, 63,881 s**.
- Final runtime: `python -m unittest test_recorded_controls test_download_collection test_recipe test_actions -q`: **18 testes, OK, exit 0**. Esta é verificação selecionada, não a suíte inteira do runtime.
- Final backend: `python -m unittest discover -s apps/backend/tests -p test_flow_recording.py -q`, com fixtures Edge habilitadas: **6 testes, OK, exit 0**.
- `node --check` em selectors.js, intelligence.js e capture.js: exit 0. `git diff --check`: exit 0; aviso ambiental de conversão LF/CRLF em intelligence.js.
- Frontend não alterado; não foram repetidos build/suite frontend.
- Revisão independente read-only: nenhum Critical, dois Important e um Minor. Important: combinadores entre shadow roots e pausa sem atividade incidental. Ambos corrigidos com regressões RED→GREEN. Baseline após orçamento excedido, inicialmente Minor, foi corrigida por ser requisito explícito da spec. Não houve segunda revisão independente após o passe de correção; a suite final acima verifica a árvore corrigida.

## Rulings e limites

- Ruling: scratch/ledger PowerShell em `temp/smart-recorder-foundation` substitui scripts bash auxiliares — ambiente Windows e commits não autorizados; evidências persistidas neste plano.
- Ruling: teste CLI novo em `test_smart_cli_edge.py`, separado do arquivo CLI antigo — mantém testes focados e legíveis sem crescer o arquivo existente.
- Ruling: testes contam eventos após confirmação do binding — entrega assíncrona pode acontecer depois de fill/click retornarem; evita falsa falha sem mudar o produto.
- Ruling: assertions antigas da preparação HTTPS preservam as 9 ações originais e verificam a nova espera de visibilidade do botão de popup — a condição é resultado esperado da inteligência integrada.
- Ruling: verificar seletores pelo subconjunto CSS produzido, com ascendência por shadow host — queries nativas separadas por root davam falsa unicidade. Colisão detectada gera seletor ausente e diagnóstico de contexto, sem exportar ação insegura.
- Ruling: ativação/pausa invalida imediatamente e blur reinicia baseline; resposta privada obsoleta é ignorada antes de alterar estado — evita reutilizar condição antiga ou parar instalação nova.
- Ruling: após orçamento excedido, descartar inferência e reconstruir baseline limitada sem gerar prontidão nessa recuperação — controles amostrados podem aprender depois de uma nova ação; não prometer observação completa em páginas grandes.
- Uma fixture de promessa atrasada ficou pendente por retornar a própria função ao evaluator; foi corrigida para retornar void. A árvore exclusivamente desse teste foi identificada e encerrada; nenhum serviço do usuário foi afetado.
- Branch e worktree preservados, alterações sem commit/push/merge, conforme limites aprovados. A instalação no checkout principal continua na versão anterior.
- Critérios de download demorado, arquivo novo, resultado/erro/sem dados, novos adaptadores e validação SGIND/IQOS seguem na próxima entrega.
