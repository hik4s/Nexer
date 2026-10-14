# Nexer — Auditoria e plano de microtarefas para o primeiro relatório
Data: 14/10/2026. Escopo: cópia local em C:\Users\kis\Downloads\Nexer-codex-smart-recorder-handoff-2026-10-14.
Documento de arquitetura/aceite. **Não representa implementação de código, homologação corporativa nem commit Git.**

## 1. Evidências observadas nesta auditoria
- Desktop Commander: equipamento ESSPPEROE-0057D online e acessível.
- Pasta indicada existe, mas não contém .git. NÃO executar git init, reset, force-push ou sobrescrever outro checkout.
- Outros checkouts locais: C:\Users\kis\Downloads\Nexer (branch feat/etapa1-foundation, commit 4f7e73c, limpo no momento da consulta); C:\Users\kis\Downloads\Nexer-codex-nexer-reusable-flows-2026-10-13 (feat/nexer-smart-recorder, commit a414983, possui arquivo não rastreado).
- GitHub confirma a branch remota codex/smart-recorder-handoff-2026-10-14 em hik4s/Nexer; origem histórica registrada no HANDOFF.md. A cópia desta pasta não tem ancestral Git verificável.
- API em 127.0.0.1:8000/version respondeu HTTP 200 (Nexer API 0.1.0); frontend em 127.0.0.1:5173 respondeu HTTP 200. Portas ocupadas por processos existentes; NÃO subir outra instância nas mesmas portas.
- O processo de API foi identificado com --api-only; zero processos secure_main.py encontrados. Não há worker de execução observado. /diagnostics exige sessão (HTTP 401 anônimo), coerente com autenticação.
- scripts/open_nexer.ps1 usa scripts/run_local.py --api-only; run_local.py sabe iniciar workers com --workers, mas o launcher padrão não ativa esse caminho.
- apps/backend/app/services/report_options.py rejeita fragmentos hash, URLs corporativas, autenticação e parâmetros sensíveis; catálogo restrito a GET/HEAD e controle nativo ou semântica ARIA. Não relaxar essas proteções sem evidência.
- Contratos genéricos query, download correlacionado e reparo de alvos JÁ EXISTEM. Ler HANDOFF.md seções 12–14; não os reconstruir.
- docs/2026-10-14-piloto-todas-ocorrencias-design.md confirma ausência de rota autenticada de artefatos e ausência de validação SGIND real na inspeção histórica.
- Verificação desta sessão: análise AST de 186 módulos .py = exit 0; opções/backend = 3/3 testes com Edge sintético habilitado, exit 0; frontend = 12/12 testes selecionados em 3 arquivos, exit 0.
- Nenhum login corporativo, ação de geração de relatório, alteração de banco real, reinício do Nexer, alteração de executável ou commit/push foi realizado.

## 2. Decisões e limites obrigatórios
1. GPT Astra projeta, prioriza, revisa evidências e escreve microtarefas; **outro modelo implementa código**. Não confundir auditoria e documentação com mudança funcional.
2. Branch de trabalho nova derivada de codex/smart-recorder-handoff-2026-10-14, após verificar SHA/status/diff. Não modificar master nem mesclar historicamente raízes incompatíveis.
3. Infraestrutura de custo zero. Credenciais apenas na interface local, transmitidas por canal efêmero e revogadas em todos os términos; nunca em .env/receita/logs/Markdown.
4. Controle de downloads na central SGIND compartilhada requer prova de propriedade por execução; nome/prefixo, ordem, 'último arquivo' e timestamp não são suficientes.
5. Ação com efeito externo (consulta/geração/download) não pode ser repetida automaticamente depois de resultado incerto.
6. A aprovação de suíte sintética não libera origens corporativas nem equivale a E2E real. Nenhum 'bypass' de política de acesso.
7. Não ligar worker à fila do banco já em uso até inventariar itens pendentes e confirmar estratégia de isolamento/reconciliação.
8. O piloto Todas as Ocorrências exige sucesso apenas depois de o CSV próprio ser salvo, validado e acessível pela interface.

