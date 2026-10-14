# Nexer — consolidação completa e contexto de continuidade

Data: 14/10/2026. Idioma de trabalho: português. Este documento consolida decisões, implementações, evidências e pendências da sessão até a solicitação de salvar o contexto e fazer git push. Não contém credenciais, cookies, tokens nem dados corporativos reais.

## Estado atual e precedência

O trabalho atualizado está em `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`, branch `codex/smart-recorder-handoff-2026-10-14`, remoto `origin` = `https://github.com/hik4s/Nexer.git`. O diretório informado no chat, `C:/Users/hikas/Documents/ChatGPT/Nexer`, é um checkout anterior; suas alterações locais não foram sobrescritas. Não inicializar o gitlink Nexer nem copiar arquivos sobre o checkout antigo por reflexo.

Este documento é um snapshot de continuidade, não uma declaração de conclusão do seletor visual. As seções históricas anexadas conservam o texto original e suas referências temporais: frases como “sem push”, “próximo avanço não implementado” e “sem picker visual” descrevem aquele momento. Para o estado corrente, prevalecem as seções iniciais deste documento. O push solicitado agora publica a branch e o trabalho em andamento; não solicita merge, PR, deploy, instalação ou uso de serviços corporativos.

## Intenção e autorizações do usuário

O usuário solicitou continuar repetidamente, concedeu “Continue. Concedo permissão para tudo” e escolheu explicitamente “Revisar e corrigir etapas sem regravar tudo”. A seleção visual foi o avanço em curso dessa direção. A solicitação mais recente mudou a entrega imediata para consolidar todo o contexto em Markdown, salvar e fazer git push. Por isso o estado intermediário do picker é preservado com sua pendência explícita, sem apresentar a feature como finalizada.

## Linha de implementação e commits anteriores

- `a414983`: base com gravador inteligente e melhorias de estabilidade.
- `04fcece`: inteligência local do gravador e downloads correlacionados.
- `3fb7062`: especificação de consultas correlacionadas.
- `a0c0b21`: validação de receitas query.
- `ba616a5`: execução query com resultados correlacionados.
- `554997c`: resultados seguros nos históricos de execução.
- `c0efe56`: supressão de detalhes privados de exceções de consultas.
- `477ff5d`: configuração e explicação de resultados de consultas na UI.
- `ede8813`: correções de concorrência na aceitação de query e preservação de rascunhos.
- `54004be`: documentação da entrega query e revisão.
- `f1994d5`: revisão e reparo de alvos sem regravar; base da implementação visual atual.

Os detalhes completos das entregas anteriores estão anexados abaixo. Seus testes são evidências de cada entrega, não execuções novas desta solicitação de documentação.

## Implementação visual em andamento sobre f1994d5

### Experiência e escopo

O editor pode abrir uma sessão nova e efêmera de Edge na URL inicial configurada. O usuário prepara a página manualmente, ativa Selecionar alvo e escolhe um elemento. O seletor retornado preenche somente o rascunho; Aplicar continua obrigatório. Não há replay automático do fluxo. A edição manual continua disponível.

A primeira versão atende página principal: texto, select nativo, checkbox, range/color e elementos genéricos de clique/espera/hover/scroll/press/drag, incluindo destino de arrastar. Frames e controles customizados choose/choose_radio permanecem manuais. IDs, ação, parâmetros, ordem e contexto da receita não são alterados pela aquisição visual.

### Contrato, captura e driver

- `apps/runtime/target_picker_contract.py`: contrato puro compartilhado; valida configuração exata URL/tipo e resultado exato `{selector}`. Tipos: element, text, select, checkbox, range, color. Gramática estrutural com limite de 2048 caracteres e vocabulário restrito para IDs/atributos. Rejeita texto livre, IDs privados, valores, href e seletores arbitrários fora da política. Decisão: colocar no runtime em vez do recorder evita novo PYTHONPATH no backend; o plano original ainda registra o caminho inicial.
- `apps/recorder/nexer_recorder/target_capture.js`: usa selectors.js e instala captura antes dos handlers da página; barra Preparar página / Selecionar alvo / Cancelar seleção. Exige clique confiável. Intercepta ponteiro, mouse, teclado, input e submit durante seleção; também intercepta eventos da barra. Guarda referência do nó realmente escolhido. Corrigida corrida inicial de revisão que deixava a preparação bloqueada.
- `apps/recorder/nexer_recorder/target_picker.py`: expõe target_script, validate_selection e pick_target. Valida página/frame, unicidade, visibilidade, compatibilidade e identidade do nó conectado. Rejeita html/body/canvas/iframe/password/hidden/file. Usa fila limitada para executar validação Playwright fora dos callbacks. Fixa documento durante seleção; troca de documento invalida. Seleção exige origem correta, uma página e ausência de password visível. Fecha navegador próprio em finally.
- `scripts/pick_target.py`: configuração JSON pelo stdin privado, monitor de cancelamento/EOF e protocolo de fase/resultado/erro com mensagens fixas. Sem eco de exceções ou conteúdo do site.

### Backend e ciclo de vida

- `apps/backend/app/services/login_recordings.py`: hook de validação de configuração; default preserva comportamento de login existente.
- `apps/backend/app/services/target_pickings.py`: serviço específico reutiliza lifecycle privado, ownership, TTL de 300 segundos e capacidade 2 por owner/32 global. Valida protocolo estrito e aceita DONE somente em SELECTING. Lock e status protegem contra resultado após cancelamento. Cancelamento inicia reap do subprocesso imediatamente, com fallback de cleanup.
- `apps/backend/app/api/target_pickings.py`: POST/GET/cancel em /target-pickings; autenticação local e owner da sessão, validação estrita, respostas de sucesso no-store e erros fixos. O handler global de erro não foi alterado para adicionar no-store aos erros, que não carregam dados do alvo.
- `apps/backend/app/main.py`: router e integração de sweep/close_all no lifespan. Sem tabela ou migração nova.
- Estados: PREPARING → SELECTING → DONE/FAILED/CANCELLED. Voltar à preparação é permitido. Navegador e contexto são novos, sem perfil persistente/downloads.

### Frontend e concorrência

- `apps/frontend/src/lib/api.ts`: tipos e start/get/cancelTargetPicking; GET suporta AbortSignal.
- `apps/frontend/src/components/VisualTargetPicker.tsx`: polling sequencial de 500 ms, geração por sessão, cancelamento imediato local e aborto do GET. Se POST termina após invalidar/unmount, cancela a sessão recém-criada. Resposta antiga não preenche outro rascunho. Erros fixos preservam edição manual.
- `apps/frontend/src/components/StepReviewEditor.tsx`: integra picker ao alvo e destino, mapeia tipo, conserva rascunho e controla busy/dirty. Aplicar e navegação ficam bloqueados durante seleção. Edição/descarte invalidam a aquisição.
- `apps/frontend/src/pages/NewFlowPage.tsx`: fornece URL ao editor.

### Políticas mantidas e limites

Somente origem configurada; redirects e websocket bloqueados, service workers e Worker/SharedWorker desabilitados. Preparação permite navegação manual na mesma origem; SELECTING bloqueia métodos diferentes de GET/HEAD. Não foram ampliados gates de HTTPS/SSO/origem. Não se promete proteção contra scripts hostis, requisições autônomas ou efeitos implementados em GET.

O protocolo não transporta valores digitados, credenciais, HTML, screenshots nem URL final. A política de seletores aproveita o vocabulário estrutural existente; metadados arbitrários podem conter dados de negócio. Sessões não persistem no banco. Testes sintéticos não validam SGIND/IQOS real.

## Verificação observada da implementação atual

Logs locais em `temp/visual-target-repair/`, ignorados pelo Git. Foram lidos após a retomada:

| Verificação | Resultado observado |
| --- | --- |
| Recorder, Edge opt-in habilitado | 63 testes, OK, sem skips; 72,922 s |
| Backend | 150 coletados, 138 passaram, 12 skips; 20,158 s |
| Frontend | 106 testes em 30 arquivos, todos passaram; 104,81 s |
| TypeScript tsc -b | log vazio, execução anterior registrada como bem-sucedida |
| Vite build | 119 módulos, build concluído em 5,01 s |

