# Nexer — automações reutilizáveis, perfis de login e lotes

Data: 2026-10-12. Direção de produto solicitada pelo usuário nesta conversa; interfaces técnicas abaixo são a proposta de implementação. Não declarar cadastro de login ou paralelismo prontos com base neste documento.

## Objetivo e experiência

Nexer passa a ser um aplicativo local Windows para automatizar tarefas em sites, pessoais ou profissionais. Seus três pilares são automações, perfis de login reutilizáveis e gravação de fluxos. SGIND/IQOS continuam como adaptadores especializados, não como limite do produto.

Fluxo principal: **Cadastrar login → Gravar fluxo → Revisar campos → Publicar → Nova execução ou Executar lote → Acompanhar resultados**. Fluxos sem autenticação pulam o perfil de login. Cada etapa deve ter indicação clara de rascunho, validação e disponibilidade; não exibir recurso apenas planejado como funcional.

O usuário confirmou selecionar vários fluxos e iniciar um lote, com progresso e cancelamento separados por fluxo. Cada fluxo tem seus próprios parâmetros, versão e resultado. Uma falha não cancela automaticamente os demais.

## Estado real reaproveitado

React/Vite, FastAPI, SQLite/Alembic, SSE, receitas versionadas, parâmetros dinâmicos, gravador Edge, runtime, worker, canal efêmero de credenciais e cancelamento já existem. Gravação e consulta de catálogos estão limitadas a fixtures locais de mesma origem. O worker reserva execuções atomicamente, mas seu loop ainda processa uma execução por vez. Configurar concurrency_limit sozinho não cria paralelismo real.

A entrega do Studio nesta rodada importa JSON local e permite editar nomes exibidos, mantendo identificadores e placeholders. Carrega a receita da versão publicada selecionada e invalida validar/publicar após editar. Isso é independente da implementação dos módulos abaixo.

## Perfil de login

O botão **Cadastrar login** abre um formulário com nome do site e URL de login. Ao clicar **Identificar campos no Edge**, uma sessão nova abre a URL e um modo de seleção permite apontar os campos de usuário, senha e o botão de entrada. Neste modo, clicar identifica um alvo e impede submissão; não se digita senha para cadastrar. Formulários com várias etapas exigem adaptação explícita, sem inferir fluxo de SSO ou ignorar desafios.

Armazenar apenas nome, URL configurada, origens permitidas, seletores estruturais, cadeias de iframe de mesma origem, tipo do campo e regra de sucesso. Não ler ou salvar input.value, texto digitado, password, checked, cookies, token, estado autenticado, URLs intermediárias ou corpo de requests. Os valores usados durante uma gravação nunca viram defaults.

A regra de sucesso deve ser explícita: marcador de página autenticada ou URL final configurada sem query/fragment, acompanhada de ausência do formulário de login. Não considerar ausência isolada do campo senha como prova de login. Perfil sem regra verificável permanece rascunho. CAPTCHA, MFA, consentimentos e confirmação humana são sinalizados; não implementar evasão. Nesta primeira versão, esses perfis não são marcados executáveis automaticamente.

Modelo proposto: `LoginProfile(id, name, current_version, status)` e `LoginProfileVersion(profile_id, version, login_url, allowed_origins, username_target, password_target, submit_target, success_rule, validated_at)`. Target contém `selector` e `frames`. Cada receita publicada pode referenciar uma versão de perfil; alterar perfil cria nova versão, sem alterar execuções já criadas.

API proposta: CRUD `/login-profiles`, versões `/login-profiles/{id}/versions`, início/status/cancelamento de seleção `/login-profile-recordings`. Retornos não contêm credenciais. Arquivo JSON de perfil pode conter configuração, nunca segredo. Exclusão é desativação quando há referência em histórico.

## Execução autenticada

Nova execução mostra Usuário/Senha apenas para os perfis usados pelo fluxo. Credenciais são enviadas em envelope efêmero separado de `inputs`, receita, eventos e armazenamento. O formulário fica fora do cache React Query e do armazenamento do navegador; limpa referências após submissão/cancelamento/saída. A execução conserva somente referências opacas vinculadas à sessão, versão do perfil, execução e worker autorizado.

Reaproveitar revogação por cancelamento, término, logout, expiração e perda do worker. Generalizar a identidade SGIND/IQOS para perfil versionado sem eliminar os gates especializados. Não adicionar credenciais em .env, CLI, arquivos temporários, logs ou exportações. Reinício exige novas credenciais; não restaurar sessões autenticadas de disco.

Na preparação de listas protegidas, abrir contexto efêmero autorizado usando o mesmo perfil; catálogos continuam em memória, com no-store. Não reaproveitar sessão de outro fluxo ou conta. Não enviar credenciais em payload de parâmetros persistidos.

## Sites e isolamento

