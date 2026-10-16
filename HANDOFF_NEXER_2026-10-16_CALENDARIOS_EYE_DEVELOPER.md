# HANDOFF NEXER — 16/10/2026
## RPA generalista, calendários semânticos, Eye Developer, motor inteligente e estabilização

> **Documento de continuidade e ponto de recuperação.** Consolidado a pedido do usuário ao encerrar a sessão. Os detalhes históricos ainda válidos constam de docs/HANDOFF_NEXER_RPA_2026-10-14.md e dos documentos específicos citados abaixo. **Este handoff não certifica que o RPA está homologado em SGIND/IQOS nem que todas as suítes estão verdes.** Preservar as evidências e as pendências.

### 0. Orientações imediatas para o próximo chat

1. Conectar ao Desktop Commander e confirmar o dispositivo Windows ESSPPEROE-0057D. Não presumir acesso à máquina se o dispositivo estiver offline.
2. Verificar primeiro git status --short --branch, git remote -v, git log -1, alterações pendentes e o resultado do push final deste handoff. **Nunca modificar master, nunca fazer git push --force, reset ou stash destrutivo.**
3. Checkout de desenvolvimento desta sessão: C:/Users/kis/Downloads/Nexer-dev-2026-10-16 (com .git). HEAD inicial a1773c2e1517b31e8b8622c0ddc019b421890bbc, branch inicial feat/nexer-guided-artifact-validation-2026-10-16. Repositório: https://github.com/hik4s/Nexer.git.
4. Exportação operacional anterior: C:/Users/kis/Downloads/Nexer-codex-nexer-stability-artifacts-2026-10-15 (SEM .git). A etapa anterior SI-05 a SI-09 foi sincronizada para ela com backup em temp/semantic-outcome-slice2-backup-2026-10-16 e API reiniciada, mas **a presente entrega de calendários + Eye Developer foi programada no checkout com Git, e não foi implantada automaticamente na exportação operacional**. Não confundir uma cópia da pasta com o branch real.
5. Segurança: nunca colocar senha do SGIND/IQOS em .env, código, receita, logs, trace, vídeo, testes, commit ou chat. Solicitar credenciais no frontend somente para a execução e descartá-las. Preservar SQLite local, arquivos privados e outros processos do usuário.
6. **Gate bloqueante atual: última suíte completa do runtime falhou em 3 testes.** Ver seção 7. Não chamar esta branch de release estável sem reteste e correção.

### 1. Produto, missão e decisões definitivas

O Nexer, antes RelatPy (renomeado em 08/10/2026), evoluiu de um extrator específico para **plataforma RPA de propósito geral local-first, desktop-first, distribuível a usuários comuns, profissionais e empresas**. O objetivo é permitir criar, gravar, revisar, parametrizar, executar, monitorar, reutilizar e distribuir automações web sem programação obrigatória. SGIND/IQOS são apenas **primeiro piloto corporativo autorizado**, não dependências para usuários externos.

Produto hoje: **aplicação web local híbrida** (React + FastAPI + Python worker + navegador Edge), não um site SaaS pronto nem um executável moderno autossuficiente. Direção: Nexer Desktop v1.0 com instalador real para Windows; Tauri + React + sidecar Python foi proposto, não decidido ou implementado. Nuvem opcional no futuro para coordenação/sincronização, não substitui worker local que acessa intranet, Edge e arquivos locais. Hospedagem Render não torna SGIND acessível fora da intranet.

Restrições: priorizar custo zero, sem servidor pago/LLM externo, com atenção futura a licenças e assinatura de binários; credenciais efêmeras; receitas estruturais declarativas, sem JS arbitrário do usuário; scripts gravam seletores e condições, não valores digitados; entradas configuradas em dashboard/lotes. No trabalho em IA, o usuário escolheu **Astra para arquitetura, brainstorm e microtarefas**, outro modelo/Codex/Copilot para codificação. Evidências reais antes de afirmar sucesso.

### 2. Arquitetura atual e funcionamento

