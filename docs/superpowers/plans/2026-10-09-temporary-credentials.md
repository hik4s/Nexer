# Credenciais temporárias SGIND/IQOS — Implementation Plan

**Goal:** credenciais recebidas na interface e usadas somente na execução autorizada.
**Architecture:** pareamento local temporário, cookie protegido, cofre em memória por execução e sistema, canal autenticado API-worker e contextos descartáveis.
**Tech Stack:** React/Vite, FastAPI, Python, Playwright/Edge, SQLite local.
**Spec:** NEXER_WORK_HANDOFF_2026-10-09.md e desenho aprovado no chat em 09/10/2026.

## Global Constraints
Custo R$0; preservar mudanças; branch feat/etapa1-foundation; nenhum commit/push sem revisão e autorização; segredos fora de arquivos, banco, logs, eventos, receitas, parâmetros e keyring.

## Review Focus
Expiração durante execução interrompe novas ações; URLs/redirects externos falham; reinício invalida cofre/canal; erros não persistem valores; logout/cancelamento interrompem acesso e contexto.

### Task 1: Cofre temporário
Create: apps/backend/app/ephemeral_credentials.py. Test: apps/backend/tests/test_ephemeral_credentials.py.
Interfaces: put(execution_id, owner, systems, ttl_seconds); get(execution_id, owner, system); revoke(execution_id); revoke_owner(owner).
- [ ] Testar isolamento execução/proprietário/sistema, expiração, revogação, cópias defensivas e repr/erros seguros.
- [ ] Executar testes RED; implementar relógio monotônico e lock; executar GREEN e suite backend.

### Task 2: Proteção local
Modify: security.py, api/auth.py, main.py, frontend/auth.tsx e LoginPage.tsx.
- [ ] Testar pareamento de uso único, requests externos, Origin/Host, expiração/logout.
- [ ] Substituir conta .env por pareamento local temporário gerado no processo; manter cookie HttpOnly/SameSite Strict e acesso fail-closed.

### Task 3: Execução e canal worker
Modify: api/executions.py, schemas_execution.py, worker/main.py e nexer_worker/processor.py; criar launcher/canal.
- [ ] Testar passagem em processos separados, token inválido, execução não reservada e reinício.
- [ ] Capability por encarnação somente em memória/pipe herdado; vincular retirada à execução reservada; credenciais em campo separado, nunca inputs.
- [ ] Limpar em rollback, cancelamento, término, logout e timeout; verificar SQLite/respostas/eventos sem segredos.

### Task 4: Runtime
Modify: auth_guard.py, worker/main.py e processor.py.
- [ ] Testar provider temporário por execução/sistema e bloqueio de keyring/storage_state no fluxo novo.
- [ ] Validar HTTPS, origem permitida e URL final antes de preencher; bloquear destinos externos no contexto autenticado; fechar contexto em finally.
- [ ] SGIND origem conhecida; IQOS bloqueado até confirmação. Login SGIND bloqueado até validar sucesso pós-login. Sanitizar erros/eventos.

### Task 5: Interface e verificação
Modify: NewExecutionPage.tsx, lib/api.ts, testes frontend, handoff e MASTER_PLAN.md.
- [ ] Campos SGIND/IQOS separados, limpar depois do envio/falha/logout; não guardar segredos em storage/cache.
- [ ] Suites backend/worker/runtime/frontend, typecheck, build e diff --check; apresentar interface e diffs.

## Ledger
09/10: documentos lidos; dispositivo online; remote correto; branch feature; mudanças preservadas. Código ainda usa keyring e persiste textos de erros. Aprovação do usuário permite execução contínua; commit/push permanecem proibidos sem revisão. Plano inicialmente não foi escrito porque o diretório não existia; diretório criado, sem alteração em código.

## Contratos adicionais de execução do plano
A especificação completa está em 2026-10-09-temporary-credentials-spec.md; prevalece sobre resumos acima.

