# Nexer — geração demorada e seleção de arquivo novo

Data: 14/10/2026. Estado: direção aprovada pelo usuário com “Continue”; contrato genérico detalhado abaixo para o plano de implementação. O adaptador real SGIND depende de evidência adicional do portal.

## Objetivo

Continuar o método B, com inteligência local do gravador e adaptadores reutilizáveis. Esta entrega permite aguardar um arquivo gerado com atraso e baixar o item vinculado à solicitação correta, inclusive quando várias execuções usam a mesma central. A identificação de item novo é uma evidência complementar; sozinha não comprova a origem do arquivo.

## Requisito acrescentado pelo usuário

O usuário confirmou que futuramente vários relatórios serão baixados simultaneamente em lote e que a central SGIND é compartilhada entre os relatórios. Contextos de navegador e pastas isolados não isolam a fila de arquivos no servidor.

Formato de nome descrito pelo usuário: `TodasOcorrencias-XXXXX.csv`, com vários números aparentemente aleatórios no sufixo e prefixos equivalentes para os outros relatórios. Esse formato permite filtrar por tipo e distinguir nomes completos. Ainda não foi confirmado que o sufixo seja um ID de solicitação, nem que o nome completo apareça fora da central após gerar. A próxima informação necessária é onde o nome/identificador fica disponível para a execução que enviou a solicitação.

Consequências obrigatórias:

- Não selecionar um item somente por ser novo ou corresponder ao padrão, mesmo quando houver um único candidato visível.
- Não reservar a central separadamente por tipo de relatório: relatórios diferentes podem disputar a mesma lista.
- Cada solicitação deve produzir um vínculo de correlação usado pela execução que a enviou.
- A disponibilidade de um arquivo para B não autoriza o download por A. Cancelamento ou falha de A não afeta o vínculo ou resultado de B.
- Atributo de identidade na linha distingue itens, mas precisa ser relacionado à solicitação para provar propriedade. Encontrar um `data-job-id` novo na central, sem conhecer o ID da solicitação, ainda é insuficiente.

A primeira entrega de seletores e prontidão permanece como base, na branch `codex/smart-recorder-foundation`, checkout `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`. Reutilizar esse checkout e preservar os diffs existentes.

## Decomposição do próximo escopo

O próximo escopo foi dividido em dois blocos independentes:

1. Geração → espera → seleção de arquivo novo, descrito aqui.
2. Consulta → resultado, erro ou ausência de dados, que precisa de contrato próprio de conclusão e apresentação no histórico.

Os testes atuais de visibilidade/habilitação não comprovam nenhuma dessas duas etapas. Esta entrega não altera autenticação, políticas de origem ou os gates corporativos.

## Experiência proposta

O usuário grava a solicitação de geração e, quando o arquivo fica disponível, clica no botão de download na central. Na revisão de downloads, pode escolher **Arquivo novo gerado neste fluxo** e indicar qual ação gravada solicita a geração.

O Nexer configura a comparação antes dessa ação usando a estrutura da coleção já capturada. A UI apresenta a ação vinculada, o prazo de espera e a estratégia que correlaciona solicitação e arquivo. A escolha é explícita; a aplicação não presume que um clique próximo foi a solicitação certa.

Para central compartilhada, o modo só pode ser habilitado após configurar uma correlação verificável. O adaptador SGIND depende de quais identificadores ou informações o portal efetivamente fornece.

O padrão do arquivo continua sendo uma entrada da execução. Nenhum nome ou valor da demonstração vira padrão, identidade ou valor inicial da receita.

Receitas existentes continuam usando sua seleção atual quando executadas dentro das condições antigas. Essa compatibilidade não valida seleção por padrão em lote na central compartilhada. Fluxos sem correlação confiável devem ser sinalizados como incompatíveis com execução simultânea nessa central antes de enfileirar, sem escolher outro arquivo automaticamente. Fluxos sem download e downloads individuais mantêm seu contrato.

## Estratégias de correlação

Preferência 1: obter um ID/protocolo da solicitação a partir de um marcador DOM verificável após gerar e procurar o mesmo ID na central. O valor existe só na memória da execução; a receita guarda apenas onde obtê-lo e onde compará-lo.