Permitir perfis HTTPS configurados pelo usuário; HTTP é reservado a fixtures loopback. Rejeitar userinfo/query/fragment na URL configurada. Origens são explícitas e normalizadas pelo backend. Redirects, assets, iframes e popups passam por política do perfil; SSO externo exige origem adicional cadastrada e revisão específica. A receita não pode ampliar essas permissões. Novo perfil genérico não pode contornar bloqueio de SGIND/IQOS.

O seletor de alvos de login é um modo separado do gravador normal, que deve continuar excluindo senhas e formulários de login. Suas sessões têm timeout, cancelamento, limite de sessões simultâneas e encerramento da árvore de processos apenas criada pelo Nexer. Não fechar Edge pessoal. Autenticação real exige testes autorizados no ambiente do usuário; fixtures não provam compatibilidade universal.

## Lotes e paralelismo

Dashboard mantém Relatórios registrados e ganha uma biblioteca de fluxos, com seleção múltipla e botão **Executar lote**. Não apagar nomenclatura de relatórios dos fluxos já existentes. Preparação mostra um card por fluxo: parâmetros próprios, versão publicada e perfil de login necessário. Usar o mesmo perfil permite informar credenciais uma vez para o lote, mas distribuir autorizações efêmeras separadas, sem compartilhar contexto autenticado.

Persistir `ExecutionBatch` e vincular uma execução existente por fluxo ao lote. Batch criação valida todos os itens antes de enfileirar: versões publicadas, parâmetros, perfis e limite. Persistência é atômica; falha de binding efêmero revoga os bindings criados e reverte o lote. Submissão idempotente evita duplicar trabalho quando o usuário repete o clique ou uma resposta se perde. Snapshot de receita/perfil é fechado na criação.

API proposta: `POST /execution-batches`, `GET /execution-batches/{id}`, `POST /execution-batches/{id}/cancel`. A resposta contém IDs e estados por execução. Cancelamento individual usa API existente; cancelar lote solicita parada das execuções ainda não terminais e não altera sucessos anteriores. Agregação distingue sucesso total, sucesso parcial, falha total e cancelamento parcial/total; SSE preserva vínculo com execução de origem e Last-Event-ID.

Implementar paralelismo por processos isolados, cada um com seu próprio driver Playwright, BrowserManager, contexto, sessão DB e workspace. Não compartilhar objetos Playwright síncronos entre threads. Supervisor mantém identidade/capability por processo. Inicialmente dois slots, configuráveis de 1 a 4; excedente permanece na fila. Limites maiores, agentes remotos e distribuição são evolução posterior, não condição desta entrega. O canal atual de worker único precisa ser generalizado antes de aumentar o número de processos.

Isolamento testado: cookies, credenciais, filtros, resultados e cancelamento não cruzam fluxos. Login e gravação são trabalhos separados das execuções; limite evita esgotar a máquina. Reinício recupera estados interrompidos sem reproduzir automaticamente ações potencialmente não idempotentes.

## Sequência de entrega

1. Studio: importar gravação, nomes amigáveis, edição/versionamento corretos (implementação nesta rodada).
2. Perfis: modelo/API/tela e identificação de campos no Edge, inicialmente fixtures sintéticas.
3. Login genérico: binding efêmero, política por origem, regra de sucesso e execução; validação autorizada de sites.
4. Lotes: criação atômica, parâmetros por fluxo e acompanhamento individual.
5. Worker: múltiplos processos/capabilities, isolamento, parada e prova de simultaneidade real.
6. Jornada integrada: cadastrar perfil → gravar → publicar → lote de dois fluxos com valores novos; depois empacotamento Windows.

## Critérios de aceite

- Selecionar os campos de login não salva valores nem submete formulário.
- Receita, DB, logs e arquivos de teste não contêm canários de senha/cookies/tokens.
- Login só é considerado bem-sucedido após regra explícita; erro por segredo nunca devolve conteúdo.
- Nome amigável muda o dashboard sem alterar placeholder, tipo ou regra do campo.
- Dois fluxos têm intervalos de execução sobrepostos em processos reais, não somente status RUNNING simultâneos.
- Cancelar fluxo A encerra somente seu contexto e preserva fluxo B; cancelar lote encerra todos os ativos.
- Um resultado com o mesmo nome em outro fluxo não é sobrescrito.
- Lote inválido/idempotência/queda do worker/revogação não deixam registros parciais ou credenciais reutilizáveis.
- Gates corporativos seguem fechados até validação no computador com acesso.

## Alternativas avaliadas

Ampliação apenas corporativa não atende ao direcionamento. Compartilhar uma sessão de Edge entre fluxos é mais simples, mas mistura contas e cancelamentos. Recomenda-se biblioteca genérica com perfis versionados e execução isolada por processo, preservando especializações corporativas existentes. Cadastro e execução são módulos distintos para que novos sites não exijam código específico em toda a aplicação.

Planos separados: [Perfis de login](../plans/2026-10-12-login-profiles.md) e [Lotes/paralelismo](../plans/2026-10-12-batches-parallelism.md). Estes planos ainda não foram executados.