Task 2:
Create app/local_pairing.py: PairingAuthority.issue(ttl_seconds=300) -> str, consume(code: str) -> bool; validade monotônica, uso único e limite de 5 tentativas por código. API não chama issue.
POST /auth/login payload PairingRequest(pairing_code: SecretStr); retorna AuthSession sem código.
Tests test_local_pairing.py: invalid_code_does_not_create_session; code_is_single_use; code_expires_at_boundary; five_failed_attempts_invalidate_code; foreign_origin_is_rejected; non_loopback_host_is_rejected; logout_revokes_owner_credentials.
Frontend login(pairingCode: string) -> Promise<boolean>; LoginPage tem campo Código de pareamento. Testar formulário/erro/limpeza. Remover utilização de auth_username/auth_password_hash no fluxo ativo, mantendo primitivas antigas apenas se legado isolado precisar delas.

Task 3:
Create app/worker_channel.py: WorkerChannel(authority, vault, session_factory); resolve(execution_id: int, system: str, capability: str, incarnation: str) -> dict[str, str]; release(execution_id, capability, incarnation) -> None.
Create scripts/run_local.py: main() -> int; inicia backend e worker com pipe herdado, bind 127.0.0.1, gera pareamento somente no console. Não registrar capabilities nem usar argv/env/files para transportá-las.
Create worker/nexer_worker/credential_client.py: ExecutionCredentialClient.resolve(execution_id, system) -> dict; release(execution_id) -> None; comunicação sem pickle e sem logs de body.
Schema ExecutionCreate.corporate_credentials: dict[Literal["SGIND", "IQOS"], CorporateCredential] com CorporateCredential username/password SecretStr; este campo não aparece em ExecutionRead.
Tests test_worker_channel.py: wrong_capability; stale_incarnation; unclaimed_execution; foreign_worker_claim; separate_process_exchange; backend_restart; channel_unavailable; release_is_idempotent.
Tests test_execution_credentials.py: sqlite_contains_no_canary; response_contains_no_canary; rollback_revokes; cancellation_revokes; logout_revokes; session_ttl_bounds_credential_ttl.
Antes de aceitar credenciais, validar worker atual e política do adaptador; execução publicada não pode correr antes do cofre estar pronto. Se API reiniciar, worker marca falha constante CREDENTIALS_UNAVAILABLE.

Task 4:
Create runtime/corporate_auth.py: CorporateAuthPolicy(system: str, allowed_origins: tuple[str, ...]); validate_url(url: str) -> None; authenticate(page, credential_client, execution_id: int, validated_adapter) -> None.
Adaptador validado é configuração confiável, separada da receita; não aceitar seletores/origens arbitrários para credenciais.
Worker usa client somente para auth corporativa, sem expor segredos a VariableResolver. page_factory não carrega sessão keyring; processor não salva sessão keyring.
Substituir persistência de str(exc) e result.error por códigos constantes no fluxo corporativo; eventos usam lista de campos permitidos.
Tests test_corporate_auth.py: rejects_userinfo; rejects_wrong_port; rejects_similar_host; rejects_external_redirect_before_fill; blocks_arbitrary_script; unknown_iqos_fails; sgind_without_success_validation_fails; closes_context_after_failure.
Tests worker: keyring_never_called; session_state_never_saved; browser_error_canary_absent_from_events_and_sqlite; cancellation_closes_context; expired_credentials_stop_next_action.
Credenciais precisam de limpeza periódica no backend e limite de capacidade; get/put/revoke do cofre isolado não implementam ainda o ciclo do servidor.

Task 5:
NewExecutionPage envia corporate_credentials por chamada direta a api.createExecution fora de React Query mutation cache. Componentes CorporateCredentialsFields recebem somente estado local.
Tests CorporateCredentialsFields.test.tsx: separates_system_fields; clears_after_success; clears_after_failure; unmount_discards_values; no_storage_write; blocked_system_explains_reason.
Test API fetch: request includes credentials separately from inputs; response never rendered as secret.
Verification:
PYTHONPATH apps/backend;apps/worker;apps/runtime + NEXER_ENVIRONMENT=test; python -m unittest discover -s apps/backend/tests -v.
Mesmos paths: python -m unittest discover -s apps/worker/tests -v.
PYTHONPATH apps/runtime: python -m unittest discover -s apps/runtime/tests -v.
Frontend: npm test -- --pool=threads --maxWorkers=1; npm run typecheck; npm run build.
git diff --check; revisar novos arquivos via git diff --no-index contra /dev/null. Não fazer git add/commit/push automaticamente.

