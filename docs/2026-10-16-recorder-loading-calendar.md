# Nexer — estabilidade da gravação durante Pesquisar e parametrização por calendário (16/10/2026)

## Origem e segurança

- Usuário reportou: após clicar **Pesquisar** no SGIND durante gravação, o Edge/fluxo encerrou com erro de comunicação; em dois campos **Data Hora Início** e **Data Hora Fim**, o clique no ícone do calendário não gerava parâmetro reutilizável.
- Reproduzido e corrigido **com fixtures sintéticas de Edge**, sem acessar SGIND/IQOS reais e sem capturar, salvar ou trafegar credenciais/datas de usuário.
- Referência Git: `hik4s/Nexer`, base `codex/nexer-stability-artifacts-2026-10-15`, commit `a1773c2e1517b31e8b8622c0ddc019b421890bbc`.
- Checkout de desenvolvimento: `C:/Users/kis/Downloads/Nexer-dev-2026-10-16`, branch **local** `feat/nexer-guided-artifact-validation-2026-10-16`; já continha modificações preparadas para validação guiada e recuperação do launcher, sem commit/push. Não alterar `master`.
- Exportação em uso: `C:/Users/kis/Downloads/Nexer-codex-nexer-stability-artifacts-2026-10-15`, **sem .git**. Foi preservada e atualizada apenas nos arquivos listados abaixo, com backups locais.

## Implementações

### 1. Captura de calendário do site (`apps/recorder/nexer_recorder/capture.js`)
- O clique em um botão do calendário PrimeNG (`p-calendar`, `p-datepicker`, `.p-calendar`, `.p-datepicker`) é associado a um único `input` editável do respectivo componente.
- O evento enviado ao compilador é **`fill` no seletor do input**, criando um parâmetro de execução reutilizável com rótulo do campo. Não é enviado um `click` que dependa de o painel estar aberto no próximo replay.
- Suporte às variantes de gatilho `.p-datepicker-trigger`, `.p-datepicker-dropdown`, `data-pc-section=dropdown/trigger` e ícones PrimeNG comuns.
- Cliques de navegação no calendário/painel de dia, mês, ano e hora não viram etapas extras na receita; o evento `change` posterior do input é deduplicado pelo compilador.
- Rótulo próximo do campo é identificado estruturalmente quando não há `label for` associado.
- **Privacidade:** nem o valor original, nem texto digitado, nem o nome/data selecionados são persistidos na receita. Para inputs `type=text` com máscara PrimeNG, o campo aparece como texto parametrizado; na execução, informar data/hora no formato aceito pelo site (por exemplo, `dd/MM/yyyy HH:mm`).
- **Limite relevante:** datepickers `readonly` e componentes proprietários sem um único input editável não são convertidos automaticamente em preenchimento executável; exigem um adaptador de calendário específico e homologação. Não interpretar este incremento como suporte a todos os datepickers.

### 2. Resiliência durante tela de carregamento (`scripts/record_recipe.py`)
- Em solicitações same-origin canceladas pela própria página durante navegação/carregamento, `route.fetch/fulfill` é tratado com **abort seguro** em vez de propagar a exceção para o dispatcher; redirecionamentos e origens externas continuam bloqueados como antes.
- A entrada na página usa `wait_until=domcontentloaded`, evitando esperar por carregamento completo de recursos longos para instalar o gravador.
- Interrupções transitórias conhecidas do Playwright (troca de contexto, frame destacado, navegação interrompida) são toleradas enquanto a página continua aberta, com limite de tentativas (~30s); falhas não reconhecidas e fechamento definitivo não são silenciosamente ignorados.
- A monitoração continua usando uma aba viva do contexto quando a aba inicial é fechada mas outra aba permitida segue aberta; `stop` e `finish` permanecem os únicos comandos explícitos de controle.
- O gravador não realiza replay de clique em Pesquisar, não modifica o site e não relaxa as restrições de origem/credenciais.

## Evidências de testes realizados

1. **RED** calendário Edge: clique original era `click` no ícone, seguida de cliques de navegação; nenhuma variável de data gerada. **GREEN** após correção: cliques no ícone geram dois `fill` (início/fim), navegação em popup ignorada e execução de replay com valores novos. O teste de `apps/recorder/tests/test_capture_edge.py` passou.
2. **RED** navegação: um erro Playwright `Execution context was destroyed` interrompia a gravação com `RECORDER_BROWSER_FAILED`. **GREEN**: testes de interrupção transitória e falha não recuperável passaram.
3. Simulação de solicitações canceladas, corrida `route.fulfill` e recurso cross-origin: 4 testes do arquivo `test_record_recipe.py` passaram; requisição não permitida é abortada e não enviada para fora.
4. **Suíte completa do gravador com Edge habilitado:** 67 testes, 67 passaram, exit 0 (antes da última pequena extensão de tratamento de `route.fulfill`; testes direcionados após extensão: 4/4, exit 0).
5. `node --check capture.js` e `py_compile record_recipe.py`: exit 0; teste específico do calendário foi repetido após extensão de seletores e passou.
6. A exportação recebeu cópias verificadas por SHA-256 dos scripts e testes; os scripts anteriores foram guardados em `temp/recorder-loading-calendar-backup-2026-10-16/`.
7. Nenhuma operação de login, pesquisa ou download em SGIND/IQOS real foi realizada nesta sessão; o problema reportado pelo usuário precisa ser validado manualmente no fluxo corporativo.

## Como validar visualmente na máquina

1. Abra o Nexer **já recuperado**, `http://127.0.0.1:5173/`, e inicie **nova** gravação (a sessão anterior com erro não pode ser reaberta).
2. No Edge corporativo, conclua o login manual e inicie a gravação. Abra os calendários **Data Hora Início** e **Data Hora Fim**, escolha datas normalmente e clique em **Pesquisar**.
3. Aguarde a tela de carregamento e o resultado; quando a janela de gravação continuar ativa, encerre com **Parar gravação**.
4. Em **Campos/Publicar**, verifique que existem dois parâmetros de entrada identificáveis pelo rótulo de data/hora. Na execução seguinte, altere-os para novas datas no padrão aceito pelo portal.
5. Se o fluxo voltar a encerrar ao pesquisar, registrar **qual ação antecedeu o fechamento**, se o Edge permaneceu aberto, e a mensagem/status do erro. Não compartilhar credenciais, cookies ou relatórios privados. Investigar especialmente restrições de recursos externos do site e componentes customizados.

## Pendências e próximos gates

- A execução em SGIND/IQOS é **não homologada**, inclusive o suporte real ao calendário mostrado nas capturas. Se readonly, escrever adaptador de controle visível específico, sem tentar alterar atributos de segurança do site.
- A política de acesso somente à origem inicial permanece vigente. Sistemas que requerem recursos de outras origens devem usar uma lista de permissões explícitas e auditadas, não liberação genérica.
- Novas gravações carregam o código atualizado via subprocesso; **não é necessário reiniciar a API nem executar trabalhadores da fila**. Preservar as configurações de credenciais temporárias.
- Alterações no checkout local **ainda sem commit/push** e alterações anteriores preservadas; para publicar, revisar branch, diff e arquivos sensíveis antes de criar commit em branch separada.