Uma segunda estratégia futura poderá inserir um identificador único gerado pelo Nexer em um campo permitido, se o portal permitir nomear a solicitação. Não integra esta implementação: depende de suporte confirmado do portal.

Sem vínculo verificável, não habilitar download automático simultâneo na central. Um fallback coordenado pode serializar solicitações que disputam a mesma central e preservar paralelismo nos demais fluxos, mas precisa de desenho próprio e não elimina interferência de solicitações externas ao Nexer. Mutex apenas no processo worker ou separação de diretórios não resolve o problema.

Tipo, usuário, horário, filtros, ordem das linhas e padrão de nome podem restringir candidatos, mas só constituem correlação suficiente quando o contrato do site permite demonstrar unicidade da solicitação. Duas execuções com os mesmos filtros e nomes precisam continuar distinguíveis.

## Contrato declarativo

Adicionar ação `snapshot_downloads`, inserida imediatamente antes da ação de geração escolhida. Ela recebe os seletores da coleção e a cadeia de frames. Coleta a identidade dos itens presentes somente na memória da execução.

Converter a ação de geração escolhida de `click` para `request_download`. Esse passo recebe `baseline`, com o ID do snapshot, e `confirmation`, com `selector` de um elemento contendo somente nome completo ou protocolo; a leitura usa texto ou um dos atributos estruturais de identidade permitidos. Antes de clicar, ler o marcador existente; depois do clique, aguardar marcador único, visível, não vazio e diferente do anterior. Uma resposta antiga já presente não comprova nova solicitação. Cancelamento ou falta de confirmação não reenvia a ação.

No passo `download`, `generation` contém o ID do passo `request_download`. A correlação é por nome integral quando a coleção não tem atributo de identidade, ou por igualdade de protocolo quando tem `identity_attribute`. Padrão de nome e ausência da identidade na baseline complementam a correlação; nenhum deles a substitui.

Validação exige IDs existentes e únicos, snapshot imediatamente antes da geração e geração antes do download. A ação escolhida precisa ser clique esquerdo simples. Geração e download correlacionados recusam retry automático. Coleções dos passos vinculados devem concordar em seletores e estratégia; frames e índice de aba precisam ser iguais. O runtime também confere a identidade real da página. Referências, configurações desconhecidas e ciclos são recusados na validação.

Exemplo de passos (fragmento; `pattern` deve ser declarado como variável da receita):

```json
[
  {"id":"baseline","action":"snapshot_downloads","collection":{"container":"#table","rows":"#table tbody > tr","name":"td:first-child","button":"button","pattern":"{{pattern}}","identity_attribute":"data-job-id","shared":true}},
  {"id":"generate","action":"request_download","selector":"#export","baseline":"baseline","confirmation":{"selector":"#request-result","attribute":"data-job-id"},"timeout_ms":180000},
  {"id":"obtain","action":"download","selector":"button","filename":"download","preserve_filename":true,"generation":"generate","collection":{"container":"#table","rows":"#table tbody > tr","name":"td:first-child","button":"button","pattern":"{{pattern}}","identity_attribute":"data-job-id","shared":true},"timeout_ms":180000}
]
```

`confirmation` sem `attribute` lê texto. Valores de confirmação são limitados a 256 caracteres de identificador/nome (`A–Z`, `a–z`, números, `_`, `-` e `.`); uma mensagem inteira, URL ou resultado malformado não vira chave. O valor observado pertence somente à execução e nunca é um campo de configuração ou variável comum.

`shared: true` declara uma central compartilhada e exige o novo vínculo para validar/publicar. Receitas antigas sem essa declaração continuam compatíveis, mas não recebem promessa de segurança concorrente. Nenhuma heurística marca a central SGIND como validada a partir do host ou do padrão fornecido pelo usuário.

O snapshot e a coleção usam seletores idênticos para linhas e nome. Opcionalmente, podem usar um atributo de identidade configurado, limitado inicialmente a `data-job-id`, `data-report-id` ou `data-download-id`. Esse atributo é configuração estrutural; seus valores só são lidos durante execução e ficam em memória.

Sem esse atributo, a identidade é o nome integral do arquivo. Um arquivo de mesmo nome que já existia no snapshot não pode ser classificado como novo apenas porque a tabela foi reconstruída. Esse caso exige identificador de item ou adaptador específico.