Testes novos cobrem contrato, privacidade, contexto/tipo inválido, eventos usuais bloqueados, preparação, shadow aberto, clique sintético ignorado, identidade do nó substituído, ownership, TTL/capacidade, cancelamento e resultado tardio, autenticação/API e rascunho sem aplicação automática. O teste de driver usa Edge real e servidor sintético: POST bloqueado durante seleção, efeito do botão zero e navegador desconectado no finally. Testes de protocolo backend usam processos simulados; não afirmar que houve E2E completo do CLI até o frontend.

Houve ciclos RED/GREEN para contrato ausente, seleção/identidade do nó e UI. A ampliação posterior de driver/capacidade não teve um RED independente registrado. Suítes runtime/worker não foram repetidas nesta implementação visual; seus últimos resultados estão no relatório query. QA do app compilado em desktop/mobile para o picker ainda não foi feito; o QA anterior pertence ao reparo manual.

## Revisão independente e pendência obrigatória

Revisor independente concluiu uma ocorrência importante ainda NÃO corrigida:

**Recolher o editor não cancela a seleção visual.** TargetEditor permanece montado dentro de details não controlado, sem propagar estado aberto/fechado. Fechar apenas oculta o conteúdo. A sessão Edge continua ativa; DONE tardio ainda pode preencher rascunho oculto e busy/dirty continua bloqueando navegação. Isso viola a spec de invalidar ao fechar.

Próxima correção sugerida, ainda não implementada: acompanhar abertura por ID estável, invalidar/cancelar aquisição ao fechar e preservar rascunho manual. Antes do fix, adicionar regressão que fecha details com GET pendente, verifica cancelamento e ignora DONE tardio; reabrir deve conservar edição manual. Depois repetir testes afetados, TypeScript/build e QA. Não declarar a feature concluída enquanto essa pendência existir.

Revisor examinou e não promoveu a achados: respostas atrasadas após cancel/unmount, identidade do nó/documento, frames, captura de eventos, aplicação somente explícita, privacidade/owner. Não estabeleceu caminho alcançável para substituição de receita com mesmos IDs/seletores durante aquisição. Não editou código. A revisão completa deve ser aproveitada, sem reiniciar toda a implementação.

Outras observações de continuidade, sem classificação de bug confirmado: limite de readline(8192) no CLI merece comparar com URL máxima serializada/Unicode; invalidação de props depende de efeito React; não alterar preventivamente sem reproduzir. Não confundir essas observações com o achado confirmado.

## Próximos passos após este snapshot

1. Corrigir fechamento do editor com regressão RED/GREEN, preservando rascunho.
2. Repetir suítes afetadas; considerar regressões runtime/worker conforme imports; registrar skips honestamente.
3. QA do build em 1280×1000 e 390×844, sem overflow; conferir bloqueio de navegação durante aquisição, preenchimento só de rascunho e Apply explícito. Separar API simulada de driver Edge real.
4. Quando aplicável, coletar receita reparada pela UI e reproduzir em fixture real do runtime: original falha no alvo antigo, reparada conclui; canário da execução ausente da receita/eventos.
5. Atualizar relatório de entrega, README/HANDOFF e plano conforme evidências. Não marcar checkboxes retroativamente como concluídos sem a evidência.
6. Portal corporativo continua não validado. Não iniciar produção, alterar banco real/gates ou instalar executável como consequência de testes locais.

## Ambiente e preservação

Python disponível no venv do checkout antigo: `C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe`. Worktree usa junction local de node_modules após comparação de package/lock; isso não viaja no Git. Em clone novo, instalar dependências pelo lock. PYTHONPATH e comandos de teste estão no HANDOFF anexado. Não usar tsc --noEmit no tsconfig raiz como substituto de tsc -b.

Evidências temporárias ignoradas incluem logs, scripts e screenshots em temp/query-outcomes, temp/step-review e temp/visual-target-repair. Não são arquivos de entrega no push. Uma limpeza recursiva anterior foi bloqueada automaticamente; preservar evidências, não buscar workaround para exclusão. Não apagar diffs do checkout antigo. Nenhum segredo deve ser incluído no snapshot ou no Git.

## Anexos integrais de contexto versionado

Os documentos abaixo são incorporados para que este arquivo seja autossuficiente. Podem conter estado histórico superado pelas seções iniciais.

---

### Fonte: HANDOFF.md

# HANDOFF — Nexer: estado consolidado para o próximo chat

Atualizado em 14/10/2026. Este é o ponto de entrada da continuação. Leia antes de modificar o código. Os documentos antigos são contexto histórico; não comprovam instalação ou validação corporativa atual.

**Continuação mais recente:** o contrato de consultas com resultado correlacionado foi implementado neste mesmo worktree/branch. Leia a seção 12 e `docs/2026-10-14-query-outcomes.md`; a prioridade de desenhar esse contrato, descrita abaixo, já foi atendida. Não reimplementar as quatro tarefas do plano.

**Avanço posterior:** revisão e reparo de alvos na etapa Campos implementados; veja seção 13 e `docs/2026-10-14-step-review.md`. Não recomeçar essa implementação.

## 1. Objetivo e decisões do usuário

Construir um gravador inteligente, estável e versátil para tarefas comuns, sites dinâmicos e ambientes empresariais. O usuário demonstra um fluxo; o Nexer interpreta ações e transições verificáveis, gera uma receita parametrizada e permite reproduzi-la com entradas diferentes.

Decisões que não devem ser reabertas sem motivo:

- **Método B:** núcleo genérico confiável com adaptadores reutilizáveis por componente/site. Não confundir com a antiga opção B de entrega efêmera de credenciais.
- **Inteligência local estrutural:** DOM, acessibilidade, eventos, estados e regras. Não é um agente de IA conduzindo navegação livremente.
- **Sem API paga de IA no funcionamento essencial.** O usuário descartou essa direção. Nenhum LLM local é requisito; não introduzir Ollama/modelo por padrão. Não foi feito benchmark do hardware corporativo.
- Evidência ambígua deve gerar revisão ou interrupção; não inferir propriedade, sucesso de negócio ou repetibilidade sem sinais verificáveis.
- Motor serve tarefas gerais, inclusive formulários sem datas. SGIND/IQOS são casos de uso/adaptação, não regras espalhadas pelo núcleo.
- O usuário informou que haverá vários relatórios baixados simultaneamente em lote e que a central SGIND é compartilhada por todos.
- Nomes SGIND normalmente seguem `TodasOcorrencias-XXXXX.csv`, com vários números aleatórios no sufixo; outros relatórios têm outros prefixos. Isso permite filtrar tipo, mas NÃO comprova qual solicitação originou o arquivo.
- A informação ainda ausente é onde o portal entrega o nome integral/protocolo/ID para a execução que fez a solicitação. Não presumir que os números do nome sejam um job ID.

O usuário autorizou agora salvar tudo, consolidar o handoff e fazer commit/push em **nova branch**. Não pediu merge nem PR. Essa autorização não significa executar serviços corporativos ou alterar instalação real.

## 2. Fonte de verdade, Git e ambientes

| Item | Estado desta continuação |
|---|---|
| Repositório | `https://github.com/hik4s/Nexer.git` |
| Branch de entrega | `codex/smart-recorder-handoff-2026-10-14` |
| Base remota indicada pelo usuário | `feat/nexer-smart-recorder` |
| Commit base | `a414983c85bae70e23837d4934609d9824207db2` |
| Checkout com implementação | `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer` |
| Branch anterior deste worktree | `codex/smart-recorder-foundation` |
| Checkout principal local | `C:/Users/hikas/Documents/ChatGPT/Nexer` |
| Branch do checkout principal | `codex/nexer-reusable-flows-2026-10-13`, código anterior |
| Python usado | `C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe` |
| Ambiente | Windows, PowerShell, Edge via Playwright, timezone America/Sao_Paulo |

**O código atualizado está no worktree/branch de entrega, não no checkout principal anterior.** O principal recebeu cópias dos documentos para leitura. Não iniciar seu launcher supondo que executa este código. Para outro computador, clonar/fazer checkout da branch de entrega e verificar `git status`, `git log -1` e upstream antes de trabalhar.