## Evidência desta rodada
Task 1: cofre isolado implementado; testes RED por módulo ausente, depois cinco testes GREEN.
Suite backend: 46 testes OK, exit 0, após corrigir PYTHONPATH para incluir worker/runtime.
Primeira tentativa da suite: 45 testes OK e erro de importação test_etapa1_gate por PYTHONPATH incompleto; não foi regressão de código.
Aviso StarletteDeprecationWarning sobre httpx/httpx2 observado; não alterado.
Tasks 2–5 pendentes. Cofre ainda não integrado; interface anterior mantida.
Nenhum commit/push. Revisão desta rodada pelo próprio autor; nenhuma revisão independente executada.

## Continuação Work — 09/10/2026, bloco de pareamento e canal
Implementado local_pairing.py: código aleatório, uso único, 5 minutos, limite de 5 tentativas; /auth/login recebe pairing_code SecretStr. Login .env não é usado pela API ativa. Sessão HttpOnly/SameSite Strict, TTL até 8h, relógio monotônico; logout/expiração revogam o cofre. Removido bypass de NEXER_ENVIRONMENT=test. Middleware valida loopback/Host/Origin; testes de negócio usam helper test_client.py com sessões explícitas.
Cofre ganhou capacidade 128 e limpeza periódica via lifespan a cada 5s.
Criados worker_channel.py, api/worker_credentials.py, nexer_worker/credential_client.py, secure_main.py e scripts/run_local.py. Capability por encarnação é transportada pelo stdin herdado, não por argv/env/arquivo. Rotas internas verificam capability, vínculo da execução, reserva do worker, sessão, cancelamento e estado RUNNING.
Testado transporte em subprocesso separado com HTTP fixture e valores sintéticos; não confundir com E2E corporativo. Rotas internas FastAPI têm dois testes próprios.
Worker não lê/grava keyring/storage_state no fluxo ativo; provider padrão nega segredos. Erros persistidos usam AUTOMATION_FAILED; renovação de receita não validada falha antes de criar navegador. Runtime ganhou política de origem exata HTTPS SGIND; adaptadores reais continuam bloqueados.
ExecutionCreate tem corporate_credentials separado com SecretStr/repr=False, mas API REJEITA esse campo com 409 até validar adaptadores. Cofre/canal NÃO estão ligados à criação de execuções corporativas de produção; não afirmar integração completa.
Frontend usa pareamento e exibe cartões SGIND/IQOS desabilitados em Nova execução. Nenhuma senha é coletada nesses campos ainda. API base usa hostname compatível com UI para cookie SameSite.
Verificação real: worker Ran 19 tests, OK skipped=1; runtime Ran 48 tests, OK skipped=1; frontend 18 testes/10 arquivos passaram, typecheck e build exit0. Suite backend passou no comando integrado; conferir contagem na saída antes de comunicar. git diff --check exit0 com avisos LF/CRLF.
Visual real: Edge renderizou tela vazia de pareamento; screenshot docs/development/previews/pairing-login.png via scripts/preview_pairing_ui.py. Frontend http://127.0.0.1:5173 HTTP200, PID de lançamento18716.
Tentativa de abrir API em PowerShell visível não produziu listener confirmado: /health falhou e última checagem API_NOT_LISTENING. Import app.main e disponibilidade uvicorn passaram. Não afirmar API live operacional. Usuário pode iniciar python scripts/run_local.py --api-only; Ctrl+C e repetir gera novo código e invalida sessões. Nunca capturar/registrar código local real.
Pendentes: investigar inicialização real API, testar UI-backend real, finalizar bind/rollback/snapshot seguro quando adaptadores validados, revogação/cancelamento do contexto ativo, teste real launcher API-worker e SGIND/IQOS. URL IQOS e sucesso SGIND desconhecidos. Nenhum login corporativo, commit ou push.