## 3. Microtarefas executáveis (ordem por dependência)
### G0 — Ambiente e origem versionada
- [x] **NX-AUD-01 [P0]** Inventariar pasta, Git, serviço em execução e documentação. Evidência: itens da seção 1.
- [ ] **NX-GIT-02 [P0]** Conferir SHA/árvore do remoto de entrega e criar checkout Git separado, sem tocar na pasta exportada nem nas alterações do checkout antigo. Aceite: branch derivada comprovada, status limpo, upstream e SHA registrados; nenhum arquivo sobrescrito inadvertidamente.
- [ ] **NX-OPS-03 [P0]** Fazer inventário *somente leitura* da fila e do banco atualmente usados. Aceite: quantidade/status de QUEUED/RUNNING, origem/versão da API e caminho do banco estabelecidos sem expor dados ou consumir fila. Ponto de controle antes de iniciar workers.
- [ ] **NX-QA-04 [P0]** Criar ambiente de teste isolado (DB SQLite temporário, downloads temporários, portas livres, nenhuma credencial real). Aceite: comando reproduzível e shutdown sem processos filhos órfãos.

### G1 — Operação/launcher
- [ ] **NX-OPS-05 [P0]** Projetar e implementar modo explícito 'executar' com exatamente 1 worker no piloto, preservando modo --api-only para inspeção. Aceite: usuário vê diferença entre 'visualizar' e 'executar'; nenhum worker é ligado por efeito colateral de abrir tela.
- [ ] **NX-OPS-06 [P0]** Criar readiness API + worker com confirmação de registro/heartbeat/consumo, não apenas porta aberta. Aceite: falta de worker bloqueia nova execução real com erro orientativo, mas não invalida visualização.
- [ ] **NX-OPS-07 [P0]** Controlar encerramento/reinício do launcher e worker próprio; evitar porta duplicada e recuperação silenciosa de job incerto. Aceite: cancelamento e fechamento alcançam processos filhos; fila antiga não é consumida automaticamente.
- [ ] **NX-OPS-08 [P1]** Testar pareamento/token local em inicialização nova, expiração e múltiplas janelas. Aceite: cópia do código local ou entrega de token ocorre sem logging de segredo; falha tem orientação recuperável.

### G2 — Acesso e preparação do SGIND
- [ ] **NX-AUTH-09 [P0]** Mapear gate corporativo existente ponta a ponta: rotas de execução unitária/lote, validação, perfil e worker. Aceite: matriz allow/deny por sistema, origem, método e path; não adicionar permissões globais.
- [ ] **NX-NAV-10 [P0]** Admitir fragmento de rota #/home apenas nos caminhos seguros e consistentes com perfil/origem. Aceite: aceita hash de SPA autorizado e rejeita query de credenciais, origem alternativa, URL com usuário/senha e redirecionamentos indevidos.
- [ ] **NX-FORM-11 [P0]** Definir obtenção de opções de empresa usando sessão autorizada, quando exigida, sem retornar credenciais ao dashboard nem passar chamadas corporativas por bypass. Aceite: catálogo atual, erro por indisponibilidade e nenhum POST não observado/autorizado.
- [ ] **NX-FORM-12 [P0]** Adaptar controle p-select empresa e filtros dependentes com estado/escopo da sobreposição; não selecionar o primeiro item arbitrariamente. Aceite: filtros posteriores são invalidados quando a empresa muda; uma opção única é comprovada antes de selecionar.
- [ ] **NX-FORM-13 [P1]** Normalizar data inicial/final, timezone e validação do intervalo. Aceite: período enviado igual ao solicitado e rejeição de entradas impossíveis.

### G3 — Evidência SGIND e geração
- [ ] **NX-SGIND-14 [P0, BLOQUEIO EXTERNO]** Inspeção assistida do portal autorizado: rota real, controles, estados consulta dados/vazio/erro, identificador de solicitação e nome/ID de arquivo disponibilizado na central. Aceite: capturas de metadados permitidos e mapeamento rastreável; sem credenciais/payloads/dados sensíveis no registro.
- [ ] **NX-QUERY-15 [P0]** Parametrizar receita piloto no contrato query existente com confirmação NOVA e única por solicitação. Aceite: resultado stale/erro/vazio interrompe; timeout não repete clique.
- [ ] **NX-DOWN-16 [P0]** Configurar snapshot/generation/download correlacionado na central compartilhada. Aceite: execução A nunca baixa arquivo B em teste concorrente; se SGIND não fornecer identificador verificável, BLOQUEAR automação e propor fluxo manual assistido sem falsa garantia.
- [ ] **NX-FLOW-17 [P0]** Persistir receita piloto versionada 'Todas as Ocorrências' com empresa/período como inputs, sem dados da sessão gravada. Aceite: preview/revisão/executar reproduz os mesmos parâmetros, ações e seletores de confiança.

