# Continuidade Nexer — 2026-10-13

Workspace Windows: C:\Users\hikas\Documents\ChatGPT\Nexer. Branch feat/etapa1-foundation. Alterações cumulativas locais, sem commit/push/merge. Preservar legado e diffs anteriores. Usuário autorizou continuar login/lotes e, nesta rodada, aplicar nexer-logo-kit à identidade visual com minimalismo e interação.

## Implementado

Perfis versionados sem credenciais, API e migrations0004/0005. Seleção de3 alvos no Edge por processo privado, bloqueando digitação/submit. UI Logins de sites; cancelar seleção ao sair, inclusive resposta de início tardia. Studio vincula somente id/version do perfil.

Credenciais via inputs DOM não controlados, envelope separado, cofre/canal efêmero e snapshot de configuração. Modo de teste realmente simula sem login. Perfil só confirma acesso por URL/elemento explícito e senha ausente; marcador já presente antes de login é rejeitado. Receita com perfil+authentication legado/variável secret é rejeitada antes de publicar.

Lotes transacionais/idempotentes, migration0006, um Execution por fluxo com inputs próprios. Dashboard seleciona vários; NewBatchPage prepara campos e um acesso por perfil; BatchDetailPage acompanha SSE/status e cancela indivíduo/lote. Replay SSE sem duplicação, eventos limitados500 e limpeza ao trocar execução.

Supervisor --workers1..4, padrão2, processos isolados e capabilities privadas distintas por stdin. Claim de execução com credencial respeita worker vinculado. Worker perdido faz execução vinculada aguardando falhar sem reassociar segredo.

Identidade Percurso aplicada usando arquivos originais do kit em public/brand e favicon. Navegação lateral/mobile, dashboard grafite, atalhos, biblioteca em cartões, busca e seleção de lote preservada ao filtrar. Formulários/Studio/entrada e estados de interação padronizados. Sem novas dependências.

## Evidência e revisão

- Frontend38 testes e build passaram; logo/busca/seleção/lote/Studio/mobile inspecionados em Edge, sem overflow horizontal ou erros de navegador.
- Worker32 testes: OK,1skip. Um teste antigo dependia de PID10 estar morto; fixture corrigida para declarar esse estado por mock, evitando reaproveitamento Windows.
- Runtime107: OK,10skips no modo normal. Login Edge opt-in passou anteriormente, inclusivePOST/cookie/regra de sucesso; nova regressão de contratos mistos observada RED→GREEN.
- Backend107: OK,12skips no modo normal; alembichead verificado em bancos temporários.
- Supervisor contenção real:4 testes Windows passaram (parada, parent-loss, worker morto, timeout).
- Dois processos reais + Edge: teste passou, downloads sobrepostos; cancelamentoA enquantoB termina. Segundo lote termina ambos, contas distintas com mesmo nome de arquivo em diretórios distintos; canário ausente no dumpDB.
- Revisão independente de login/lotes identificou2 problemas Importantes: loading travado ao editar durante catálogo pendente; receita com contratos de login incompatíveis publicável. Ambos corrigidos com regressões RED→GREEN e suítes relevantes. Nenhum Critical estabelecido.

## Prévia de design

http://127.0.0.1:4173 — dados de exemplo; POSTs bloqueados e nenhuma automação real. Servidor temp/preview_identity.py em processo oculto, PID12388 nesta sessão. Scripts/screenshots emtemp são locais/ignorados. Fonte real emapps/frontend. Reabrir preview após npm run build; o servidor lê dist atualizado a cadaGET. Prévia não substitui login da instalação real.

## Limites e próximos passos

### Continuação aprovada: workspace prático

O usuário pediu implementar todas as7 sugestões, autorizando prosseguir sem aprovações intermediárias. Plano docs/superpowers/plans/2026-10-13-practical-workspace.md. Grupos/rotinas API+modelos+migration0007; cadastro guiado NewFlowPage, recorder privado pela UI, datas rápidas, campos comuns compatíveis/override, resumo antes de iniciar, favoritos, repetir execução/lote, navegação3 áreas e histórico de lotes implementados.

Grupos organizam destinos e compartilham somente o preenchimento de credenciais; seletores podem ser clonados, mas regras de sucesso/origins não. Rotinas favoritas pela UI salvam grupos de fluxos; API aceita parâmetros declarados não secretos. Repetir traz parâmetros anteriores para revisão contra versão atual, exclui credenciais e exige novo acesso.