O formato continua `schema_version: 1`, com campos adicionais opcionais e validação estrita do novo contrato. A aplicação que recebe a receita deve conhecer as novas ações antes de aceitá-la; não prometer que runtimes anteriores as executarão.

## Snapshot e seleção

1. Antes da solicitação, observar todos os itens materializados na coleção, inclusive ocultos, para compor a baseline. A central precisa existir antes da ação de geração.
2. Exigir baseline completa dentro do limite de 1000 linhas. Se excedida, se a leitura não concluir no prazo ou se houver identidade ausente/duplicada com atributo configurado, interromper antes de gerar.
3. Executar a ação de geração uma vez. O vínculo deve recusar retry automático dessa ação, pois repetir a solicitação pode gerar arquivos duplicados.
4. Aguardar linhas visíveis vinculadas ao identificador da solicitação, com nome correspondente ao padrão; a baseline é evidência complementar contra itens antigos.
5. Nenhum candidato correlacionado: continuar aguardando até o prazo ou cancelamento. Um candidato correlacionado: revalidar sua identidade e verificar botão único, visível e habilitado antes de baixar. Vários candidatos correlacionados ou identidade inconsistente: interromper com diagnóstico de ambiguidade, sem clicar em nenhum. Mudanças na ordem das linhas não podem trocar o item entre verificação e clique.
6. Preservar o nome atual fornecido pelo navegador e a proteção existente contra sobrescrita de arquivo na mesma execução.

O prazo de cada etapa de confirmação/download será configurável na revisão entre 1 e 15 minutos, padrão 3 minutos. São dois orçamentos separados: a confirmação começa ao entrar em `request_download`; a busca/obtenção começa ao entrar no passo `download`. O snapshot tem prazo próprio de 30 segundos. Cada operação de leitura/clique respeita o tempo restante; polling usa intervalos de até 250 ms e verifica cancelamento e autorização. O orçamento de obtenção termina com o evento de download confirmado pelo navegador; salvar o arquivo continua sujeito ao transporte existente e não recebe promessa de prazo rígido nesta entrega.

## O que a comparação comprova

A comparação identifica um item que não fazia parte da lista observada antes da geração e que corresponde ao padrão configurado. A seleção final exige a correlação adicional com a solicitação. Sem esse vínculo, um item único também pode pertencer a outro fluxo ou usuário.

Centrais paginadas, virtualizadas, acessíveis somente após gerar ou com trabalhos concorrentes indistinguíveis precisam de um adaptador que forneça correlação verificável e descreva os limites da observação. Padrão específico ajuda a filtrar; não substitui identificação da solicitação.

## Memória, segurança e diagnóstico

Guardar snapshots em um campo próprio de `ExecutionContext`, fora de `variables`, inputs, eventos, checkpoints, receitas e banco. Vincular cada snapshot à página e aos frames. Limitar a 1000 identidades por snapshot e no máximo 50 snapshots por execução, limpando ao terminar ou cancelar.

Erros usam códigos constantes para baseline indisponível/incompleta, identidade inválida, contexto divergente, múltiplos candidatos e prazo excedido. O worker precisa preservar somente esses códigos conhecidos, com mensagens amigáveis na UI, sem persistir textos de página, nomes examinados ou exceções brutas do browser.

Snapshots não são checkpoints para retomar após restart. Perda do processo exige nova execução e não reenvia automaticamente a solicitação de geração.

Nenhum valor de campo, nome de arquivo, identificador de trabalho, cookie, token ou conteúdo de rede é coletado da demonstração para implementar essa comparação. Valores de nomes/identidades usados no replay não entram em logs de seleção; os metadados do arquivo efetivamente baixado seguem a política de resultados existente.

## Arquivos e fronteiras previstas

- `apps/runtime/recipe.py`: ações e validação das referências, limites e compatibilidade.
- Novo módulo de runtime para snapshots/seleção: leitura de coleção, baseline e decisão de candidato único.
- `apps/runtime/context.py`: armazenamento efêmero e limpeza dos snapshots.
- `apps/runtime/actions.py`: registro da nova ação e integração ao download.
- Novo componente/helper frontend para configurar o modo e vincular geração, usado por `NewFlowPage.tsx`.
- Worker e UI de histórico: códigos seguros e mensagens de diagnóstico pertinentes.
- Testes de runtime, Edge sintético, configuração frontend e jornada privada de gravação/reprodução.