- apps/frontend: React/TypeScript, Vite, dashboard de fluxos, perfis de login, lotes, Studio, gravação guiada, execução, artefatos, diagnósticos e nova aba Eye Developer.
- apps/backend: FastAPI em loopback, sessão de pareamento, autorização de origem e host, APIs de fluxos/versões/perfis/lotes/execuções/artefatos, SQLite + Alembic 0001-0007.
- apps/recorder e scripts/record_recipe.py: Playwright Edge, captação estrutural e semântica, associação de inputs, proteção de senha, navegação de SPA, coleta sem valores.
- apps/runtime: contrato recipe schema v1, validação de variáveis, ações/esperas, BrowserManager e Edge, correlação de consultas e downloads, checagens de artefatos, cancelamento.
- apps/worker: fila/worker e ciclo de execução, geralmente headless configurável por NEXER_BROWSER_HEADLESS em novo processo worker; na instalação anterior a API foi lançada como --api-only, logo **não iniciar jobs só porque API responde HTTP 200**.
- scripts/open_nexer.ps1, manage_nexer.ps1, prepare_frontend.ps1, Preparar-Frontend-Nexer.cmd e docs/INSTALACAO_DO_GITHUB.md: launcher/recuperação do frontend/instalação, ainda não instalador independente para toda máquina.
- Arquivos de exemplo, package-lock.json, requirements e migrações devem ir ao Git; .env local, bancos, screenshots, downloads, logs, node_modules e .venv não.

### 3. Trabalhos anteriores preservados na branch antes desta sessão

**Bootstrap/instalação e pareamento:** ver docs/2026-10-16-frontend-launcher-recovery.md e docs/INSTALACAO_DO_GITHUB.md. Correção de erro "Frontend dependencies are missing": npm ci via script de preparo; preflight evita reiniciar API quando Vite não existe; banco vazio na exportação migrado para Alembic 0007 sem apagar DB; launcher continua API-only. Cuidado com o executável antigo Streamlit/Tk e Nexer-Atualizado.exe, que não são pacote novo. Registro anterior da suíte de instalação: 20 testes aprovados.

**Gravador e calendários (primeiro incremento):** ver docs/2026-10-16-recorder-loading-calendar.md. Ícones de calendários PrimeNG passam a representar preenchimento do input editável, não clicks do popup. Popup de dias/meses não vira etapas. Resiliência em carregamento de SPA, cancelamento de requisições same-origin e transferência de abas. Primeiro incremento ainda classificava muitos inputs como text — corrigido no incremento presente.

**Semantic Intelligence Engine:** ver docs/2026-10-16-semantic-intelligence-engine-spec.md, semantic-intelligence-slice1.md e semantic-outcome-executable.md. Eventos de loading com evidência estrutural, observação busy e transição real pronto/não pronto, comando wait_for_outcome anexado após click com after_step_id, inclusive quando Parar gravação é acionado logo depois. Observador armado *antes* do clique no replay; timeout/cancelamento/erro sem retry cego. Editar/remover wait no Studio sem retirar click original. Não é detector mágico por palavra "Loading" e não cobre toda tabela SPA, iframe ou navegação que destrói documento.

**Artefatos:** mudanças antes já staged no Git, relacionadas a validação guiada e correlação de downloads, documentação docs/2026-10-16-validacao-guiada-arquivos.md, apps/frontend/src/lib/guidedFileValidation.ts, apps/runtime/download_generation.py, tests de deadlines e worker. Preservar essas mudanças e verificar sua compatibilidade com os waits. Um arquivo gerado/renomeado não significa necessariamente resultado correto: exigem-se correlação, SHA-256, acesso autorizado e, se necessário, validação de conteúdo.

### 4. IMPLEMENTADO NESTA SESSÃO — capturar máscara de data e calendário no Nexer

Motivação: na tela Preparar lote, os parâmetros aparecem como input_001 e input_002 com valores string, em vez de "Data Hora Início"/"Data Hora Fim" e seletor de data/hora. A interface precisa respeitar o formato que o site real espera.

