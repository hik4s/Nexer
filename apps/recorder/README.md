# Gravador Nexer — ações e parâmetros de execução

Grava locais das ações no Edge e gera um rascunho de receita v1. Lê rótulos estruturais dos campos para nomeá-los; não lê nem envia valores preenchidos, opção selecionada, nomes/conteúdo de arquivos gravados, cookies, screenshots ou conteúdo de requests. O coletor Python rejeita eventos com `value` ou campos fora do contrato. Formulários com senha e campos identificados como autenticação/segredo são ignorados.

Exemplo: preencher o input `period_start` gera `fill` no seletor `#period_start`, com `value: "{{period_start}}"` e declaração obrigatória do parâmetro. Nenhuma data da gravação é guardada. O runtime recebe a data nova na execução.

## Experimentar sem rede corporativa

Na raiz do checkout, em um terminal:

```powershell
.\.venv\Scripts\python.exe -m http.server 8765 --bind 127.0.0.1 --directory apps/recorder/fixtures
```

Em outro terminal, usando um nome de arquivo que ainda não exista:

```powershell
.\.venv\Scripts\python.exe scripts/record_recipe.py --url http://127.0.0.1:8765/report.html --output temp/receita-gravada.json --name "Relatório de teste"
```

Use apenas valores fictícios. Feche a janela do Edge para salvar o rascunho. Revise o JSON no Studio e salve como uma nova versão. A URL de gravação não é exportada: forneça `base_url` como parâmetro da execução. Inputs e selects com IDs semânticos `period_start`, `period_end`, `company`, `regional` recebem esses nomes; demais preenchimentos recebem `input_001` etc. Renomeie declaração e placeholder juntos durante a revisão.

## O que é capturado

- Cliques em elementos da página, inclusive fora de botões, duplo/triplo clique, botão direito e botão do meio.
- Preenchimentos de texto, data inicial/final, empresa, textarea e contenteditable; alterações de texto são agrupadas em uma ação com placeholder. Teclas digitadas e atalhos de edição não são guardados: o conteúdo final é fornecido na execução.
- Seleção simples/múltipla e listas personalizadas com roles listbox/option. As opções não são lidas durante a gravação. Seleção múltipla recebe um seletor de múltiplas opções no dashboard; receitas antigas sem metadados ainda usam lista JSON. Internamente o runtime recebe uma lista de valores; lista personalizada recebe o nome acessível da opção desejada, informado na execução.
- Checkbox recebe um controle de marcação no dashboard, com decisão explícita de marcar ou desmarcar; receitas antigas sem metadados mantêm Sim/Não. Ocorrências separadas por outras ações recebem parâmetros diferentes para permitir marcar e desmarcar ao longo do fluxo. Radio recebe o valor da opção desejada na execução; grupos nativos são distinguidos por índice estrutural, sem exportar nomes ou valores.
- Range e color recebem valores personalizados; não exportam posição/valor selecionado na gravação.
- Rolagem, hover em menus com aria-haspopup/menuitem e arrastar/soltar HTML nativo; não captura conteúdos transportados pelo drag.
- Iframes de mesma origem, shadow DOM aberto e troca/fechamento de abas abertas pelo fluxo da página. Fechar a janela principal encerra a gravação.
- Links com atributo download e controles chamados Baixar/Download geram passo download. Quando estão numa coleção identificável, registram seletores e um parâmetro de padrão; o nome atual do arquivo será obtido somente na execução. Downloads individuais mantêm o parâmetro de nome do arquivo salvo. Para um botão de exportação sem semântica reconhecida, informe `--download-selector "#export"`; a opção pode ser repetida. Um download não declarado ou não observado impede salvar o rascunho. Não captura URL/nome sugerido/conteúdo do download na gravação.

## Personalizar e executar

Em **Criar fluxo**, inicie a gravação, faça as ações na página e use **Parar gravação** na toolbar do Edge. A página de revisão de campos abre somente após a conclusão, com os nomes obtidos de label/aria-labelledby/aria-label/legend. O botão não entra na receita. Somente campos efetivamente alterados geram parâmetros; nenhuma seleção/data/texto usado na gravação vira valor padrão.

Downloads em tabelas/listas identificáveis registram uma `collection` com seletores `rows`, `name`, `button` e `pattern`. O padrão é uma entrada da nova execução, por exemplo `Relatorio_*.xlsx` (`*` representa qualquer sequência e `?` um caractere; comparação diferencia maiúsculas/minúsculas). O runtime percorre linhas visíveis na ordem do DOM e baixa o primeiro nome correspondente, conservando `suggested_filename` atual do site. Não ordena por data: a central deve listar os mais recentes primeiro. Sem correspondência, aguarda até o timeout e falha sem baixar outro arquivo. Diretórios são separados por execução. Não sobrescreve um arquivo de mesmo nome já salvo nesta execução.

