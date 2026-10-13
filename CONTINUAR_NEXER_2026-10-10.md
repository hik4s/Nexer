# Nexer — retomada em 10/10/2026

Complementa `CONTINUAR_NEXER_2026-10-09.md`. Arquitetura, opção B e gates corporativos continuam vigentes.

## Checkout desta sessão

- `C:\Users\hikas\Documents\ChatGPT\Nexer`, branch `feat/etapa1-foundation`.
- Pasta inicialmente tinha Git vazio. Recuperada de `https://github.com/hik4s/Nexer.git`, checkpoint `4f7e73c`.
- Ambiente `.venv` local criado com requisitos de `apps/worker/requirements.txt` e pacotes de sistema; Playwright instalado 1.62.0.
- Nenhum serviço real iniciado/reiniciado nem fila do usuário consumida. Todos os processos corporativos foram fixtures com DB/portas temporários e credenciais sintéticas.
- Alterações desta rodada ficam locais; nenhum commit/push feito.

## Correções e evidências

1. Fixture Edge antigo: três testes isolados passaram em 8,110s; falha/hang anterior não reproduzido. Suíte runtime inteira com `NEXER_RUN_CORPORATE_FIXTURE_E2E=1` também passou: 92 testes, skipped=1, 20,150s. Isso não prova ausência universal de falha intermitente.
2. Helper entre processos adaptado a `trusted_fixture` durante processamento/autenticação/guard/cleanup. Antes da adaptação, sucesso produziu `FAILED`; depois, download sintético validado.
3. Conexões SQLite dos testes fechadas com `contextlib.closing`: o context manager nativo de sqlite3 não fecha conexão. Antes: quatro erros WinError 32 ao remover bancos; depois: cleanup passou.
4. Cancelamento durante operação interrompida reproduziu execução `CANCELLED` com item `FAILED`. `_mark_failed` agora consulta cancelamento e cancela o item. E2E e regressão unitária capturam o defeito; teste unitário falhou sem a correção.
5. Quatro E2E opt-in entre processos passaram em 29,358s: sucesso/download, cancelamento, logout, reinício API. Verificam classificação, cleanup, arquivo e ausência de canários/capability em dump SQLite e saída capturada.
6. Revisão independente não identificou problemas acionáveis no diff. Acrescentada regressão unitária recomendada. Continua possível corrida entre leitura do cancelamento e gravação da falha; não foi introduzida nesta rodada e não há garantia de atomicidade nessa janela.

## Validação

- Backend padrão: 85 testes, OK, skipped=4.
- Worker padrão após regressão nova: 25 testes, OK, skipped=1.
- Runtime padrão: 92 testes, OK, skipped=9.
- Runtime com fixtures corporativos: 92 testes, OK, skipped=1.
- E2E entre processos: quatro testes, OK.
- `pip check`: sem requisitos quebrados. `git diff --check`: OK.
- Starlette ainda avisa sobre depreciação de httpx no TestClient.
- Frontend não alterado nem revalidado nesta rodada.

## Próximo trabalho

- Refinar concorrência/shutdown: canal lento, requisições simultâneas, término de threads/filhos e corrida de cancelamento.
- Validar launcher real em ambiente isolado sem expor pareamento/capability ou consumir fila real; helper não equivale ao launcher.
- Validar compatibilidade corporativa dos requests/assets/redirects de SGIND e IQOS com participação do usuário. Login real continua não validado.
- Formulário corporativo permanece desabilitado e gates fechados. Continuar etapas do handoff anterior; não considerar E2/E3 concluídos.

Usar `.\.venv\Scripts\python.exe` com `PYTHONPATH=apps\backend;apps\worker;apps\runtime`. Opt-ins: `NEXER_RUN_CORPORATE_FIXTURE_E2E=1` para runtime, `NEXER_RUN_CORPORATE_PROCESS_E2E=1` para teste backend de processos. Não habilitar esses overrides em produção.

## Segunda rodada — launcher e concorrência