O commit base é uma raiz sem pais; existem `data/nexer.db` versionado e gitlink aninhado `Nexer` herdados da base. Não foram examinados, alterados nem adicionados novos dados de banco nesta entrega. Não mesclar automaticamente essa raiz ao histórico antigo. Limpeza de banco versionado, gitlink e integração de históricos exigem trabalho próprio; não inicializar submódulo nem reescrever história incidentalmente.

Historicamente outro computador usava uma exportação em `C:/Users/kis/Downloads/...`, sem `.git`, e `Nexer-Atualizado.exe`; não aplicar seus caminhos, processos, estado de atualização ou hashes ao computador atual. Não substituir executáveis antigos sem investigação. O histórico integral foi preservado em [handoff anterior](docs/archive/HANDOFF-before-consolidation-2026-10-14.md).

## 3. Arquitetura e produto existente

Nova arquitetura em `apps/`: React/TypeScript → FastAPI → worker → runtime Playwright/Edge; SQLite para configuração/histórico e eventos SSE para acompanhamento. O legado Streamlit permanece na raiz e não define o contrato atual de credenciais ou execução.

- `apps/frontend`: Meus fluxos, Acessos, Execuções; cadastro guiado, revisão de campos/esperas/downloads; Studio técnico, rotinas, favoritos, destinos e lotes.
- `apps/backend`: receitas e versões, validação/publicação, gravações, perfis/grupos de acesso, execução/lotes e canais de worker/credenciais.
- `apps/recorder` + `scripts/record_recipe.py`: captura no Edge, preparação manual para login HTTPS, toolbar, compilação da demonstração em receita.
- `apps/runtime`: esquema declarativo v1, resolução de parâmetros, registry de ações, frames/abas, downloads, artefatos, validação de arquivo, cancelamento/autorização.
- `apps/worker`: execução isolada, checkpoints/eventos, status, cancelamento, perfis/credenciais efêmeras e envio de resultados conforme política existente.

Já havia biblioteca de fluxos, versões, execução parametrizada, lotes/isolamento de processos, acesso sem credenciais persistidas, vários controles, abas e contextos suportados. A existência de telas/ações/testes unitários não comprova usabilidade cotidiana nem compatibilidade geral.

## 4. Entrega A — fundamento do gravador inteligente

Implementada nesta conversa, preservada integralmente na nova branch:

- `selectors.js`: candidatos estruturais com política restrita de metadados, unicidade, âncoras e fallback posicional; seletores relativos para botões de coleção. Não usa valores digitados, texto arbitrário, URL ou ID potencialmente sensível como identificador persistido.
- `intelligence.js`: observação realmente integrada de controles que se tornam visíveis/habilitados; geração por ação, janela de 30 s, limites de 200 mutações/250 controles/1000 nós; shadow DOM aberto nos limites suportados; recuperação de baseline após observação parcial.
- Pausa, perda de foco e reinstalação invalidam associações antigas. Observadores removidos são podados. Orçamento excedido não produz inferência incompleta como certeza.
- `readiness.py`: contrato estrito para converter prontidão observada em espera, sem duplicar espera equivalente nem interferir em coleções; esperas manuais mantêm prioridade.
- `scripts.py`: bundle ordenado seletores → inteligência → captura; CLI usa o bundle real.
- `capture.js`: proteção contra respostas antigas de inicialização e listeners duplicados. Integração não reativa observações de geração anterior.

Verificação anterior: 54 testes do gravador com Edge, 18 regressões selecionadas runtime e 6 testes backend passaram. Revisão independente revelou colisões em shadow DOM e pausa não invalidada imediatamente; regressões/correções concluídas. É estabilidade estrutural/prontidão; ainda não é confirmação de resultado de negócio.

## 5. Entrega B — downloads correlacionados em central compartilhada

Contrato genérico implementado, sem presumir detalhes SGIND:

1. `snapshot_downloads` imediatamente antes da geração registra a baseline da central.
2. `request_download` faz um clique esquerdo simples, uma vez, e espera uma confirmação nova.
3. `download.generation` referencia a solicitação e baixa somente o candidato correlacionado.

Detalhes e garantias:

- `collection.container` identifica uma raiz única existente; central vazia é válida, central ausente não. Seletores CSS DOM, coleção materializada, até 1000 identidades por snapshot e 50 snapshots por execução.
- Confirmação por texto contendo nome integral ou atributo `data-job-id`, `data-report-id`, `data-download-id`. Identificador limitado a 256 caracteres ASCII de letras/números/ponto/hífen/sublinhado.
- O marcador anterior é lido mesmo oculto. Após gerar, a confirmação deve ser única, visível, nova em relação ao marcador anterior e ausente da baseline.
- Na linha, identidade é o nome integral ou o atributo configurado; precisa corresponder à confirmação. Padrão de nome/novidade/ordem não comprovam propriedade.
- `shared: true` exige correlação na validação. Receitas antigas continuam compatíveis, mas sua seleção pelo primeiro nome correspondente não recebe garantia de segurança concorrente.
- Mesma coleção, frames, índice de aba e página real; referências ordenadas. Retry automático proibido na geração e download correlacionado. Não repetir clique quando timeout torna o resultado incerto.
- Estado exclusivamente em `ExecutionContext.download_state`, fora de repr, inputs, variáveis comuns, banco/eventos/checkpoints. Limpo antes e em finally após cada run, inclusive erro/cancelamento.
- Snapshot padrão 30 s; confirmação e obtenção têm prazos separados de 1–15 min, padrão 3 min. Polling 100 ms; leituras/dispatch respeitam orçamento e limite de espera de até 250 ms. Cancelamento/autorização verificados durante espera e antes do efeito.
- A seleção final usa raiz DOM fixada/conectada e verifica identidade/botão e clica atomicamente. Reordenação e reconstrução de linhas não autorizam trocar o alvo.
- Evento de download aguardado com polling cancelável. Salvamento/nome fornecido pelo site/proteção contra sobrescrita/artefatos reutilizam a política existente. O prazo termina no evento, não promete prazo rígido para transferência/salvamento.
- UI permite configurar geração, confirmação, raiz, identidade, prazo e central compartilhada. Alterações pendentes bloqueiam avanço. Edição de seletores sincroniza baseline; IDs não colidem; remover vínculo usado por outro download é recusado.
- Worker persiste somente códigos de erro em allowlist; histórico mostra mensagens fixas. Exceções desconhecidas não são ecoadas.

Arquivos principais: `apps/runtime/download_contract.py`, `download_generation.py`, `recipe.py`, `context.py`, `runner.py`, `actions.py`; `apps/frontend/src/lib/downloadGeneration.ts`, `components/DownloadGenerationEditor.tsx`, páginas NewFlow/ExecutionDetail; `apps/worker/nexer_worker/processor.py`.

Teste sintético de concorrência: servidor local, duas instâncias/contextos Edge independentes, central reconstruída a cada 50 ms, mesmo padrão e mesmo nome de arquivo; B aparece antes de A. Os bytes finais comprovam que A baixou A e B baixou B. Inclui atraso superior à janela antiga de 2,5 s.

Revisão independente identificou confirmação antiga oculta, geração após cancelamento durante auto-wait e operações DOM sem limite. Foram corrigidas com regressões, incluindo revogação, espera de evento e raiz que reaparece tardiamente. Segunda revisão: 19 testes contrato/Edge passaram, sem novos achados materiais. Há janela de até 250 ms entre última checagem e término do dispatch nativo; não prometer atomicidade distribuída de cancelamento.

## 6. Visão crítica — onde ainda falta maturidade

