# Piloto funcional: Todas as Ocorrências — SGIND
Data: 14/10/2026. Estado: desenho para revisão; implementação e execução real não concluídas.
Usuário autorizou executar quatro etapas e escolheu Todas as Ocorrências.
Objetivo: preencher empresa/período no Nexer, autenticar com credenciais temporárias, gerar uma única solicitação, baixar seu CSV, validar e disponibilizar o arquivo na interface.

## Evidências da inspeção atual
- scripts/open_nexer.ps1 inicia scripts/run_local.py com --api-only. O supervisor já sabe iniciar workers, mas o launcher padrão não usa esse modo.
- apps/backend/app/services/report_options.py rejeita todo fragmento de URL, incluindo #/rota. A política de opções é GET/HEAD e não reproduz navegação por cliques.
- relatorios/todas_ocorrencias.py usa app-dd-empresas p-select e input.p-datepicker-input; são pistas do legado, não evidência do DOM atual.
- Gates corporativos estão na API, resolução de perfil e runtime. authenticate_corporate e ligação ao processor já existem; não reimplementar esses módulos sem necessidade.
- Perfil genérico também rejeita o host corporativo; liberar apenas uma dessas camadas não torna o fluxo funcional.
- Contratos genéricos de consulta e download já existem. Identificador de consulta/job no SGIND ainda não observado.
- Worker marca SUCCEEDED se runner encerra sem falha. A receita piloto precisa exigir arquivo e validação final.
- ExecutionDetailPage mostra estado/eventos, sem lista ou download de artefatos. Não foi encontrada rota de entrega de arquivos na API inspecionada.
- Pasta atual não tem .git; preservar mudanças locais e não alegar commit/push.

## Desenho proposto
### 1. Operação local
Manter modo de consulta API-only explícito. Acrescentar caminho de inicialização para execução com um worker no piloto, diagnóstico do worker e rejeição clara de início real sem worker saudável.
Verificar fila existente antes de iniciar worker para não consumir trabalhos anteriores involuntariamente. Não iniciar um segundo backend na porta ocupada.
Critério: abrir o app, verificar worker pronto, criar execução, acompanhar progresso; desligamento limpa processos próprios.

### 2. Acesso SGIND
Usar o adaptador corporativo confiável já existente para SGIND, com perfil versionado apenas como referência quando aplicável. Unificar a decisão nas rotas de execução individual/lote/opções e no worker.
Credenciais vêm exclusivamente de campos locais, seguem pelo canal efêmero e são revogadas em conclusão, falha, cancelamento, logout e expiração.
Política depende de origem/caminhos/métodos observados no portal; não adicionar bypass de receita ou variável de ambiente que aprove integração.
Executar testes do canal API-worker em processos separados e do contexto restrito antes da sessão real assistida.
Critério: login correto confirmado na home; login inválido/expirado falha com mensagem útil, sem persistir segredos.

### 3. Preparação de filtros
Aceitar rotas hash seguras usando a mesma validação adotada no cadastro; continuar recusando credenciais e parâmetros sensíveis em URL.
Implementar leitura do controle de empresa conforme estrutura real observada: abrir painel associado, limitar leitura ao controle e aplicar filtros dependentes na ordem.
Requisições de opções precisam de política específica se o portal usar POST para consultar; não liberar todos os POST nem reproduzir cliques de geração durante a preparação.
Critério: empresas atuais aparecem, mudanças invalidam dependências, período usa formato correto, carregamento falha claramente quando o catálogo não está pronto.

### 4. Consulta e geração
Inspecionar uma jornada autorizada do piloto sem gravar credenciais, payloads ou conteúdo de negócio.
Identificar confirmação da consulta e sinais reais de dados/vazio/erro. Contrato atual exige IDs específicos; adaptar somente a partir da evidência do portal.
Identificar confirmação que vincule o arquivo à solicitação, inclusive central compartilhada. Nome por padrão, ordem e horário isoladamente não bastam.
Critério: um clique por solicitação; resultado antigo não avança; timeout não repete geração; arquivo de outra solicitação nunca é escolhido.
Se o portal não fornecer correlação suficiente, registrar a limitação e definir alternativa verificável antes de habilitar geração automática.

### 5. Arquivo final e interface
Exigir na receita piloto um download correlacionado e validação de CSV: arquivo existe, tamanho maior que zero, formato esperado, cabeçalhos acordados com o relatório real; rejeitar HTML de login e arquivos parciais.
Registrar somente metadados do artefato por execução/item e disponibilizar listagem/download autenticados na tela de execução.
O servidor deriva caminhos a partir do vínculo persistido e da raiz de downloads; não aceitar caminhos livres. Cobrir traversal, symlink, arquivo removido, colisão e resposta sem sessão.
Critério: sucesso somente após arquivo válido; usuário consegue baixar pela interface e identificar execução/período/empresa associados sem inspecionar pastas internas.

## Verificação de aceitação
1. Fixture sintética percorre UI/API/worker/Edge até CSV e recuperação pela UI.
2. Testes de senha inválida, logout/expiração, worker ausente, cancelamento durante espera, consulta sem dados, timeout e arquivo inválido.
3. Verificar isolamento entre execuções com mesmo padrão/nome; repetir piloto com novos parâmetros não reutiliza arquivo anterior.
4. Ensaio real assistido: usuário informa credenciais na UI local e escolhe empresa/período. Conferir CSV do próprio piloto.
5. Testar reinício: nenhuma geração é reenviada automaticamente; estados interrompidos são claros.
6. Executável/launcher atualizado é testado após fechar e abrir, com versão identificável.
Não contabilizar testes sintéticos como validação corporativa. Nenhuma dessas verificações reais foi feita nesta auditoria.

## Sequência
A. Operação/diagnóstico e testes do canal já existente.
B. Preparação de URL/controles e acesso corporativo por política única.
C. Inspeção assistida do SGIND e adaptação da receita piloto.
D. Validação/entrega do CSV e ensaio completo.
E. Empacotamento e verificação de reabertura.
Conservar o núcleo genérico; adaptações do SGIND ficam delimitadas. Tudo local, custo de infraestrutura zero.

## Informações necessárias na sessão assistida
Empresa, período de teste e confirmação de acesso manual ao SGIND. Senha/código nunca no chat.
Os seletores e identificadores de confirmação serão obtidos por inspeção autorizada do portal; não são inventados no desenho.