## Continuação Work — 09/10/2026: pareamento confirmado e vínculo por execução
Usuário confirmou acesso real à dashboard com código local. Esta confirmação substitui a nota anterior API_NOT_LISTENING; não reiniciar a API ou invalidar sua sessão automaticamente.
Implementado execution_credentials.py, put_session_credentials em security.py e criação de execução ligada ao cofre/canal antes do commit da fila. Campos corporativos continuam fora dos modelos SQLAlchemy/respostas/inputs; dicionário transitório é limpo após a cópia para o cofre, sem promessa de zeroização física de strings Python.
Política confiável require_validated_corporate_auth permanece bloqueando QUALQUER envio corporativo na produção. Somente dependency override dentro dos testes autoriza credenciais sintéticas. Não há flag no request/.env para contornar o bloqueio.
Vínculo exige sistema correspondente à automação e worker ONLINE da encarnação atual, heartbeat até 30s, sem stopped_at. Owner vem exclusivamente do cookie; não é persistido. TTL limitado à sessão e a 3600s. Logout é serializado com put; bind ocorre depois de liberar session lock para evitar inversão channel -> session. Mudança de encarnação antes do bind falha e revoga.
Rollback de IntegrityError e de qualquer exceção antes/durante commit revoga cofre e vínculo. Cancelamento, logout, timeout e release já existentes foram exercitados com credenciais presentes, não por ausência inicial.
Novo test_execution_credentials.py: 12 testes com SQLite temporário e canários fictícios; criação/claim/release idempotente, dump SQL/resposta sem canários/owner, rollback, cancelamento, logout, TTL, worker stale/canal ausente, sistema incorreto, mudança de encarnação e logout concorrente com submissão. Observado RED com módulo gate ausente; depois gate sozinho permitiu reproduzir falta de armazenamento/validação; implementação passou. Quatro casos adicionais verificaram comportamento já implementado.
Verificação final desta rodada: backend Ran 74 tests, OK, exit0; worker Ran 19 tests, OK (skipped=1, E2E Edge não executado); git diff --check exit0, avisos LF/CRLF. Aviso Starlette/httpx legado mantido. Frontend/runtime sem alterações nesta rodada, não rerodados. Revisão desta fatia pelo próprio autor; revisão independente da branch completa ainda pendente.
Ruling: preservar branch e alterações aprovadas, sem nova worktree/commit/push; política corporativa permanece bloqueada pois URL/seletores IQOS e sucesso SGIND não estão validados. Custo: esta fatia não libera execução corporativa real nem valida launcher API-worker completo.
Pendências: validar adaptadores reais (sem pedir senhas no chat), restringir contexto autenticado/origens e scripts antes de habilitar login; finalizar formulário efêmero fora do cache React Query; cancelamento do contexto durante navegação e expiração durante ações; E2E do launcher; limpar mapas de owners expirados/terminais periodicamente para não reter tokens além do necessário; revisão independente final. Não afirmar plano inteiro concluído.
API atual não foi reiniciada: alterações backend entram em vigor no próximo reinício manual. Nunca coletar o código de pareamento real.

### URLs e formulário corporativo informados — 09/10/2026
Usuário forneceu URLs IQOS https://indicadoresenergisaess.scl.corp/iqos/#/login e SGIND https://indicadoresenergisaess.scl.corp/sgind/#/login, junto de HTML de ambos os formulários. Evidência registrada em docs/development/corporate-login-evidence.md. Usuário/senha têm name cre_username/cre_password; botão real é button[type="submit"]; SGIND form#idFormLogin, IQOS form[name="form"]. Não usar classes de validação Angular ou atributos pc/_ngcontent como seletores.
Esta evidência substitui "URL/seletores IQOS desconhecidos" nos registros anteriores, mas NÃO valida sucesso de autenticação. Precisamos URL e elemento exclusivo pós-login de cada sistema. Políticas da API/runtime ainda bloqueiam corp login; nenhum segredo solicitado, enviado ou armazenado.
Interface IQOS atualizada para aguardando validação, explicando que URL/formulário foram informados e falta indicador de sucesso; campos continuam desabilitados. Nenhuma navegação/login real executado nesta rodada. Branch feat/etapa1-foundation confirmada; sem commit/push.