1. **SGIND/IQOS real não validado.** Não houve login corporativo nem jornada real gravar → reproduzir → baixar → validar. Gates existentes continuam fechados. Prefixo aleatório de CSV não resolve ownership.
2. **Prontidão não é resultado.** `visible`/`enabled` ajudam no timing, mas não comprovam consulta concluída, dados atualizados, erro ou vazio. Esse é o próximo contrato a construir.
3. **Adaptadores precisam de evidência.** Paginação, virtualização, shadow DOM na coleção de download, centrais só acessíveis após gerar, canvas, shadow fechado e eventos que exigem `isTrusted` não são cobertos genericamente por esta entrega. Não relaxar a correlação para fazer uma demo passar.
4. **Seletores conservadores têm tradeoffs.** A política de privacidade limita atributos/textos. Fallback posicional permanece vulnerável a certos layouts; falta reparo visual assistido e explicação de ambiguidade. Suportar shadow aberto em captura não implica suportar toda coleção shadow no runtime novo.
5. **Sem semântica completa de consulta.** Falta reconhecer resultados novos versus stale, sucesso/erro/sem dados, campos opcionais e ramos por evidência. Não ampliar retries de ações com efeito sem contrato de repetibilidade.
6. **Revisão ainda técnica.** A configuração de correlação exige seletores e conhecimento de confirmação. O próximo salto de usabilidade precisa reduzir trabalho manual por adaptadores/revisão guiada, não escondendo incertezas.
7. **Rascunho/reparo/retomada incompletos.** Preservar etapas válidas ao detectar componente não suportado e corrigir etapa sem regravar tudo são prioridades. Snapshots são efêmeros, não checkpoints para retomar após restart; não reenviar geração automaticamente.
8. **Operação/instalação precisa de validação própria.** Não atualizado executável/installer, não medido consumo na máquina corporativa, não validado ciclo real de restart/worker/filas sob falha. Nada nesta entrega autoriza trocar instalação ativa.
9. **Git herdado requer cuidado.** Banco versionado/gitlink/commit raiz e checkout principal antigo são riscos de continuidade. Consolidar história/remoção de dados em etapa separada, com evidência e escopo explícito.

O produto está mais coerente e melhor testado; ainda não está comprovado como automação empresarial universal. Não reduzir essa distância a um número de testes sintéticos.

## 7. Próximos passos recomendados

**Prioridade imediata:** desenhar contrato genérico consulta → resultado/erro/ausência de dados. Definir evidência de atualização posterior à ação, resultado stale, prazo, cancelamento, apresentação no histórico e comportamento quando sinais competem. Não substituir por delay fixo nem chamar botão habilitado de sucesso. Usar fixture sintética antes do portal real.

**Em paralelo:** descobrir, em inspeção autorizada SGIND, onde aparece o nome completo/protocolo/ID da solicitação. Se existir, implementar adaptador que extraia apenas metadado necessário e ligue à linha correta. Se não existir, explicar a limitação e desenhar alternativa verificável; não assumir ordem, novidade, exclusividade por tipo ou central isolada.

Depois: revisão visual/reparo pontual, preservação de rascunho incompleto, adaptadores de controles complexos; testes sintéticos de worker/lote com falhas/cancelamento/restart; validação corporativa acompanhada com credenciais efêmeras; embalagem Windows reproduzível. Não introduzir IA externa nem ampliar origens/gates por conveniência.

## 8. Testes e evidências

Os relatórios das entregas preservam verificações anteriores; a verificação completa imediatamente anterior ao commit está registrada em `docs/2026-10-14-verificacao-handoff.md`. Leia contagens, skips e comandos; não converter opt-in pulado em aprovação.

Evidências locais ignoradas: `temp/smart-recorder-foundation`, `temp/correlated-downloads` (logs/fixtures/screenshots desktop e mobile), `temp/handoff-2026-10-14`. As conclusões, contagens e achados estão versionados; logs gerados/dados de execução não são adicionados ao Git. Não houve novos pacotes ou migrations de produção.

Em alguns ensaios um processo de teste travou; foi encerrado pelo PID e commandline exatos junto aos seus filhos. Não foram interrompidos serviços do usuário. Um teste retornava função de `page.evaluate`, que Playwright executava/aguardava: usar callback com bloco e sem retorno incidental para setup JS.

Processo: RED→GREEN em contratos/runtime/selector/helper/worker; componente e primeiro wizard foram criados depois da integração sem RED de comportamento inicial. Desvio explicitamente registrado no plano; não inventar evidência TDD. Diagnóstico de histórico teve RED→GREEN próprio. Revisões somente leitura, sem dados corporativos.

## 9. Como continuar no computador atual

Primeiro confirmar cwd, branch, status/upstream, arquivos e eventuais instruções AGENTS/skills. Não criar checkout paralelo se este worktree servir. Não sobrescrever checkout principal com código sem verificar seus diffs. Não inicializar o gitlink `Nexer`.

```powershell
Set-Location 'C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer'
git status --short
git branch --show-current
git log -1 --oneline
git remote -v
$env:PYTHONPATH="$PWD/apps/runtime;$PWD/apps/runtime/tests;$PWD/apps/recorder;$PWD/apps/backend;$PWD/apps/backend/tests;$PWD/apps/worker"
$env:NEXER_RUN_RECORDER_E2E='1'
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' -m unittest discover -s apps/runtime/tests -q
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' -m unittest discover -s apps/recorder/tests -q
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' -m unittest discover -s apps/worker/tests -q
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' -m unittest discover -s apps/backend/tests -q
Set-Location apps/frontend
node node_modules/vitest/vitest.mjs run --pool=threads
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
```

`node_modules` deste worktree foi reutilizado por junction para o checkout principal após verificar package/lock idênticos. A junction é local/ignorada, não faz parte da branch. Em novo clone, instalar dependências conforme lock e configurar Python/Edge; não presumir que essa junction existe. `tsc --noEmit` no tsconfig raiz de referências não substitui `tsc -b`.

Não habilitar testes corporativos reais ou iniciar workers/API/migrations em banco existente sem verificar escopo/ambiente e autorização. Alguns opt-ins são sintéticos, mas precisam de ambiente próprio. Scripts operacionais e handoffs antigos não são autorização para restart.

## 10. Regras de continuidade

- Receita declarativa, sem JavaScript fornecido pelo usuário. JS interno do runtime tem escopo e limites definidos.
- Valores digitados na demonstração não viram defaults nem nomes secretos persistidos. Credenciais/cookies/tokens não entram em receita, logs ou banco. Segredos somente na execução, efêmeros.
- Metadados DOM só conforme política de privacidade; textos/IDs arbitrários podem ser dados de negócio.
- Ambiguidade ou perda de contexto interrompe. Arquivo novo/padrão/ordem não comprova vínculo.
- Repetir geração/download com efeito requer contrato explícito; nunca reenviar por timeout incerto.
- Não mexer em produção, dados reais, gates de origem/corporativos ou executáveis por reflexo.
- Não confundir validação sintética com validação no portal. Registrar evidência e limites de cada entrega.
- Preservar alterações existentes e usar Git legítimo. Push autorizado nesta entrega; merge/PR não solicitado.

## 11. Mapa de leitura

1. Este `HANDOFF.md` e [verificação final](docs/2026-10-14-verificacao-handoff.md).
2. [Visão e decisões de inteligência local](docs/2026-10-13-foco-gravador-inteligente.md): consolidação do diagnóstico GPT Astra, não transcrição literal; os achados ali descrevem a base antes das duas entregas.
3. [Spec de fundamento](docs/superpowers/specs/2026-10-13-smart-recorder-foundation-design.md) e [plano/evidências](docs/superpowers/plans/2026-10-13-smart-recorder-foundation.md).
4. [Entrega de downloads](docs/2026-10-14-downloads-correlacionados.md), [spec](docs/superpowers/specs/2026-10-14-fresh-downloads-design.md) e [plano/evidências](docs/superpowers/plans/2026-10-14-correlated-downloads.md).
5. Código e testes nas áreas citadas, README de recorder/runtime/worker/backend/frontend.
6. [Handoff anterior preservado](docs/archive/HANDOFF-before-consolidation-2026-10-14.md), `HANDOFF_NEXER_NEXT_CHAT.md`, `NEXER_WORK_HANDOFF_2026-10-09.md` e roadmaps apenas para recuperar histórico. Se houver divergência operacional, validar código/estado atual antes de agir.

Para retomar: “Leia HANDOFF.md, especialmente as seções 12 e 13, e os relatórios docs/2026-10-14-query-outcomes.md e docs/2026-10-14-step-review.md. O contrato de consultas já está implementado e testado. Confira branch/status e escolha o próximo avanço por evidência real do portal ou revisão guiada, preservando os limites SGIND.”

## 12. Continuação — consultas correlacionadas

