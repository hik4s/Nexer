# Workspace prático — plano de implementação

> Usar executing-plans, execução inline autorizada pelo usuário: “Faça todas essas alterações. Concedo permissão para tudo, sem parar.” Não solicitar aprovações intermediárias para decisões reversíveis.

Goal: simplificar acessos, criação e reutilização de fluxos e lotes, sem persistir credenciais.

Architecture: grupos de acesso organizam perfis/destinos; cada perfil conserva configuração versionada e política de origem. Rotinas favoritas persistem referências e parâmetros declarados não secretos. UI guia preparação/revisão e oferece campos comuns, datas rápidas e repetição a partir de inputs já armazenados.

Tech: React/TypeScript, FastAPI, SQLite/Alembic, runtime existente. Sem dependências novas.

## Contrato aprovado

- Agrupar destinos como Energisa/SGIND/IQOS e reutilizar seletores, solicitar acesso uma vez por grupo no lote. Não ampliar gate corporativo nem compartilhar cookies entre processos.
- Cadastro guiado: site, acesso, gravação, nomes de campos, salvar/publicar. Aproveitar importação existente e introduzir gravação pela interface apenas dentro das políticas autorizadas do recorder.
- Campos comuns no lote apenas quando tipo/regras compatíveis; ajuste individual e listas carregadas por destino. Listas compartilhadas usam somente valores/labels habilitados presentes em todos os destinos.
- Rotinas favoritas: grupos de fluxos, parâmetros opcionais não secretos, preparar com um clique; nunca executar ao carregar favorito.
- Executar novamente: parâmetros da execução anterior, revisados contra receita atual; credenciais novas.
- Datas rápidas Hoje/Mês atual/Mês anterior/Personalizado, calendário local.
- Navegação principal Meus fluxos/Acessos/Execuções; configurações e Studio como ferramentas secundárias.
- Resumo antes de iniciar contém destinos, parâmetros e acessos, sem segredo; iniciar somente por ação explícita.

## Tasks

- [x] 1 Backend grupos/rotinas: migration0007, modelos, APIs autenticadas, validação campos/refs, testes RED404→GREEN, atualizar perfilDTO/API.
- [x] 2 Acessos UI: criar grupo, associar destino, reutilizar campos, UI lote compartilha DOM refs por grupo com envelopes específicos por perfil.
- [x] 3 Preparação: campos comuns compatíveis, ajuste individual, datas rápidas, revisão com parâmetros/destinos sem credenciais; testes de separação e regras.
- [x] 4 Reutilização: favoritos dashboard/preparação, repetir execução/lote via dados do backend, wizard ligado a Studio, navegação simplificada; testes de jornadas.
- [x] 5 Suites/build/visual desktop/mobile, revisão independente, documentação e handoff. Preservar diff acumulado, sem push/merge implícitos.

## Ledger

- Ruling: manter gravador comum loopback até política HTTPS específica validada — não transformar autorização genérica em acesso a sites/credenciais não fornecidos; custo: wizard explica gravação local/importação e não promete gravação universal.
- Task1: API grupos/rotinas RED404→GREEN2; teste integração publicar+favoritar sem executar e início explícito GREEN1. Migração0007 aplicada em bancos temporários nas suítes backend/worker.
- Task2: grupos e associação, clonagem somente de seletores (origens/confirmação independentes), envelopes por perfil com um DOMcredential por grupo. Teste duasURLs/grupoEnergisa/override/segredo fora do resumo GREEN.
- Task3: dates usam calendário local, mês atual até hoje, mês anterior completo e anos bissextos. Compatibilidade compara tipos/regras; base_url fica individual. Listas são consultadas por destino e só compartilham interseção de valores/labels habilitados. Ajuste individual preservado; campos compartilhados ficam bloqueados no destino até marcar personalização.
- Task4: rotinas favoritas persistem referências de fluxos, sem credenciais nem execução automática; repetir usa inputs declarados não secretos das versões anteriores para revisão na receita atual. Wizard recebe site/acesso/gravação/labels, gera rascunho versionado, valida/publica e abre preparação. Private recorder subprocess reaproveita CLI com finish/cancel, HTTP loopback. Edge real GREEN2: localidades sem canário digitado; URL externa rejeitada antes do spawn.
- Final review: agente independente read-only,2Important, nenhumCritical. Corrigidos em uma passagem: campo compartilhado aparecendo antes de carregar receita incompatível (RED→GREEN); confirmação de checkbox/range/color deixando resumo obsoleto (RED→GREEN). Invalidação fica no callback de parâmetro e catálogos.
- Evidência visual: Edge desktop1440/celular390, favoritos→datas/empresa comuns→resumo, wizard e acessos; sem overflow/erros de navegador. Prévia atualizada em127.0.0.1:4173, dados sintéticos, POST bloqueado.
- Decisão operacional: banco real/fila preservados; migration0007 deve ser aplicada antes de iniciar a instalação real. Sem commit/push/merge.
- Task5: frontend46/17arquivos GREEN; backend112 OK(13skips); worker32 OK(1skip); recorder15 OK(5skips em modo normal) e privateEdge recorder opt-in2/2; buildGREEN, diff-check limpo, visual atualizado e handoff escrito. Suite de gravador com todos os opt-ins registrada ao concluir a rodada.
- Gravador completo com NEXER_RUN_RECORDER_E2E=1:15/15 GREEN, incluindo seleção/login, controles e CLI original. Extração compartilhada de labels deixa nomes amigáveis também no resumo do lote; verificações de campos/lote e build reexecutadas.
- Complemento de listas: compartilhamento nativo REDcampo comum ausente→GREENinterseção carregada; alteração de período REDempresa anterior preservada→GREENseleção limpa; resumo REDid interno→GREENnome da opção. Botão carregar todos consulta sequencialmente para limitar contextos temporários e preserva opções do campo selecionado ao invalidar dependentes.
- Ruling: listas com IDs ou labels diferentes não são mapeadas automaticamente — evita aplicar uma empresa errada; custo: nesses destinos a seleção permanece individual até criar um mapeamento explícito.
- Verificação final após complemento: frontend49/17arquivos GREEN, buildGREEN, visual desktop/mobile sem overflow/erros. Backend112 OK(13skips), worker32 OK(1skip), recorderEdge15/15 e protocolo privado2/2 preservados. Prévia atual PID5448; consultas de opções demonstrativas são permitidas, mutações reais bloqueadas.