- apps/recorder/nexer_recorder/capture.js: procura rótulos explícitos e próximos (.field-label, labels com for, aria). Limpa "*" decorativo. Em componente PrimeNG compatível, reconhece placeholder/data-date-format **estáticos** (não o valor digitado) e cria field.control = date ou datetime-local e field.site_format, por exemplo dd/MM/yyyy HH:mm:ss. Em rótulos estáticos de data/hora com máscara ausente pode propor formato padrão; **exige revisão humana quando inferência não é confiável**.
- apps/runtime/field_schema.py: nova chave opcional site_format sob lista permitida; valida combinação do controle date/datetime-local; rejeita strings arbitrárias e dados inseridos pelo usuário. Compatível com schema_version 1 e com receitas antigas.
- apps/frontend/src/lib/siteDates.ts (novo): conversão estrita de data/hora civil local entre widget HTML e máscara do site, sem mudança implícita de timezone. Formatos iniciais: dd/MM/yyyy, dd/MM/yyyy HH:mm, dd/MM/yyyy HH:mm:ss, yyyy-MM-dd, yyyy-MM-dd HH:mm:ss. Validação de dia/mês/ano, hora, minuto, segundo.
- apps/frontend/src/components/RecipeField.tsx: para field.site_format permitido, mostra input nativo type=date ou datetime-local com seletor; renderiza aviso de formato e converte onChange para texto do portal. Mantém string na variável de execução/receita, nunca salva o valor digitado na definição. Valor inválido recebe aviso, não conversão silenciosa. Formatos não configurados continuam com controles antigos.
- apps/frontend/src/components/DateFormatEditor.tsx (novo): seletor visual de máscara; conectado à etapa Campos em NewFlowPage.tsx e ao StudioPage.tsx para ajuste antes de publicar, sem VS Code ou edição manual de JSON. Pode optar pelo controle texto.
- apps/frontend/src/pages/NewBatchPage.tsx: limpa erro antigo "Preencha input_001" ao mudar entrada e revalida no submit.
- Testes: apps/recorder/tests/test_capture_edge.py (real Edge sintético), apps/frontend/src/components/RecipeField.test.tsx, DateFormatEditor.test.tsx, apps/runtime/tests/test_calendar_metadata.py.
- **A receita previamente publicada NÃO é reescrita nem reclassificada automaticamente.** Regravar, editar a nova versão ou importar rascunho, revisar data/máscara e publicar outra versão. Não inferir a máscara a partir de valores que o usuário digitou.
- Limites: campos readonly, portais com máscaras proprietárias, frameworks sem placeholder confiável, calendários com timezone/locale próprio e formatação dinâmica exigem adaptadores e teste real. Se o site só aceita texto via popup e proíbe preencher input, o calendário do Nexer pode não bastar.

### 5. IMPLEMENTADO NESTA SESSÃO — Eye Developer v0 (real, mas delimitado)

Área local protegida pelo login do Nexer, via /developer-eye em apps/frontend/src/App.tsx, no menu Ferramentas e ajustes.

Funções implementadas:
1. Estado da API, banco e workers; últimos jobs/executions com links e atualização automática opcional a cada 5 segundos, além de refresh manual. Reutiliza endpoints existentes e sessão local.
2. Laboratório de Edge **headless**: usuário informa URL válida e seletor CSS; POST /developer-eye/probe chama apps/backend/app/services/developer_eye.py; abre Edge isolado sem perfil corporativo/cookies, com bloqueio de downloads/service workers, procura seletor e retorna SOMENTE status FOUND, NOT_FOUND, AMBIGUOUS, PAGE_UNAVAILABLE, CROSS_ORIGIN_REDIRECT, quantidade 0/1/2+, visible, enabled, elapsed_ms. Sem leitura de texto ou conteúdo do campo, sem screenshots, no-store e sem persistência.
3. Inspeção **headed/visual** via endpoint /target-pickings existente: abre outra janela Edge para selecionar alvo por clique; permite cancelar, mostrar/copy seletor e usá-lo no teste. Essa janela é uma sessão SEPARADA, NÃO espelha uma execução real.
4. **Analisador de receitas publicadas** acrescentado após a primeira regressão completa: seleção do fluxo, exibição de nomes e tipos de campos não secretos, máscara site_format, nomes das ações em sequência e botão que chama teste/validação contratual do backend, sem executar site. Deve ser verificado nas regressões finais e não exibir conteúdo de campo, valores ou selectores sensíveis.
5. Rotas/arquivos: apps/backend/app/api/developer_eye.py, services/developer_eye.py, main.py; apps/frontend/src/pages/DeveloperEyePage.tsx e DeveloperEyePage.test.tsx; src/lib/api.ts e App.tsx.
6. Não há modo "ver a execução real ao vivo" nesta versão. Headless significa sem janela. Para ver uma execução efetiva, é necessário supervisão segura do worker e iniciar explicitamente NOVA sessão headed, com consentimento e isolamento, não tomar controle de sessão corporativa já em andamento.
7. Segurança: operação loopback com sessão e proteção de origem. Headless aceita uma URL autorizada sintaticamente em HTTPS ou HTTP localhost, mas deve ser futuramente restringida por política explícita de acesso a hosts/origens e quotas antes da distribuição para empresas. Não adicionar shell, JS remoto, terminal genérico ou dumps de DOM/cookies à interface.

### 6. Testes e evidências — estado REAL ao finalizar