Usuário aprovou spec e plano e autorizou execução completa (“Continue. Concedo permissão para tudo”). Implementação inline, com revisão independente ao final. Base desta continuação `3fb7062`; correções finais da implementação em `ede8813`, com documentação consolidada em commit posterior. Commits estão locais na mesma branch, ainda sem push. O checkout principal continua anterior e não recebeu cópia do código.

Nova ação `query`: baseline antes do clique, confirmação nova por atributo allowlisted, resultado com mesma geração e um único estado visível dentre dados/vazio/erro. Só dados permite prosseguir. Vazio é `QUERY_NO_DATA`, status `FAILED`, mensagem explícita; erro/ambiguidade/geração substituída interrompem. Sem retries nem novo status/migração. Cancelamento tipado do runtime chega ao worker; todos os itens cancelados mantêm execução cancelada.

Editor na etapa Campos converte clique simples elegível, preserva contexto e permite descartar edição/voltar ao clique. Mapa de alterações pendentes por editor impede liberar avanço ao salvar só um deles. Histórico apresenta códigos fixos, sem texto do site. Exceções internas não encadeiam dados privados. Correção incidental de snapshot de download tornou a contagem/verificação de linhas atômica, após regressão real de concorrência na suíte completa.

Verificação após correções da revisão: runtime161/151pass/10skip, recorder54/54, worker39/38pass/1skip, backend144/132pass/12skip, frontend86/86. Total484, 461 passaram,23 skips, sem falhas. tsc-b/Vite e QA visual Edge 1280/390 passaram. Evidências/limites e resultado da revisão ficam no relatório da entrega. Os três achados importantes e a perda de restauração exata do clique foram corrigidos com regressões. Sem achados adiados. Evidências locais ignoradas em temp/query-outcomes/.

O protocolo depende de um ID novo e não reutilizado fornecido pela aplicação e ligado à ação atual. Marcador global compartilhado não basta. Site deve declarar os estados terminais corretamente. Sem comprovação SGIND/IQOS, shadow DOM, navegação completa durante query, ramificação ou retomada. Não tratar testes sintéticos como aprovação corporativa.

Próximo escopo a escolher: inspecionar evidência real de confirmação de consulta/download no portal autorizado; ou reduzir configuração técnica na revisão por adaptadores/reparo pontual. Preservar método B e limites de dados/instalação. A feature genérica de consulta já existe; revisar os commits e relatório antes de começar qualquer nova implementação.

## 13. Continuação — revisão e reparo pontual

O usuário escolheu explicitamente “Revisar e corrigir etapas sem regravar tudo”. Implementado sobre `54004be`, no mesmo worktree/branch, com autorização ampla de execução já concedida. Ampliação delimitada da revisão existente, sem novo schema/backend/runtime.

A etapa Campos agora apresenta ações em ordem, parâmetro associado e aba/quantidade de frames. É possível corrigir seletor de alvo e destino de arrastar, mantendo IDs, ordem, frames e parâmetros. Espera automática imediatamente anterior, com mesmo seletor/frame, pode acompanhar a correção e passa a manual. Configuração inalterada não muda metadados. Downloads em coleção continuam especializados.

Rascunhos de correção não se perdem ao remover esperas anteriores ou sincronizar outra etapa. Pendências por editor impedem sair da revisão até aplicar/descartar. O alvo corrigido sobrevive à restauração de consulta para clique. Importação rejeita IDs inválidos/duplicados antes de renderizar. Os três achados da revisão independente foram reproduzidos em RED e corrigidos. Depois das correções passaram 101 testes frontend em 28 arquivos, tsc-b e Vite. QA visual Edge 1280/390 e replay de receita reparada pela UI passaram; original falhou no alvo antigo e corrigida concluiu as quatro etapas. Não foram repetidas suítes Python sem mudanças de produção nessas camadas. Evidências finais em docs/2026-10-14-step-review.md e temp/step-review/.

Limites: reparo por seletor, sem picker visual; frames/tipo/ordem não editados aqui; sem persistência do rascunho após reload; sem alteração da validação SGIND. A validação de formato do seletor na UI não comprova alvo único nem resultado de negócio.

Próximo avanço ainda não implementado: seleção visual assistida para o reparo, preservação de gravação incompleta após componente não suportado, ou inspeção autorizada do portal real. Revisar o relatório antes de escolher; não repetir as entregas de consultas ou revisão.


---

### Fonte: docs/2026-10-14-verificacao-handoff.md

# Verificação antes do commit/push — 14/10/2026

Branch: `codex/smart-recorder-handoff-2026-10-14`. Base: `a414983c85bae70e23837d4934609d9824207db2`, de `feat/nexer-smart-recorder`.

Execução nova imediatamente antes do commit, no worktree gerenciado `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`. Sem falhas. Código das duas entregas preservado; esta etapa consolidou documentos e não modificou comportamento.

| Suíte | Coletados | Passaram | Pulados | Resultado |
|---|---:|---:|---:|---|
| Runtime | 132 | 122 | 10 | exit 0 |
| Recorder | 54 | 54 | 0 | exit 0 |
| Worker | 34 | 33 | 1 | exit 0 |
| Backend completo | 143 | 131 | 12 | exit 0 |
| Frontend completo | 78 | 78 | 0 | exit 0 |
| **Total** | **441** | **418** | **23** | **Sem falhas** |

Frontend: 22 arquivos de testes. `tsc -b` e build Vite passaram, exit 0. Diff-check conferido antes do commit.

`NEXER_RUN_RECORDER_E2E=1` habilitou Edge sintético, incluindo contrato/concorrência de downloads e gravação integrada. Os demais opt-ins não foram habilitados: pilotos, fixture/login corporativo, lançamento/processos e cenários que exigem configuração própria. Não contar skips como validação SGIND/IQOS. Migrações impressas pelos testes ocorreram em bancos temporários de teste, não no banco real versionado.

## Comandos

Cwd: worktree da entrega. Python: ambiente existente no checkout principal. Todos os diretórios de módulos no PYTHONPATH apontaram ao worktree.

```powershell
$env:PYTHONPATH="$PWD/apps/runtime;$PWD/apps/runtime/tests;$PWD/apps/recorder;$PWD/apps/backend;$PWD/apps/backend/tests;$PWD/apps/worker"
$env:NEXER_RUN_RECORDER_E2E='1'
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' -m unittest discover -s apps/runtime/tests -q
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' -m unittest discover -s apps/recorder/tests -q
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' -m unittest discover -s apps/worker/tests -q
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' -m unittest discover -s apps/backend/tests -q
Set-Location apps/frontend
node node_modules/vitest/vitest.mjs run --pool=threads
node node_modules/typescript/bin/tsc -b
node node_modules/vite/bin/vite.js build
```

Logs brutos locais: `temp/handoff-2026-10-14/{runtime,recorder,worker,backend,frontend,typecheck,build}.log`, ignorados pelo Git. Resultados foram lidos e exit codes confirmados. Screenshots/fixtures das entregas anteriores continuam em `temp/correlated-downloads` e suas conclusões estão no relatório versionado.

## Alcance

Evidência de correlação: duas execuções independentes, central única reconstruída a cada 50 ms, mesmo nome e término B antes de A, bytes próprios corretos. Revisão independente e regressões de propriedade/cancelamento concluídas na entrega anterior.

Não comprova instalação atualizada, desempenho no computador corporativo, fluxo real SGIND/IQOS, suporte universal a componentes, retomada após restart ou semântica completa de consultas. Próximas prioridades e decisões estão em `HANDOFF.md`.

O usuário autorizou commit/push em nova branch, sem merge/PR. A confirmação do hash e da referência remota deve ser feita pelo Git após o push; este documento não antecipa resultado de rede nem grava seu próprio hash.


---

### Fonte: docs/2026-10-14-downloads-correlacionados.md

# Downloads vinculados à solicitação

Entrega de 14/10/2026, seguindo o método B: inteligência local e contrato genérico com adaptadores específicos quando necessários. Sem API de IA ou modelo local obrigatório.

## O que foi implementado

A receita agora pode registrar a central antes de gerar, emitir a solicitação uma única vez, aguardar sua confirmação e baixar somente o resultado identificado por essa confirmação. Duas execuções podem aguardar a mesma central e terminar fora de ordem, inclusive com arquivos de mesmo nome quando existe um identificador de trabalho.