- `scripts/run_local.py` usa `NEXER_PORT` tanto na API quanto no endereço do bootstrap worker. Três regressões de launcher foram observadas RED antes da implementação (porta fixa, fechamento precoce do pipe, ausência de parada por EOF).
- Pipe do worker permanece aberto após bootstrap com flush; EOF solicita parada por Event em `secure_main.py`. `main.py` entrega o Event ao processor. Autorizações corporativas rejeitam shutdown e o monitor fecha operação pendente; shutdown impede novas ações/itens e sucesso posterior. Parada do supervisor não se apresenta como cancelamento solicitado pelo usuário: execução interrompida fica FAILED, salvo cancelamento explícito.
- `stop_worker` espera até 90s pelo encerramento normal. Em timeout Windows, `taskkill /PID <filho criado pelo launcher> /T /F` encerra a árvore enquanto a raiz ainda existe. Não matar apenas Python primeiro. Em outros sistemas, fallback antigo terminate/kill permanece; esta rodada valida Windows.
- Job Object foi investigado, mas filhos sintéticos não ingressaram automaticamente no job nesta máquina. Protótipo e instrumentação removidos; não há Job Object em produção. Um filho sintético bloqueado sobreviveu à morte isolada do worker e foi limpo pelo teste; o novo teste demonstra que o fallback de `stop_worker` encerra esse filho.
- Revisão independente identificou o cenário ativo e o fallback Windows como lacuna importante; tratados com propagação de shutdown e teste de árvore bloqueada. Nenhum novo re-review foi solicitado após a correção.
- Novos testes de monitor: autorização lenta, quatro operações simultâneas interrompidas e três ciclos sem retenção de threads; 13 testes do monitor passaram. Não prometer limite rígido de parada para callback/canal que nunca retorna.
- Launcher isolado usa `run_local.main`, API, bootstrap, worker e Edge reais, banco/fila/downloads temporários. Apenas o controle de parada de uvicorn é substituído por stdin no helper. Não valida Ctrl+C interativo nem launcher com execução corporativa autenticada.
- Quatro testes launcher passaram em 19,246s: parada normal, perda abrupta do pai, morte forçada do worker/Edge ocioso e timeout do supervisor com filho sintético bloqueado. Checam processos observados, OFFLINE nas saídas normais, fila vazia, pareamento real em pipe de teste e gate corporativo 409. Morte forçada mantém registro ONLINE/sem stopped_at; não falsifica saída graciosa.
- Cenário novo entre processos: shutdown do worker durante ação com API viva. Primeira tentativa do helper ficou sem bootstrap por falta de flush; corrigido. Erro de close de pipe agora não interrompe cleanup dos demais subprocessos. API órfã da tentativa falha foi identificada pelo caminho exato do helper e encerrada pela árvore do PID da rodada. Teste isolado novo passou em 6,682s.
- Suítes padrão após correções: backend 90 testes/9 skips, worker 29/1 skip, runtime 95/9 skips, todas OK. Frontend continua sem mudanças/revalidação.
- `Resolve-DnsName indicadoresenergisaess.scl.corp` retornou nome DNS inexistente neste ambiente; compatibilidade SGIND/IQOS real depende de rede/VPN corporativa. Nenhuma credencial real foi solicitada, nenhum login real feito.
- Usuário confirmou que a validação corporativa será em OUTRO computador com acesso à rede corporativa. Não insistir em VPN nesta máquina nem abrir gates por causa dessa decisão.
- Repetições finais: cinco E2E API/worker OK em 35,981s; runtime completo com fixtures Edge habilitados 95 testes OK/skipped=1 em 19,203s; `pip check` e `git diff --check` OK.

Para launcher isolado: `NEXER_RUN_LAUNCHER_E2E=1`, executar `python -m unittest discover -s apps/backend/tests -p test_local_launcher_e2e.py -v` com o Python da `.venv`. Helpers são exclusivamente testes. Gates e campos UI continuam fechados.

Pendências: compatibilidade HTTP real SGIND/IQOS, corrida de cancelamento entre leitura e gravação, perda simultânea de supervisor e worker bloqueado, comportamento de fallback fora de Windows e login corporativo real acompanhado pelo usuário. O fallback testado depende de supervisor vivo; não há garantia de contenção universal para processos criados depois de snapshots ou para falha simultânea dos processos. Mudanças seguem locais, sem commit/push.

## Terceira rodada — gravador local sem dados