### G4 — Arquivos e conclusão
- [ ] **NX-FILE-18 [P0]** Definir contrato de artefato por execution_id/item_id: nome original, MIME, tamanho, hash opcional e estado de validação, sem caminho arbitrário fornecido pelo cliente.
- [ ] **NX-FILE-19 [P0]** Validar CSV final: existência/tamanho, CSV legível, cabeçalhos acordados após amostra autorizada, codificação, proteção contra HTML de SSO e arquivo parcial. Aceite: arquivo inválido não marca SUCCEEDED.
- [ ] **NX-FILE-20 [P0]** Criar listagem e GET de download autenticados com autorização por proprietário; derivar caminho da raiz confiável e id persistido. Aceite: traversal, symlink, usuário não autorizado, arquivo removido e colisão recebem respostas seguras.
- [ ] **NX-UI-21 [P0]** Mostrar artefato e status na ExecutionDetailPage, com erro compreensível e download do CSV. Aceite: navegador baixa exatamente os bytes validados da execução.
- [ ] **NX-WORK-22 [P0]** Associar sucesso do item à presença do artefato exigido, revogação de segredo em qualquer saída e eventos/situações consistentes. Aceite: falha, cancelamento e ausência de CSV não são SUCCEEDED.

### G5 — Homologação e distribuição
- [ ] **NX-QA-23 [P0]** E2E isolado UI → API → worker → Edge → CSV → UI, com DB/portas/downloads temporários. Aceite: repetição com parâmetros diferentes; inspeção de hashes/bytes, logs sem segredos, cleanup confiável.
- [ ] **NX-QA-24 [P0]** Matriz negativa: senha errada, expiração, worker ausente, lista vazia, timeout, ação com resultado incerto, cancelamento, dois lotes sobrepostos, arquivo inválido, restart. Aceite: falha fechada, nenhum reenvio silencioso.
- [ ] **NX-QA-25 [P0, BLOQUEIO EXTERNO]** Primeiro ensaio real acompanhado no SGIND com credenciais digitadas na interface, empresa/período informados pelo usuário. Aceite: arquivo pertencente ao job, válido, nome e filtros corretos, disponível pelo Nexer; coletar apenas evidências não sensíveis.
- [ ] **NX-PACK-26 [P1]** Empacotar launcher/EXE somente após aceite do piloto. Aceite: nova instalação em pasta limpa abre/fecha, diagnostica dependências e repete E2E local; não sobrescrever Nexer-Atualizado.exe em uso sem plano de migração.

## 4. Ordem de execução para modelo de código
1. Primeiro bloco: NX-GIT-02 + NX-OPS-03 + NX-QA-04. *Entregar inventário e nenhuma alteração de serviço/prod.*
2. Segundo: NX-OPS-05/06/07 com TDD e E2E isolado, sem criar jobs no banco real.
3. Terceiro: NX-AUTH-09/NX-NAV-10/NX-FORM-11/12/13 em fixtures sintéticas e políticas comprovadas.
4. Gate humano: NX-SGIND-14; se faltar ID vinculante, parar antes de NX-DOWN-16.
5. Quarto: NX-QUERY-15/NX-DOWN-16/NX-FLOW-17 e NX-FILE-18 a 22.
6. Quinto: NX-QA-23/24; só depois NX-QA-25; finalmente NX-PACK-26.

## 5. Critério comum de conclusão
Para cada microtarefa, modelo de código registra: arquivos alterados; teste RED que reproduz o defeito; implementação mínima GREEN; testes de regressão; resultado real com exit code; diff revisado; riscos/limitações; e estado do Git. Não chamar skip de pass, não declarar E2E corporativo sem evidência da jornada real. Não fazer commit/push antes de revisão de segredos e mudanças. Planejamento é de GPT Astra; implementação fica com o modelo selecionado pelo usuário.

## 6. Bloqueios e próximos insumos
- Git na pasta exportada ausente; branch remota foi localizada. É preciso checkout separado antes de mudança de código.
- Nexer servido atualmente em API-only e worker não observado; não reconectar worker à fila atual sem inventário.
- Página /diagnostics sem sessão respondeu HTTP 401; não contornar autenticação para observabilidade.
- Ainda faltam provas autorizadas do DOM real do SGIND e de um identificador forte vinculando solicitação à linha do download.
- Usuário fornecerá credenciais somente na própria interface corporativa e definirá empresa/período quando chegar a sessão real.