Não reestruturar módulos sem relação com a entrega. Nenhuma migration de produção é necessária para snapshots efêmeros.

## Critérios de aceite

- Central já contém arquivo correspondente; outro aparece depois de atraso: baixar somente o item correlacionado à solicitação atual.
- Duas execuções simultâneas, mesma central e mesmo padrão: concluir cada fluxo com seu próprio arquivo, mesmo que B fique disponível antes de A.
- Um arquivo novo de B aparece enquanto A aguarda e é o único candidato do padrão: A não baixa esse arquivo.
- Dois relatórios diferentes compartilham a central; duas execuções do mesmo relatório usam filtros iguais: a correlação ainda distingue as solicitações.
- Cancelar A enquanto B aguarda: impedir download posterior por A e permitir conclusão de B.
- Reordenar ou reconstruir a lista entre seleção e clique: revalidar a identidade e não clicar em arquivo alheio.
- Novo item correlacionado aparece após mais de 2,5 segundos: seleção funciona sem ampliar a correlação de clique/download da gravação.
- Tabela é reconstruída com o arquivo antigo: não confundir reconstrução DOM com novo arquivo.
- Nome se repete e há identificador diferente de trabalho: reconhecer item novo pela identidade configurada. Sem identificador, aguardar/falhar sem baixar o antigo.
- Dois candidatos permanecem indistinguíveis após a correlação: informar ambiguidade e não iniciar download.
- Botão atrasado/desabilitado: aguardar dentro do orçamento. Mais de um botão no candidato: recusar.
- Baseline ausente, truncada, sem identidades verificáveis ou em outra aba/frame: interromper antes de efeito inadequado.
- Referência adiantada/inexistente, geração com retry ou configuração malformada: recusar na validação.
- Cancelamento e expiração de autorização durante polling impedem clique posterior.
- Receitas antigas mantêm sua seleção e campos existentes nos modos compatíveis; lote simultâneo na central compartilhada exige estratégia confiável configurada. Fluxos sem download continuam válidos.
- Canários de nomes/identidades da demonstração e valores transitórios de seleção ausentes de receita, eventos e dump do banco.
- Jornada completa sintética: gravar → configurar vínculo → validar → reproduzir com padrão/entradas novas → obter arquivo correto.

Testes novos terão RED antes da implementação, seguido de GREEN e regressões pertinentes. Validação SGIND/IQOS continua sendo uma etapa separada no computador autorizado.

## Próximo passo

Implementar e testar o contrato genérico com páginas sintéticas que mostram protocolo/nome na confirmação e compartilham uma central. Isso permite avançar sem inventar sinais do SGIND. Antes de habilitar o adaptador SGIND, confirmar onde o vínculo de solicitação fica disponível e validá-lo no ambiente autorizado. Depois, especificar o reconhecimento de resultado/erro/ausência de dados, incluindo apresentação de resultado vazio em execução/lote.


## Ajustes confirmados na implementação

- Coleções correlacionadas exigem `container`: raiz única presente antes da solicitação. Isso distingue uma central vazia válida de um seletor que não encontrou a central. O contrato legado de coleção não muda.
- A confirmação anterior é lida mesmo se estiver oculta; depois do clique somente uma confirmação visível e diferente pode estabelecer o vínculo.
- A geração aguarda prontidão com polling e verifica cancelamento/autorização antes do único clique, sem retry após timeout. Leituras usam no máximo 250 ms de espera por locator e respeitam o prazo restante.
- A busca faz a checagem final e o clique do botão na mesma operação DOM, em raiz fixada e conectada. É código interno do runtime; receitas não podem fornecer JavaScript. Botões HTML e links são suportados; componentes que exigem eventos nativos confiáveis precisam de adaptador específico. Coleção usa seletores CSS DOM; shadow DOM, paginação e virtualização precisam de adaptador que comprove a abrangência.
- O orçamento do download vai até o evento do navegador; o salvamento mantém a política existente. A referência em memória é eliminada em `finally`, inclusive em cancelamento/erro de validação.