Wizard de5 passos publica sem executar; teste real API comprovou ausência de Execution até o início explícito. Gravação privada local permite concluir/cancelar; Edge real comprovou captura de seletores e placeholders sem canário digitado. Site inicial é configuração explícita, preenchida como base_url ao preparar, editável pelo usuário.

Revisão independente:2Important corrigidos com RED→GREEN (compatibilidade antes de todas receitas carregarem; resumo obsoleto ao confirmar campo por botão). Frontend49 testes, build, visual desktop/mobile verificados. Backend112 OK(13skips), worker32 OK(1skip), privateEdge recorder2/2, recorderEdge15/15. Listas comuns usam interseção de opções habilitadas por valor+label; mudar período limpa seleção anterior e exige nova consulta. Resumo exibe nomes amigáveis, nomes das opções e datas locais. Manter limites corporativos e sem migração do banco real nesta sessão.

Prévia atual em4173 usa servidor oculto PID5448 (substituiu8472/12388) e dados de exemplo, incluindo rotina Relatórios mensais. POST de consulta input-options devolve catálogos sintéticos; mutações continuam bloqueadas. Screenshots temp/practical-*.png; verificador temp/check_practical_visual.py. Abrir Meus fluxos → Preparar rotina → escolher período → carregar opções de todos → Empresa para testar preenchimento comum e resumo; Criar fluxo guiado e Acessos para as novas telas.

Gravador completo opt-in Edge:15/15 OK, além do protocolo privado2/2. Resumo de lote usa labels amigáveis. Patch cumulativo temp/NEXER_PATCH_2026-10-13.patch regenerado e validado por git apply --reverse --check; inclui novas migrações/API/UI/ativos, não scripts/screenshots ignorados da prévia.

Gravador comum ainda loopback. PerfisHTTPS não significam compatibilidade universal; MFA/CAPTCHA, etapas extras, popups autenticados e componentes customizados exigem adaptação. SGIND/IQOS gates fechados; teste corporativo no outro computador autorizado. Banco de produção não migrado nem fila real iniciada nesta rodada; aplicar migrações antes de usar o núcleo real. Expandir cenários de perda/restart de workers e filas longas; testes atuais não demonstram todos os casos Windows.

Continuar alinhamento visual com usuário, depois adaptação de sites reais fornecidos. Não pedir novamente autorização para tarefas reversíveis já solicitadas; não fazer login externo real sem site e credenciais autorizados. Não colocar segredo no JSON, cache, evento ou banco.

## Campos após gravação e download por padrão — rodada mais recente

Usuário confirmou que nomes de relatórios mudam e deseja padrão configurável. Gravador lê somente rótulos estruturais dos campos (label/aria-labelledby/aria-label/legend) antes da edição, sem valores selecionados/digitados, defaults ou nomes de arquivos da gravação. Somente campos editados geram parâmetros. A UI segue automaticamente para Campos após DONE; base_url permanece configuração de Site, separado dos nomes dos campos descobertos. Nova tentativa de gravação limpa receita anterior somente após abrir com sucesso.

Toolbar Parar gravação na página principal chama binding de conclusão, não entra no script e não interfere no cancelamento pelo dashboard. Processo privado real validado usando esse botão, sem fechar janela manualmente.

Links download e controles Baixar/Download em tabelas/listas registram seletores de collection, revisáveis após gravar. Parâmetro download_pattern_NNN é solicitado na execução (glob, exemplo Relatorio_*.xlsx), sem copiar nome usado na gravação. Runtime percorre linhas visíveis na ordem do DOM e baixa a primeira correspondente; sem match aguarda até timeout, respeita cancelamento e falha sem baixar arquivo alheio. Preserva suggested_filename atual do site e impede sobrescrever arquivo já salvo na mesma execução. Centrais devem estar ordenadas pelos mais recentes primeiro; estruturas particulares exigem revisar seletores/Studio.

Revisão independente encontrou texto Baixar contaminando nome em listas; regressão Edge RED→GREEN corrigida removendo controles de ação ao ler nome da linha (:scope). Novas evidências: frontend50/17 arquivos + build OK; recorder19/19 com Edge; runtime109 OK/10skips; backend112 OK/13skips; protocolo privado2/2 com Edge/toolbar. QA campos e configuração de download desktop/mobile sem overflow/erros em temp/recording-fields-*.png. Plano docs/superpowers/plans/2026-10-13-recording-fields-downloads.md, README do gravador atualizado.

Não houve nova migração, início de fila real, commit/push nem expansão do escopo de origens. Gravador direto continua HTTP local; prévia4173 continua read-only com dados de exemplo. Site externo/corporativo e distribuição final ainda não validados. Patch cumulativo regenerado após estas alterações.