- `snapshot_downloads`: registra em memória até 1000 identidades de uma central materializada, com raiz `collection.container` única e existente. Central vazia é válida; central ausente ou leitura incompleta interrompe antes de gerar.
- `request_download`: vincula a baseline, faz um clique esquerdo simples e aguarda confirmação única, visível e diferente da anterior. Confirmação anterior oculta também é considerada para impedir aceitação de trabalho antigo. Não há retry de geração.
- `download.generation`: referência à solicitação; exige a mesma coleção, frames e aba. Só seleciona identidade confirmada, ausente da baseline, com nome correspondente ao padrão. Ambiguidade interrompe sem baixar.
- O clique final verifica a identidade e o botão no mesmo bloco DOM, suportando reordenação e reconstrução frequente das linhas. Cancelamento e autorização são verificados durante prontidão, confirmação, seleção e espera pelo evento de download.
- Snapshot e identificador ficam fora de inputs, variáveis comuns, eventos, checkpoints e banco; são apagados antes e depois da execução, inclusive em falha/cancelamento.

Confirmação: texto com nome completo do arquivo ou atributo `data-job-id`, `data-report-id`, `data-download-id`. Com atributo na linha, a identidade precisa corresponder ao identificador confirmado. Identificadores aceitos têm até 256 caracteres ASCII: letras, números, ponto, hífen e sublinhado.

Na revisão do fluxo, **Vincular download à solicitação** permite selecionar a ação de geração, a raiz da central, a confirmação, a identidade na linha, a indicação de central compartilhada e o prazo por etapa (1–15 minutos, padrão 3). Alterações pendentes bloqueiam avanço até aplicar. Editar seletores mantém a baseline consistente; remover vínculo compartilhado por outro download é recusado.

Centrais declaradas `shared: true` exigem correlação para validar/publicar. Receitas antigas permanecem compatíveis; sua seleção pelo primeiro nome correspondente não comprova propriedade em uma central compartilhada. O histórico apresenta mensagens fixas para códigos conhecidos; exceções desconhecidas continuam mascaradas pelo worker.

## Verificação

- Runtime: 132 testes, 122 passaram e 10 opt-ins não habilitados foram pulados. Inclui 19 testes de contrato/Edge desta entrega, todos passaram.
- Gravador: 54 testes passaram, incluindo Edge sintético.
- Worker: 34 testes, 33 passaram e 1 opt-in foi pulado.
- Backend de gravação, versões e lotes: 14 testes, 13 passaram e 1 opt-in foi pulado.
- Frontend: suíte completa final com 77 testes passou. Após conferir a integração dos diagnósticos no histórico, os 2 testes dessa página passaram; o cenário novo reproduziu RED antes da correção. TypeScript (`tsc -b`) e build Vite passaram após a alteração final.
- Revisão independente identificou confirmação antiga oculta, geração após cancelamento e espera DOM sem limite. Regressões reproduziram as duas primeiras; os três achados foram corrigidos e a segunda revisão confirmou 19 testes e ausência de novos achados relevantes.
- Interface inspecionada em 1280 px e 390 px com API simulada, sem acesso a serviços reais.

O teste de concorrência usa servidor HTTP sintético, duas instâncias/contextos independentes do Edge, uma central única reconstruída a cada 50 ms e arquivos com o mesmo nome. B fica disponível primeiro; os bytes finais comprovam que A recebeu A e B recebeu B.

## Limites e próximos passos

O SGIND real ainda não tem adaptador de correlação validado. O formato `TodasOcorrencias-XXXXX.csv` informa tipo e nome, mas sozinho não identifica a solicitação. É necessário observar onde o portal fornece o nome completo/protocolo/identificador para a execução que gerou o relatório. Esse sinal não foi presumido.

O contrato genérico cobre coleções CSS DOM materializadas e links/botões HTML. Shadow DOM, paginação, virtualização ou controles que exigem eventos nativos confiáveis precisam de adaptador específico que comprove a abrangência e a correlação. O prazo termina no evento de download; salvar o arquivo mantém o transporte e as proteções existentes. Reinício do processo perde o vínculo e não retoma/reenvia geração automaticamente.

Próxima etapa de inteligência: contrato **consulta → resultado, erro ou ausência de dados**, com condições verificáveis e histórico claro. Em paralelo, obter evidência estrutural autorizada do SGIND para seu adaptador.

Código está no worktree `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`, branch `codex/smart-recorder-foundation`. Diffs da entrega anterior foram preservados. Não houve commit, push, merge, migração do banco existente ou execução corporativa.


---

### Fonte: docs/2026-10-14-query-outcomes.md

# Consultas com resultado correlacionado — 14/10/2026

O Nexer agora permite configurar, na revisão do fluxo, uma consulta que dispara uma única vez e distingue dados atuais, ausência de dados e erro. O resultado precisa apresentar o mesmo identificador novo confirmado pela solicitação. Visibilidade de tabela, spinner ou botão habilitado, sozinhos, não comprovam conclusão.

## Uso e comportamento

Na etapa Campos do cadastro guiado, abra “Consulta · ID” em um clique simples elegível. Configure confirmação, container do resultado, seletores dos três estados e prazo total. A identificação deve vir do próprio site/adaptador, nos atributos `data-query-id` ou `data-request-id`; seus valores não são guardados. Configurações pendentes bloqueiam o avanço. A navegação para fora da revisão é bloqueada enquanto houver edições pendentes. É possível descartar a edição ou voltar ao clique original durante a sessão, inclusive após ir à publicação e retornar; uma consulta importada volta a um clique simples.

- Dados correlacionados: segue para a próxima etapa.
- Ausência de dados: interrompe com `QUERY_NO_DATA`, exibindo “Consulta concluída sem dados; etapas seguintes não executadas.” O status atual é `FAILED`.
- Erro do site: interrompe com mensagem fixa, sem copiar o texto do portal.
- Resultado antigo: continua aguardando dentro do prazo.
- Resultado de outra geração, contexto trocado ou sinais conflitantes: interrompe.
- Cancelamento: chega ao worker e ao histórico como cancelado.

O clique não é repetido após timeout. O prazo inclui a preparação; varia de 1 a 900 segundos, com padrão de 180 segundos. A transferência de um relatório continua dependendo do contrato separado de downloads.

## Implementação

`query_contract.py` valida a ação declarativa; `query_execution.py` fixa documento/frame, observa confirmação com estado limitado, usa identificadores efêmeros e classifica o resultado em uma leitura DOM. A autorização ocorre antes da leitura DOM final de contexto e resultado; depois dela só são checados cancelamento, prazo e referência da página. O observador preserva evidência limitada de IDs intermediários usando registros de mutação, sem adotar silenciosamente a última geração. Mais de 1000 registros em um lote interrompem conservadoramente; só o atributo de identificação da confirmação é observado com valor anterior. Observadores e handles são liberados em todos os caminhos. Exceções inesperadas são reduzidas a código fixo e não encadeiam mensagens privadas do navegador.

Worker persiste apenas códigos de uma allowlist. A agregação de execução composta exclusivamente de itens cancelados agora mantém `CANCELLED`, mesmo sem outro flag de cancelamento no banco. Não há migração ou novo status.

A suíte revelou uma corrida preexistente no snapshot da central compartilhada: linhas eram lidas e depois contadas em outra chamada ao navegador. A verificação de completude agora acontece na mesma avaliação DOM, com regressão determinística e teste Edge de duas execuções concorrentes.

## Verificação

Verificação executada no worktree `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`, usando Python do checkout principal. Todos os módulos no PYTHONPATH apontaram ao worktree.

| Suíte | Coletados | Passaram | Pulados |
|---|---:|---:|---:|
| Runtime | 161 | 151 | 10 |
| Gravador | 54 | 54 | 0 |
| Worker | 39 | 38 | 1 |
| Backend | 144 | 132 | 12 |
| Frontend | 86 | 86 | 0 |
| Total | 484 | 461 | 23 |

Todas encerraram com exit 0. TypeScript `tsc -b` e build Vite passaram. `NEXER_RUN_RECORDER_E2E=1` habilitou os fixtures sintéticos Edge nas suítes pertinentes. Os 23 skips permanecem opt-ins de pilotos, processos/configurações e jornadas corporativas; não representam validação desses cenários.