### Evidência home e probe anônimo — 09/10/2026
Usuário forneceu URLs pós-login /sgind/#/home e /iqos/#/home e HTML com app-home-page em ambos. Sucesso candidato composto: URL home exata do sistema + componente visível + formulário login ausente.
Probe REAL na máquina do usuário via Playwright/Edge headless, contextos novos sem cookies/storage state e sem preencher credenciais: home SGIND -> /sgind/#/login, login_visible=true, home_visible=false; home IQOS -> /iqos/#/login, mesmos estados. TLS padrão, exit0. Esta evidência valida redirecionamento anônimo; NÃO é um login automático/E2E autenticado.
corporate_auth.py agora define CorporateLoginDefinition congelada para SGIND/IQOS, URLs/selectores confiáveis independentes da receita e matches_authenticated_home (predicado puro). validate_corporate_url reconhece IQOS e restringe cada sistema ao seu caminho, bloqueando troca SGIND/IQOS, aliases, traversal, caminhos percent-encoded, userinfo, host semelhante, porta externa e HTTP.
Cinco novos testes observados RED (política IQOS ausente, caminhos não restritos, definições/matcher ausentes), depois GREEN. Runtime Ran53 tests OK skipped=1, exit0. Worker Ran19 tests OK skipped=1, exit0. Esses skips são E2E Edge opt-in, não executados. O probe Edge anônimo é separado desses testes.
Interface SGIND/IQOS agora diz "Telas de login e início identificadas. Integração automática em preparação." Campos seguem desabilitados. Teste de texto observado RED antes da alteração.
Ruling: evidência manual+probe permite fixar URL/home/seletores; manter gates API/require_validated_adapter enquanto login seguro do worker não está conectado. Custo: usuário ainda não pode enviar credenciais corporativas por esta UI. Não pedir novamente URL/HTML home já recebidos.
Pendências de implementação, não de dados home: interceptar destinos e restringir scripts no contexto; preencher e validar usando client efêmero; revalidar credenciais/cancelamento durante ações; formulário fora de React Query/storage; teste launcher/E2E autenticado com senha digitada pelo usuário apenas na UI. Mensagem de erro de senha desconhecida pode ser tratada por timeout/código constante. Não habilitar guard de renovação de receita arbitrária.
Branch feat/etapa1-foundation confirmada; mudanças preservadas, sem commit/push. Próxima etapa é ligar definição confiável ao worker, não solicitar nova aprovação para continuar desenvolvimento autorizado.

## Continuação Codex — adaptador de login confiável
Implementado authenticate_corporate em apps/runtime/corporate_auth.py, usando as definições fixas SGIND/IQOS. Valida URL exata de login e action do formulário antes de resolver credenciais; consulta o canal novamente antes de senha, submit e durante espera por home; observa cancelamento; exige URL home exata, componente visível e ausência de formulário. Descarta dicionários transitórios e retorna erro constante sem encadear erro bruto do navegador.
Pré-condição: contexto novo, restrito pelo chamador, que deve fechá-lo em falha. A função AINDA NÃO está chamada pelo worker; gates da API/runtime e campos UI continuam bloqueados. Não confundir primitive de login com proteção de rede completa ou login real.
Dez testes sintéticos em test_corporate_login.py. Oito falharam antes da implementação por função ausente; teste de timeout inválido revelou TypeError, corrigido movendo cálculo depois da validação. Caso de revogação confirmou comportamento já implementado.
Verificação observada: runtime Ran63 OK skipped=1 exit0; worker Ran19 OK skipped=1 exit0. Primeiras tentativas restritas falharam por PermissionError nas pastas temporárias/SQLite; repetição elevada passou. Skips E2E Edge; nenhum login real, build frontend ou teste backend nesta entrega.
Próximo: restringir requests/redirecionamentos/popups/iframes/WebSockets no contexto, conectar adaptador ao processor pelo sistema da automação, revalidar autorização durante as ações e testar cleanup integrado antes de abrir gates/UI. Serviços existentes não reiniciados. Sem commit/push.