- Usuário confirmou: guardar locais e ações do Edge e gerar receita parametrizada; nunca guardar a data ou outro valor usado durante a gravação.
- `scripts/record_recipe.py` abre Edge em contexto novo e exporta rascunho JSON após fechar a janela. Apenas HTTP loopback, mesma origem, redirects bloqueados, sem downloads, persistência de sessão ou conexão WebSocket. Não habilita acesso corporativo.
- `apps/recorder/nexer_recorder/capture.js` coleta ações e seletores estruturais; não lê valores, texto, labels, URLs ou corpos de requests. Ignora campos sensíveis e formulários com senha. Data inicial/final, empresa e regional usam nomes semânticos permitidos; outros inputs recebem nomes genéricos. `compiler.py` rejeita eventos com valores/campos adicionais e exporta apenas placeholders e declarações obrigatórias sem defaults.
- Revisão independente encontrou submissão duplicada com Enter, controles input omitidos, selects sem nome semântico e contextos iframe/popup incorretos. Corrigidos: supressão do clique gerado pelo Enter, cliques nativos, parâmetro semântico em selects, rejeição visível de iframe/nova aba sem exportação parcial. Checkbox/radio gravam clique; o estado inicial precisa ser revisado. Calendários personalizados, shadow DOM, rota, download e autenticação ainda exigem trabalho manual.
- Studio usa validação compartilhada com runtime e revalida ao publicar; botão agora diz “Validar receita”. Isso é validação estrutural, não execução real. Declarações de variável precisam ser objetos; default do Studio corrigido.
- Verificação: gravador 7 testes OK, incluindo 3 Edge reais sintéticos (DOM, teclado/controles, CLI salvando JSON com servidor HTTP local). Teste CLI substitui somente modo visível por headless e interação humana por interação automática. Canários de data/texto/seleção/credenciais ausentes da receita. Backend 91 OK/9 skips, worker 29 OK/1 skip, runtime 96 OK/9 skips. Frontend 18 testes em 10 arquivos, typecheck e build passaram. Opt-ins corporativos anteriores não foram repetidos nesta rodada.
- `scripts/verify.ps1` inclui suite recorder. Instruções e fixture em `apps/recorder/README.md`. Sem commit/push; atualizar patch portátil com o estado desta rodada.

## Quarta rodada — cobertura de interações e formulário de parâmetros

- Usuário pediu ampliar para todas as ações da página mantendo as informações personalizadas na execução. Cobertura adicionada para cliques genéricos, duplo/triplo clique, botão direito/meio, contenteditable, selects múltiplos, listbox/option acessível, checkbox booleano, grupos radio por índice sem exportar names/values, range/color, hover de menus, drag/drop HTML e rolagem. Não afirmar cobertura universal de componentes de qualquer site.
- Iframes de mesma origem usam cadeia de seletores estruturais enviada pelo JS. Uma tentativa inicial de `frame_element()` dentro do binding síncrono travou Playwright; stack confirmado por faulthandler. Chamadas ao browser removidas desse callback. Dois processos sintéticos travados foram identificados pelo comando exato do teste e encerrados com suas árvores. Não tocaram filas/serviços/credenciais reais.
- Abas abertas pelo fluxo geram switch_tab e close_tab; fechamento é idempotente quando o próprio botão já fechou a aba. Registro de listeners reinstalado no DOMContentLoaded com AbortController para cobrir navegação de popup sem duplicar handlers. Hub interno de downloads do Edge desativado na CLI/fixture para não virar aba extra de execução.
- Downloads são declarados no clique do link a[download], ou por `--download-selector` repetível para botão conhecido. Nome de saída é input `download_file_001`. Downloads esperados/observados conferidos por página antes de salvar. Não converter último clique arbitrário quando chega download assíncrono; controles ambíguos exigem adaptação explícita.
- Revisão independente achou e motivou correções: grupos radio fundidos, checkbox com estados sucessivos compartilhados, download tardio alterando clique errado e duplo fechamento de popup. Regressões no compilador/runtime e E2E cobrem as correções. Checkbox não adjacente usa novo parâmetro por ocorrência; campos semânticos repetidos em contextos diferentes recebem sufixo. Texto admite limpeza explícita com allow_empty; chave ausente continua inválida.
- Nova execução carrega a versão publicada via GET existente e renderiza campos de parâmetros sem defaults da gravação. Usa datas existentes, Empresa/Regional/Endereço inicial, Sim/Não booleano, números e listas JSON. Entradas fornecidas pertencem à execução, nunca ao JSON gravado. Tipos/obrigatoriedade tratados antes de enviar. Credenciais gerenciadas continuam bloqueadas.
- CI e verify.ps1 incluem suite recorder. Fixture expandida possui iframe, popup com botão que fecha a própria aba, controles, listbox e CSV fictício.
- Teste CLI real grava datas/empresa/seleções/textos sintéticos, exporta JSON sem canários e roda RecipeRunner com dados diferentes; verifica datas, empresa/regional, checkbox, radio, range/color, editor, listbox, iframe, conteúdo novo da popup antes de fechar e download com nome novo. Outro Edge testa shadow DOM aberto, duplo clique, hover, drag/drop e rolagem. Nada disso valida SGIND/IQOS real.
- Verificação final desta rodada: gravador 12 OK (4 Edge), runtime 101 OK/1 skip com fixtures corporativas sintéticas opt-in, backend 91 OK/9 skips e worker 29 OK/1 skip; frontend suite 19 OK em 10 arquivos, teste de parâmetros atualizado 2 OK e build final OK. pip check e git diff --check OK. Falha temporária de build por mock incompleto foi corrigida, sem alteração de dependências.
- Limites: HTTP loopback/mesma origem, sem login real; barra de endereço/controles Edge, shadow DOM fechado, calendários customizados sem campo editável, canvas, uploads e componentes sem semântica exigem adaptação. Canvas/upload/readonly/contexto não suportado detectado impede exportação. Datas nativas estão cobertas. Não habilitar gates corporativos antes da validação no outro computador.
- Sem commit/push. Patch portátil atualizado em temp/NEXER_PATCH_2026-10-10.patch incluindo todas as rodadas locais.