| Suite/área | Resultado | Contexto |
|---|---|---|
| Backend completo | **167 tests, 13 skipped, exit 0** | 16/10 após alterações da API Eye Developer |
| Frontend completo (antes da última extensão do analisador) | **127/127 tests, 34 arquivos, exit 0** | incluiu gravador, Studio, lote, novas datas, Eye Developer original |
| TypeScript + Vite build produção (antes da última extensão do analisador) | **exit 0; 124 módulos Vite** | pós-editor de datas |
| Gravador/Edge completo após corrigir expectativa antiga | **83/83 tests, exit 0** | mudança esperada de rótulo "Data Hora Início *" para "Data Hora Início"; agora datetime-local |
| Contrato de máscara do runtime | **2/2 pass, exit 0** | aceita máscara válida e recusa combinação inválida |
| Endpoint Eye + Edge headless real fixture | **3/3 pass, exit 0** | autenticação, no-store, dados estruturais, URL inválida |
| UI direcionada (antes da extensão analisador) | **21/21 pass** | Studio, NewFlow, DateFormatEditor, RecipeField, Eye Developer |
| Runtime completo atual, opt-in Edge | **178 tests, 10 skipped, 3 FAIL, exit 1** | **pendência P0; NÃO está verde** |
| Novo analisador de receitas Eye e calendário (último ajuste) | **TypeScript exit 0; 12/12 tests UI direcionados, exit 0** | DeveloperEyePage 3, RecipeField 7, DateFormatEditor 2; não substitui suíte completa |
| SGIND/IQOS real | **NÃO testado** | depende de homologação/credenciais pelo usuário |
| Instalação moderna MSI/Tauri em máquina nova | **NÃO testada** | projeto ainda local web híbrido |

Erros exatos da última suíte de runtime:
- test_download_generation_edge.GenerationEdgeTests.test_two_real_contexts_share_central_and_finish_out_of_order: threads concorrentes permaneceram ativas, BrokenBarrierError no fixture HTTP; necessidade de isolar/sincronizar e provar correlação correta.
- test_query_execution_edge.QueryEdgeTests.test_deadline_covers_unready_button_without_click_retry: esperado QUERY_CONFIRMATION_TIMEOUT, recebido QUERY_CONTEXT_MISMATCH.
- test_query_execution_edge.QueryEdgeTests.test_empty_and_error_interrupt_following_action (subtest outcome=empty): esperado QUERY_NO_DATA, recebido QUERY_EXECUTION_FAILED.
- Também ocorreu ConnectionAbortedError [WinError 10053] na fixture local. Distinguir intermitência de regressão em runs isolados, não editar expectativas sem entender os estados/causas. Uma rodada anterior do runtime (incremento SI-05-09) estava verde com 176 testes/10 skipped, mas **não é evidência de aprovação da versão atual**.

### 7. Microtarefas e critérios de continuação

**P0 — estabilidade e validação antes da entrega operacional**
1. Fixar nova branch e push do snapshot com este handoff (feito somente quando commit e remote confirmarem). Verificar status final sem resíduos.
2. **Já confirmado após o último ajuste:** TypeScript exit 0 e 12/12 testes direcionados. Ainda se recomenda a suíte completa novamente antes de promover release.
3. Reproduzir isoladamente as três falhas do runtime e preservar logs estruturais RED; identificar se fixtures HTTP/Edge, monitoramento de deadline e exceções mascaradas são a causa; aplicar TDD sem relaxar asserts.
4. Rodar runtime completo novamente com Edge opt-in; comparar com recorder e backend. Não repetir clique de pesquisa nem permitir falso sucesso.
5. Rodar smoke em checkout limpo, com banco TEMPORÁRIO, branch isolada; não usar dados da exportação ativa nem credenciais.
6. Auditar superfície Eye Developer: validação de selector, allowed host/origin/SSRF, redirecionamento, quotas de subprocessos, timeouts de context, CSRF/origin middleware, no-store, controle de acesso e ausência de logs sensíveis.
7. Verificar roundtrip gravação (input data-hora) → receita schema v1 → publicação nova versão → Preparar lote → entrada calendário → Playwright fill com máscara → arquivo, em site sintético real.
8. Se autorizado, sincronizar SOMENTE arquivos necessários à exportação operacional, backup prévio e comparação SHA-256; conferir ociosidade de gravação/workers antes de restart; não iniciar worker automaticamente para testar.
9. Realizar piloto SGIND com operador: login manual/efêmero, datas novas, Pesquisar, wait real, download específico e conteúdo esperado, sem expor credenciais/relatório.
10. Não prometer suporte a calendários readonly até implementar adaptador de popup e teste E2E.