Revise os seletores de nome/linhas/botão no cadastro após gravar. Tabelas usam inicialmente a primeira coluna como nome; listas removem textos dos controles de ação. Se a central usa outra estrutura ou a linha inclui status junto ao nome, indique o seletor específico do nome no editor. Botões/links com nome acessível começando por Baixar/Download são reconhecidos; controles sem essa semântica exigem `--download-selector` ou adaptação. A página central do site é capturada; a interface de downloads do próprio Edge não é instrumentada.

1. No Studio, selecione ou crie a automação e use **Importar gravação JSON** para abrir o arquivo gerado (até 1 MB). Em **Campos no dashboard**, edite os nomes exibidos sem alterar identificadores/placeholders, tipos ou regras. O editor JSON avançado permanece disponível para revisar seletores. Salve uma nova versão; alterações tornam necessária nova validação/publicação.
2. Valide a estrutura e publique a versão.
3. No **Dashboard → Relatórios registrados**, selecione o relatório publicado. O formulário também está disponível em **Nova execução**. Os campos aparecem sem valores da gravação, usando o tipo e as regras declaradas: datas/horários, números, email, texto, textarea, listas, radio, checkbox, range e color.
4. Informe o endereço inicial e os filtros disponíveis; clique em **Carregar opções do site**. As listas simples/múltiplas e radio mostram as escolhas atuais da página. Ao mudar uma escolha, as listas posteriores são limpas e exigem nova consulta. Informe período inicial/final e um nome novo para cada arquivo baixado. Campos opcionais podem ser explicitamente esvaziados quando a declaração contém allow_empty; parâmetro ausente continua inválido. Checkbox e lista múltipla vazia exigem decisão explícita.
5. Crie a execução. O worker entrega as novas entradas ao runtime. **Modo de teste** simula as ações; desmarque para executar de fato a fixture local.

A gravação conserva apenas metadados HTML permitidos em `variables.<nome>.field`: tipo do controle, obrigatório, min/max/step, tamanho mínimo/máximo, pattern, inputmode e linhas de textarea. Não conserva valor, default, checked, selected ou catálogos. Regras de máscaras implementadas somente pelo JavaScript do site precisam de adaptação.

A consulta de opções usa uma sessão Edge temporária, responde com `Cache-Control: no-store` e não grava catálogos no banco ou na receita. Aceita somente HTTP loopback sem credenciais/query/fragment, mesma origem, GET/HEAD, sem redirects, WebSocket, sessão persistente ou downloads. Aplica filtros nativos fornecidos nesta preparação; aguarda timers/requests e DOM estável, rejeitando atualizações que não concluam no prazo. Lê o formulário inicial e iframes presentes de mesma origem; listas em novas abas, páginas acessadas por cliques ou componentes que precisam de abertura/consulta específica exigem adaptação. SGIND/IQOS e login corporativo continuam bloqueados até validação na outra máquina.

Os dados informados nesta etapa pertencem à execução (`execution.inputs`), não à receita gravada. Campos genéricos aparecem como input_001 etc.; renomeie-os na receita para facilitar o uso. Eventos do runtime descrevem ações, sem incluir valores de preenchimento.

## Limites desta versão

- Seletores são estruturais; revisar após alterações no DOM. Navegação causada pelos cliques é reproduzida por esses cliques, sem copiar URLs intermediárias. Navegação pela barra de endereço e controles do próprio Edge não é capturada.
- Não prometer compatibilidade universal com toda página: calendários personalizados sem campo editável, shadow DOM fechado, componentes sem semântica acessível, canvas e iframes de outra origem exigem adaptação. Ações detectadas em canvas, uploads, campos readonly ou contextos não suportados impedem a exportação. Autenticação e campos sensíveis permanecem excluídos.
- Downloads precisam de um controle identificado e revisado. Eventos espontâneos, assíncronos ambíguos e downloads sem clique identificado não são convertidos automaticamente. Somente cliques de abertura de nova aba estão cobertos, não abas criadas manualmente na interface do Edge.
- Esta CLI aceita somente HTTP loopback sem query/fragment. Não usar para SGIND/IQOS; gates corporativos continuam fechados. A instrumentação é código confiável do gravador e não pertence à receita.
- Validação no Studio é estrutural, usando o contrato do runtime; não significa execução real bem-sucedida.
- Nenhum dado de preenchimento é persistido pelo gravador; isso não impede a página de teste de processar os valores em memória. Não usar páginas locais com dados/credenciais reais.

Testes: adicionar `apps/recorder` e `apps/runtime` ao PYTHONPATH; executar unittest discover em `apps/recorder/tests`. `NEXER_RUN_RECORDER_E2E=1` habilita testes Edge headless com canários sintéticos e o fluxo real gravar → salvar → reproduzir com entradas diferentes.

`NEXER_RUN_REPORT_OPTIONS_E2E=1` habilita o teste backend de catálogos com Edge e página HTTP sintética, incluindo atualização dependente após 1600 ms e falha fechada acima do limite.