## Quinta rodada — campos equivalentes e catálogos ao preparar execução

- Usuário confirmou: carregar opções do site ao preparar execução e preservar tipo/regras dos campos, sem copiar aparência. Dashboard ganhou seção Relatórios registrados com relatórios publicados e formulário de preparação no próprio card. Nova execução reutiliza o mesmo formulário; entradas avançadas ficam recolhidas.
- Contrato `variables.<nome>.field` validado pelo runtime/Studio: control, required, min/max/step (incluindo limites temporais), min_length/max_length, pattern, input_mode e rows. Gravador faz snapshot de atributos antes do preenchimento; não captura valor/default/checked/selected/opções. Campos obrigatórios não recebem allow_empty. Metadados de outros formatos são rejeitados.
- `RecipeField` renderiza data/hora/mês/semana/datetime-local, número, email/url/tel/search/texto, textarea, checkbox/radio, select/multiselect, range/color. Períodos aplicam limites/step. Escolhas não são preenchidas com a seleção antiga; checkbox indefinido, multiselect vazio e valores nativos iniciais de color/range exigem decisão explícita. Receitas antigas sem field mantêm formulário genérico compatível.
- POST `/automations/{id}/versions/{version}/input-options` exige versão atual publicada, usa sessão Edge temporária e devolve apenas catálogos em memória com Cache-Control no-store. Não cria execução nem altera receita/banco. SGIND/IQOS/credenciais gerenciadas são rejeitados; HTTP loopback sem usuário/senha/query/fragment, mesma origem GET/HEAD, sem redirects/WebSocket/downloads/storage persistente. Trata falhas com códigos constantes sem conteúdo da página.
- Aplicação de filtros nativos fornecidos nesta preparação: fill/select/check/set_value/radio. Escolha de empresa invalida catálogos/seleções posteriores no dashboard; datas e filtros de texto invalidam catálogos. Responses pendentes de uma preparação anterior são descartadas por geração. Usuário clica Carregar opções do site novamente para consultar dependências.
- Sincronização acompanha timers/fetch/XHR sem guardar conteúdos, espera DOM estável em cada documento/frame, rejeita atualização pendente acima de 3s. setTimeout string permanece nativo para respeitar CSP, com limpeza separada do contador. Contexto/browser encerrados sempre, sem reutilizar sessão do usuário.
- Revisão independente encontrou: campos obrigatórios vazios, limites temporais perdidos, seleção múltipla vazia implícita, respostas antes de atualização assíncrona, falta de espera no iframe e timer string pendente para sempre. Corrigidos com regressões; revisão final confirmou 3 testes do leitor de opções no Edge, sem achados restantes nesses resíduos.
- Teste HTTP/Edge usa empresa/regional fictícias, atualização por timer1600ms, stale regional descartada, atualização5000ms rejeitada, iframe com timer string1600ms e receita intacta. Endpoint testa publicação, gate corporativo fechado, no-store, ausência de execução/banco alterado. Canary de erro do browser não aparece no retorno. Screenshot desktop/mobile de build em sessão sintética: temp/dashboard-report-desktop.png e temp/dashboard-report-mobile.png; inspecionados, sem overflow horizontal.
- Verificação: backend 95 OK/9 skips com NEXER_RUN_REPORT_OPTIONS_E2E=1; gravador 14 OK incluindo 4 Edge com NEXER_RUN_RECORDER_E2E=1; runtime101 OK/9 skips e worker29 OK/1 skip. Frontend24 testes/12 arquivos, build OK. pip check/git diff --check OK. Uma execução inicial do backend omitiu apps/worker do PYTHONPATH; repetida com paths corretos. Mock da lista publicada no teste de logout atualizado após incluir seção de relatórios.
- Limites: leitor consulta formulário inicial/iframes já presentes; não reproduz cliques de navegação, submissão, abertura de popup ou menus que exigem adaptador. Máscaras/regras implementadas só em JS não são copiadas automaticamente. Timers permanentes/carregamentos acima do prazo ficam indisponíveis. Catálogos reais corporativos continuam pendentes no outro computador; não abrir gates. Campos gravados antes desta rodada precisam de nova gravação ou metadados revisados para obter controles específicos.
- Instruções atualizadas em apps/recorder/README.md. Sem commit/push. Atualizar patch portátil temp/NEXER_PATCH_2026-10-10.patch para incluir todas as rodadas.