Casos novos incluem geração nova com conteúdo idêntico, raiz reconstruída, confirmação síncrona/obsoleta/transitória, timeout, IDs inválidos, múltiplos sinais, duplicidade oculta, cancelamento, revogação, troca de documento/frame e privacidade. Backend publica e relê o contrato sem perda de campos. Worker foi exercitado com runner real e ação controlada para verificar persistência e interrupção. Frontend cobre dois editores de consulta mais download pendentes, reversão, publicação e histórico.

Testes iniciais foram observados em RED antes da implementação. Casos de aceitação adicionais do runtime foram expandidos após o primeiro GREEN; não se atribui RED individual a todos eles. Regressões de snapshot de download e de encadeamento de exceções tiveram seu próprio RED→GREEN.

QA visual do app compilado com API simulada em Edge: 1280×1000 e 390×844, campos/botões legíveis, edição bloqueando avanço, aplicação liberando avanço, sem overflow horizontal nem erro de página. Logs, script e screenshots locais estão preservados em `temp/query-outcomes/` (ignorados pelo Git).

## Limites

Primeiro contrato atende aplicações que fornecem uma identificação por solicitação verificável e não reutilizada. Um marcador global que pode refletir a consulta de outro usuário não cumpre o contrato. Não inventar contador local como substituto.

Sem validação SGIND/IQOS real. Sem navegação completa durante a consulta, shadow DOM, ramificações, retomada após restart ou repetição automática. Os estados terminais devem significar conclusão no site; o runtime não deduz isso a partir de mutações. Há janela nativa de dispatch de até 250 ms entre checagem e clique; não se promete cancelamento distribuído atômico. Avaliações JS síncronas locais não oferecem preempção de um navegador bloqueado.

Próximos avanços dependem de evidência dos componentes/portais reais e de revisão guiada mais acessível. Não houve alteração de executável, instalação, banco real ou gate corporativo.

Spec: `docs/superpowers/specs/2026-10-14-query-outcomes-design.md`. Plano e decisões de execução: `docs/superpowers/plans/2026-10-14-query-outcomes.md`. Revisão independente realizada sobre `3fb7062..477ff5d`, por agente separado (Astra). Encontrou três problemas importantes: autorização posterior ao último snapshot, perda de gerações intermediárias em mutações agrupadas e navegação que prendia edições pendentes. Todos foram reproduzidos em RED e corrigidos em uma passagem. A perda de opções originais do clique foi inicialmente classificada como menor, mas reclassificada como importante porque alterava o timeout configurado; uma asserção de igualdade direta confirmou o problema, e a regressão passou após conservar o snapshot na sessão do assistente. Correções registradas em `ede8813`. Sem achados adiados. A suíte completa foi repetida depois das correções; não houve segunda revisão independente.

## Decisões durante a execução

- Usar bookkeeping PowerShell no lugar dos scripts bash da skill: mantém ledger por plano e evidências, com custo de controle manual.
- Permitir `confirmation` de query no validador geral de downloads, mantendo as demais restrições: necessário para compartilhar o schema; regressões de download cobrem o risco de compatibilidade.
- Tornar snapshot de downloads atômico: corrige a comparação entre duas gerações da central; muda uma leitura preexistente e exige regressão de concorrência.
- Agregar todos os itens cancelados como execução cancelada, sem depender de outro flag do banco: evita diagnóstico de falha; conjuntos mistos preservam a regra anterior.
- Rejeitar duplicidades de sinais, inclusive ocultos, e lotes de mutação acima de 1000: decisão conservadora, que pode exigir adaptador em páginas muito ruidosas.
- Preservar as opções originais do clique em memória no pai do assistente: evita perder prazo ao navegar; adiciona estado de sessão, reiniciado ao importar/gravar outra receita.
- Preservar o worktree e a branch local, conforme escopo do plano; integração e publicação não foram executadas. SGIND/IQOS, dispatch nativo e navegador bloqueado mantêm os limites descritos acima.


A revisão automática de permissões bloqueou o comando que incluía remover o scratch do plano (mensagem: blocked by policy). A pasta temporária ignorada foi preservada; isso não interfere no código ou nos testes.


---

### Fonte: docs/2026-10-14-step-review.md

# Revisão e reparo pontual de etapas — 14/10/2026

Direção escolhida pelo usuário: “Revisar e corrigir etapas sem regravar tudo”. A autorização de execução completa da sessão foi mantida. Esta entrega amplia a revisão existente do cadastro guiado, sem criar um contrato de runtime, endpoint ou migração.

## Como usar

Depois de gravar ou importar uma receita, avance até Campos. A seção “Etapas do fluxo” mostra a ordem, o tipo da ação, o nome do parâmetro quando houver e o contexto de aba/frame. Abra uma etapa para editar o seletor do alvo. Em arrastar, também é possível corrigir o destino. Aplique ou descarte a correção antes de avançar ou voltar no assistente.

A correção conserva ID, ação, ordem, parâmetros, valores de referência, frames e configurações que não pertencem ao alvo. Downloads em central continuam em seu editor específico. Navegação, troca/fechamento de abas, snapshots e verificações de arquivo aparecem para conferência, sem edição genérica.

Se houver uma espera automática imediatamente anterior para o mesmo seletor e os mesmos frames, ela pode acompanhar a correção. Essa opção é explícita e inicia marcada. Ao atualizar o alvo, a espera passa a ser uma condição revisada manualmente. Esperas manuais, de outro alvo/frame ou não adjacentes permanecem intactas. Aplicar um seletor inalterado não modifica a origem da espera.

É possível corrigir o alvo de uma consulta e voltar à configuração original de clique sem perder esse reparo. Os campos técnicos de confirmação/resultado continuam nos editores especializados.

## Proteção das edições e importação

- Rascunhos de cada etapa usam o ID estável, de modo que remover uma sugestão anterior não remonta os editores seguintes.
- Uma sincronização de espera não sobrescreve um rascunho pendente naquele editor. O usuário ainda escolhe aplicar sua correção ou descartá-la em favor da configuração mais recente.
- Edições de etapas, consultas e downloads têm controle independente de pendências; salvar uma não libera as outras.
- IDs ausentes, numéricos, vazios ou duplicados e entradas nulas são rejeitados na importação antes de entrar na revisão. Uma importação inválida não substitui a receita anterior.
- A lista não exibe valores literais de ações, credenciais, conteúdo do site ou dados de uma execução. Usa somente tipo, identificador e metadados declarativos do parâmetro/contexto.

## Implementação

`apps/frontend/src/lib/stepReview.ts` descreve a sequência, valida identidades e aplica reparos sobre cópia da receita. `StepReviewEditor.tsx` mantém rascunhos locais por ID. `NewFlowPage.tsx` integra a revisão e as pendências; `QueryOutcomeEditor.tsx` conserva o seletor reparado ao restaurar um clique. Estilos seguem o editor e a navegação existentes.

## Verificação

Testes novos foram executados inicialmente em RED e depois GREEN, incluindo helper, componente e publicação pelo assistente. A revisão independente encontrou três problemas importantes: perda de rascunho por chave posicional, sobrescrita de espera pendente e importação com IDs inválidos. Os três foram reproduzidos por regressões antes da correção. Nenhum achado foi adiado.

Após as correções: **101 testes frontend passaram em 28 arquivos, sem falhas ou skips** (exit 0). `tsc -b` e build Vite passaram. Foram verificados helper, componente, importação, pendências entre editores, navegação no assistente e receita enviada à publicação.

QA do app compilado em Edge, API simulada, 1280×1000 e 390×844: sem overflow horizontal nem erro de página, controles legíveis, pendências bloqueando ida/volta. A correção feita pela interface foi coletada na requisição simulada de publicação e executada com o runtime real em uma página sintética. A receita original falhou na espera pelo alvo antigo; a corrigida concluiu as quatro etapas, preencheu o campo novo e acionou o botão. O canário digitado somente na execução não apareceu na receita publicada nem nos eventos.