**P1 — Eye Developer funcional e produto generalista**
11. Ferramentas de diagnóstico de seletor com inspeção por overlay isolado, ambiguidade, alternativas estruturais, avaliação da estabilidade do locator em SPA, sem dados digitados.
12. Monitoramento em tempo real de um worker sob consentimento: modo headed opt-in por job novo, nunca acesso a sessão ativa, snapshots DOM sanitizados, pausar/continuar/cancelar com autorização.
13. Debugging de execução com breakpoint por etapa, estado de wait/timeout, timeline/redaction, erros legíveis e replay a partir de ponto seguro somente quando a ação não tiver efeitos duplicados.
14. Adaptadores RPA robustos de datepicker readonly, dropdown/PrimeNG, tabelas virtuais, iframes permitidos, shadow DOM aberto, inputs readonly controlados, resultado vazio/erro.
15. Studio no-code: renomear/reparametrizar passos, conferir metadados, validação pré-publicação, preview de calendário no lote e diferenciação de campos idênticos.
16. Portabilidade: instalador Windows independente sem Python/Node pré-instalados, atualização/desinstalação, dependências offline e documentação de primeiro uso.
17. Separar regras corporativas privadas do core público; revisar binários legados e possível banco SQLite em histórico Git antigo antes de promover/release público; nenhuma reescrita do histórico sem autorização.
18. Documentação de governança e licenças, ambiente restrito empresa, distribuição segura para terceiros, roadmap cloud opcional sem expor FastAPI em rede.

Referências com backlog detalhado: docs/2026-10-14-auditoria-microtarefas-primeiro-relatorio.md (**26 microtarefas históricas com critérios**), docs/HANDOFF_NEXER_RPA_2026-10-14.md (produto, fases e macro backlog), docs/2026-10-16-semantic-intelligence-engine-spec.md (SI-01+), docs/2026-10-16-calendarios-eye-developer.md (especificação implementada), docs/2026-10-16-semantic-outcome-executable.md (camada SI-05-09), docs/2026-10-16-validacao-guiada-arquivos.md (artefatos).

### 8. Comandos para continuar de forma segura

- Verificar repo: git status --short --branch; git remote -v; git log -1; git diff --check; git diff --cached --check.
- Frontend (na pasta apps/frontend): node node_modules/typescript/bin/tsc -b; node node_modules/vitest/vitest.mjs run; node node_modules/vite/bin/vite.js build.
- Python do ambiente disponível anteriormente: C:/Users/kis/Downloads/Nexer-portable-acceptance-2026-10-14/.venv/Scripts/python.exe. Não assumir que estará presente em máquina nova.
- PYTHONPATH para runtime + backend + recorder deve incluir apps/runtime, apps/runtime/tests, apps/backend, apps/backend/tests, apps/recorder, apps/recorder/tests e apps/worker.
- Backend: python -m unittest discover -s apps/backend/tests -q.
- Gravador com Edge: definir NEXER_RUN_RECORDER_E2E=1, python -m unittest discover -s apps/recorder/tests -q.
- Runtime com Edge: definir NEXER_RUN_RECORDER_E2E=1, python -m unittest discover -s apps/runtime/tests -q. Testar cada erro isoladamente antes de rerun integral.
- Verificações de Git antes do push: git ls-files -- .env data/nexer.db; git status --short; não git add -f de arquivos privados. A inspeção de arquivos em 16/10 não encontrou .env nem DB no índice; isso não substitui revisão de histórico e patches futuros.

### 9. Condições de entrega, privacidade e observações ao operador

- O checkout contendo o novo Eye Developer e o calendário **não foi automaticamente implantado** no aplicativo já aberto em 127.0.0.1:5173 nesta etapa. O frontend pode usar Vite do export antigo; commit no Git não muda o código da instalação operacional.
- Credenciais do SGIND/IQOS são fornecidas pelo usuário em campos efêmeros no momento de iniciar execução, não no .env da receita; perfil de login guarda seletores/configuração, nunca segredo.
- Usuário quer funcionamento efetivo, não placebo: botão de visualização headless abre navegador invisível separado; modo visual abre janela separada; análise de receitas chama validação real do backend; não afirmar breakpoint ou streaming do worker onde ainda não existe.
- A última verificação do analisador Eye (18:01) compilou sem erros e os 12 testes direcionados passaram. Atualizar a próxima conversa com branch, commit e hash remoto confirmados após o push. Não modificar master; não fazer deploy corporativo/execução real sem confirmação do usuário.

## 10. Status final

**Implementações codificadas no checkout; frontend/backend/gravador provaram passes nas suítes citadas; runtime integral com 3 falhas abertas; homologação real SGIND/IQOS e instalação distribuível continuam pendentes.**

A branch nova representa um SNAPSHOT DE DESENVOLVIMENTO, não release homologada. Próximo chat deve começar pelo gate P0 e preservar a arquitetura, as regras de segurança e a documentação consolidada.