## Continuação Codex — contexto restrito conectado ao worker
Nova política apps/runtime/corporate_browser.py: contexto novo sem storage_state, service_workers bloqueados; requests restritos ao caminho HTTPS exato do sistema; route.fetch com max_redirects=0/max_retries=0/timeout=5000; redirecionamentos HTTP negados (exceto 304); CSP complementar bloqueia frames/srcdoc, workers, plugins e base, restringe form-action. Popups revogam contexto. Requisições proibidas marcam revogação antes de abortar e fechar.
BrowserManager.create_corporate_page instala política antes de criar página. Bootstrap worker usa essa fábrica. Processor determina SGIND/IQOS pelo cadastro da automação, aplica gate confiável, valida receita, verifica canal, autentica antes da receita e revalida antes de cada tentativa e antes de registrar sucesso. Receitas corporativas não fornecem authentication/renewal, variáveis secret ou switch_tab; ações arbitrárias continuam negadas pelo validador. CorporateExecutionGuard fecha página ao perder autorização ou voltar ao formulário de login.
Encontrado e corrigido por testes: sistema corporativo podia cair no navegador comum; retry não revalidava autorização; revogação durante última ação podia resultar em sucesso.
Encontrado em Edge real: WebSocket.close síncrono no callback deadlocka com Playwright 1.62.0 instalado. Pilha mostrou _on_web_socket_route -> WebSocketRouteHandler.handle -> sync close esperando no despachante assíncrono. Callback agora só marca revogação e NUNCA chama connect_to_server; próxima checagem externa fecha contexto. Não alegar fechamento imediato durante ociosidade/bloqueio: essa parte ainda precisa de implementação. Testes de fechamento HTTP aguardam eventos do navegador, pois goto pode falhar antes do evento close chegar.
Três testes com Edge headless REAL e fixture HTTP LOOPBACK passaram: login sintético com DOM real/home + bloqueio fetch externo; redirect HTTP sem seguir destino; WebSocket revogado e contexto fechado na próxima checagem. Fixture substitui somente a fronteira route.fetch por resposta HTTP local; não houve acesso corporativo nem credenciais reais. Não equivale a compatibilidade HTTP real de SGIND/IQOS ou E2E API+worker.
Verificação final observada: runtime Ran77 OK skipped=1 exit0 (fixture Edge habilitada); worker Ran24 OK skipped=1 exit0; backend Ran81 OK exit0. Aviso legado Starlette/httpx observado. Skips são os E2E Edge anteriores; os três novos fixtures foram EXECUTADOS. git diff --check exit0, avisos LF/CRLF. Frontend sem alteração; build/typecheck não reexecutados nesta entrega.
Revisão independente via skill requesting-code-review: nenhum achado concreto critical/important/minor; reconheceu os pré-requisitos ainda pendentes. Backend sweep de owners já existia no checkout e passou nos testes; não reimplementado.
Gates API/require_validated_adapter permanecem fechados; testes do processor substituem somente o gate via patch local de teste. UI continua desabilitada. Nenhum commit/push, nenhum reinício de serviço existente ou consumo de fila real.
Próxima entrega: revalidação e cancelamento durante ações bloqueadas/ociosidade; E2E launcher/API/worker em processos separados com canários sintéticos e cleanup; validar compatibilidade de destinos/assets/API reais sem ampliar política por receita. Somente depois abrir política de submissão e formulário efêmero fora do cache React Query. Revisão e teste corporativo autenticado exclusivamente com senha digitada na UI local.


## Checkpoint solicitado pelo usuário — 09/10/2026

Estado consolidado e instruções completas em [CONTINUAR_NEXER_2026-10-09.md](../../../CONTINUAR_NEXER_2026-10-09.md) (na raiz do checkout). Esse arquivo prevalece sobre pendências históricas superadas. Usuário pediu salvar como está e autorizou commit/push na branch feat/etapa1-foundation; não merge/master/force-push. Monitor async conectado com pool de revogação dedicado, validação antes de criar thread e msDownloadsHub desativado no processo Edge. Regressões RED→GREEN. Backend85/skipped4, worker24/skipped1, runtime padrão92/skipped9, monitor10, Edge monitorado5: OK. Frontend18, typecheck e build: OK. Fixture Edge antigo de bloqueio fetch encontrou FAIL/hang e foi interrompido; não afirmar suíte opt-in completa verde. Quatro novos testes subprocessos ainda não executados e helper precisa trusted_fixture. Classificação item cancelado e cleanup/concorrrência continuam pendentes. Gates/UI corporativos fechados; nenhum login real. Diagnóstico removido, serviços/fila reais preservados.