A entrega alterou apenas frontend; as suítes backend/worker/recorder não foram repetidas. A execução Edge acima verificou a aceitação e o replay da receita editada pelo runtime existente. Logs, script e screenshots inspecionadas estão em `temp/step-review/` (ignorado pelo Git).

## Limites

O reparo inicial usa seletores informados pelo usuário; não inclui selecionar um elemento visualmente em um navegador conectado. A aplicação da edição verifica estrutura, tamanho e referências de variáveis, mas não comprova unicidade do elemento ou sucesso de negócio. Essas condições continuam sendo verificadas na execução.

Frames e ordem permanecem definidos pela gravação/receita. Mudar tipo de ação, reordenar, reparar frame ou configurar coleções/consultas completas usa as ferramentas específicas ou o Studio. O rascunho da revisão é de sessão; esta entrega não acrescenta persistência após fechar/recarregar a página nem recuperação de gravação interrompida.

Nenhum banco real, serviço ou executável foi alterado. A validação real de SGIND/IQOS continua pendente; os fixtures não a substituem. O worktree atualizado permanece em `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`, na branch `codex/smart-recorder-handoff-2026-10-14`.


---

### Fonte: docs/superpowers/specs/2026-10-14-visual-target-repair-design.md

# Seleção visual para reparo de alvo

Continuação da direção escolhida pelo usuário: corrigir etapas sem regravar tudo. Autorização ampla de execução mantida. Base `f1994d5`; worktree/branch de entrega existentes.

## Escopo e experiência

Um botão no editor de alvo abre uma sessão nova e efêmera do Edge no endereço inicial configurado. O usuário prepara manualmente a página da etapa, ativa “Selecionar alvo” e escolhe um elemento. O resultado preenche o rascunho do editor, sem aplicar automaticamente a receita. Aplicar/descartar e sincronização opcional da espera permanecem existentes.

Primeira versão: alvos na página principal, controles de texto, select nativo, checkbox, range/color e elementos de clique/espera/hover/scroll/press/drag (origem ou destino). Controles customizados choose/choose_radio e frames conservam edição manual. Abas/frames da receita não são alterados. Uma janela nova serve somente à aquisição do seletor; o fluxo não é reproduzido automaticamente.

## Arquitetura

Reutilizar lifecycle de sessões privadas do backend (owner, TTL300s, capacidade2/32, cancelamento e reap do subprocesso), com um hook de validação de configuração; comportamento de login/gravação permanece igual. Serviço específico recebe somente URL inicial normalizada e tipo de controle, retorna `{selector}` após validar gramática estrutural permitida. Endpoint local autenticado POST/GET/cancel, respostas no-store, sem banco.

Subprocesso `pick_target.py` usa navegador/contexto próprios, sem perfil persistente ou downloads. Política de origem igual ao gravador: somente origem configurada, redirects e websockets bloqueados, service workers/Worker desabilitados. Preparação permite navegação manual nessa origem; seleção bloqueia métodos diferentes de GET/HEAD. HTTPS/login/SSO não recebem novos gates ou permissões de rede.

Bundle inclui `selectors.js` existente e captura específica, instalada antes do JS da página. Interceptar eventos de ponteiro/mouse/teclado/submit em window capture durante seleção, antes dos handlers usuais. Toolbar também intercepta seus próprios eventos. Seleção aceita apenas clique confiável; a escolha não é um replay do fluxo. Não prometer proteção contra scripts hostis, requisições autônomas ou endpoints com efeitos em GET.

IDs/textos arbitrários, valores, URLs finais, HTML, screenshots e credenciais não são coletados. Seletores usam a política restrita já existente; Python e backend verificam a gramática/atributos permitidos antes de entregar metadados à UI. A origem/frame e unicidade são verificados no documento real. Rejeitar alvo de password, contexto diferente, iframe e canvas; não adivinhar o alvo.

## Estado e concorrência

PREPARING → SELECTING → DONE/FAILED/CANCELLED. Reentrar PREPARING permite ajustar a página. Ativação somente na página principal/origem correta e sem password visível. Documento fixado durante seleção; troca de documento cancela. Binding enfileira pedido; verificações Playwright ocorrem fora do callback. Limite de um pedido pendente evita filas ilimitadas.

Frontend faz polling cancelável por sessão. A seleção preenche somente o rascunho iniciado; edição posterior, descarte, fechamento, receita substituída ou resposta de uma sessão anterior invalidam seu resultado. Cancelar explicitamente também limpa/ignora o resultado antes de aguardar a rede. Falhas usam mensagens fixas e preservam o rascunho manual. Seleção em andamento bloqueia navegação até ser cancelada ou concluída. Remover uma etapa/unmount cancela sua sessão; retorno tardio é cancelado e nunca altera outra etapa.

## Aceitação

Testes RED/GREEN para configuração/gramática, owner/TTL/capacidade e protocolo sanitizado, interação Edge (seleção não aciona handlers usuais, não envia formulário, alvos privados não entram nos metadados, shadow aberto, rejeição de frame/controle errado), endpoints autenticados/no-store, UI (apenas rascunho, escolha antiga versus nova, editar/descartar/cancelar/unmount e preparação). Testes de regressão de login/gravação e editor existentes. Suítes pertinentes completas, TypeScript/build e QA desktop/mobile; registrar skips e limites separadamente.


---

### Fonte: docs/superpowers/plans/2026-10-14-visual-target-repair.md

# Visual Target Repair Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline and one fresh whole-change review. Track RED/GREEN and decisions in `temp/visual-target-repair/progress.md`.

**Goal:** Selecionar o novo alvo no Edge e revisar o reparo antes de aplicar.

**Architecture:** Sessão privada/backend subprocesso, bundle de seleção estrutural existente, UI associada ao rascunho. Contrato de receita não muda.

**Tech Stack:** Python/unittest, FastAPI, Playwright/Edge, React/TypeScript/Vitest.

**Spec:** `docs/superpowers/specs/2026-10-14-visual-target-repair-design.md`.

## Etapas

- [ ] Contrato puro em `apps/recorder/nexer_recorder/target_contract.py`: `validate_configuration(dict)->dict`, `validate_target(dict)->dict`, allowlist de erros, gramática de `selectors.js`. Testar URL/tipo/extra/seletores seguros/privados; RED antes de implementar.
- [ ] Bundle `target_capture.js`, `target_picker.py`, CLI `scripts/pick_target.py`: `target_script()->str`, `validate_selection(source,event,page,kind)->dict`, `pick_target(configuration,stop_event,on_phase,headless=False)->dict`. Testar real Edge com init bundle, prevenção de efeitos usuais e metadados seguros; validar seleção fora do callback e limpar contexto em finally.
- [ ] Backend: hook `_validate_configuration` preservando default de `LoginRecordings`; `TargetPickings.start_target(owner,url,kind)`, get/cancel, protocolo e erros allowlisted; router `target_pickings.py`, lifespan sweep/close. Configuração e resultados passam pelo contrato puro. Testar owner/TTL/capacidade/término/cancelamento/dados inesperados e API com manager falso; nenhum DB real.
- [ ] Frontend: API tipada, componente de seleção com guard de geração e cancelamento, integração ao editor existente com URL opcional. Resultado somente muda rascunho; novas edições invalidam seleção anterior. Testes de UI em RED antes da implementação, regressões do assistente.
- [ ] Suítes recorder/backend/frontend e regressões runtime/worker conforme imports; TypeScript/build e QA UI 1280/390. Logs em temp ignorado.
- [ ] Revisão independente do diff completo; reproduzir/corrigir achados relevantes e repetir suites afetadas. Documentar, atualizar HANDOFF e commit local. Sem merge/PR/instalação real.

## Restrições e revisão

Sem valores digitados, credenciais ou HTML no protocolo; sem ampliar origens/gates. Main-frame apenas; ação de seleção não executa a receita. Revisar especialmente: evento antes do clique, mudança de documento, resultado tardio após edição/cancelamento/unmount, owner/cancelamento de subprocesso, parser de seletores arbitrários e primeira ação após retorno de preparação.

Standing authorization (“Concedo permissão para tudo”) e direção selecionada pelo usuário usadas para prosseguir sem novos checkpoints de aprovação; decisões permanecem explícitas nesta spec e no relatório. A skill não amplia o escopo para uso corporativo real ou publicação.
