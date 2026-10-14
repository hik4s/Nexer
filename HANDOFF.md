# HANDOFF — Nexer: estado consolidado para o próximo chat

Atualizado em 14/10/2026. Este é o ponto de entrada da continuação. Leia antes de modificar o código. Os documentos antigos são contexto histórico; não comprovam instalação ou validação corporativa atual.

**Continuação mais recente:** o contrato de consultas com resultado correlacionado foi implementado neste mesmo worktree/branch. Leia a seção 12 e `docs/2026-10-14-query-outcomes.md`; a prioridade de desenhar esse contrato, descrita abaixo, já foi atendida. Não reimplementar as quatro tarefas do plano.

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

Para retomar: “Leia HANDOFF.md, especialmente a seção 12, e o relatório docs/2026-10-14-query-outcomes.md. O contrato de consultas já está implementado e testado. Confira branch/status e escolha o próximo avanço por evidência real do portal ou revisão guiada, preservando os limites SGIND.”

## 12. Continuação — consultas correlacionadas

Usuário aprovou spec e plano e autorizou execução completa (“Continue. Concedo permissão para tudo”). Implementação inline, com revisão independente ao final. Base desta continuação `3fb7062`; correções finais da implementação em `ede8813`, com documentação consolidada em commit posterior. Commits estão locais na mesma branch, ainda sem push. O checkout principal continua anterior e não recebeu cópia do código.

Nova ação `query`: baseline antes do clique, confirmação nova por atributo allowlisted, resultado com mesma geração e um único estado visível dentre dados/vazio/erro. Só dados permite prosseguir. Vazio é `QUERY_NO_DATA`, status `FAILED`, mensagem explícita; erro/ambiguidade/geração substituída interrompem. Sem retries nem novo status/migração. Cancelamento tipado do runtime chega ao worker; todos os itens cancelados mantêm execução cancelada.

Editor na etapa Campos converte clique simples elegível, preserva contexto e permite descartar edição/voltar ao clique. Mapa de alterações pendentes por editor impede liberar avanço ao salvar só um deles. Histórico apresenta códigos fixos, sem texto do site. Exceções internas não encadeiam dados privados. Correção incidental de snapshot de download tornou a contagem/verificação de linhas atômica, após regressão real de concorrência na suíte completa.

Verificação após correções da revisão: runtime161/151pass/10skip, recorder54/54, worker39/38pass/1skip, backend144/132pass/12skip, frontend86/86. Total484, 461 passaram,23 skips, sem falhas. tsc-b/Vite e QA visual Edge 1280/390 passaram. Evidências/limites e resultado da revisão ficam no relatório da entrega. Os três achados importantes e a perda de restauração exata do clique foram corrigidos com regressões. Sem achados adiados. Evidências locais ignoradas em temp/query-outcomes/.

O protocolo depende de um ID novo e não reutilizado fornecido pela aplicação e ligado à ação atual. Marcador global compartilhado não basta. Site deve declarar os estados terminais corretamente. Sem comprovação SGIND/IQOS, shadow DOM, navegação completa durante query, ramificação ou retomada. Não tratar testes sintéticos como aprovação corporativa.

Próximo escopo a escolher: inspecionar evidência real de confirmação de consulta/download no portal autorizado; ou reduzir configuração técnica na revisão por adaptadores/reparo pontual. Preservar método B e limites de dados/instalação. A feature genérica de consulta já existe; revisar os commits e relatório antes de começar qualquer nova implementação.
