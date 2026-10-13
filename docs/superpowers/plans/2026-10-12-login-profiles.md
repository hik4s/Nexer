# Perfis de login reutilizáveis — implementation plan

**Goal:** Cadastrar URL e campos de acesso no Edge e reutilizar o perfil com credenciais efêmeras fornecidas na execução.

**Architecture:** Perfil e versões são configurações sem segredos. Seletor de alvos é modo próprio, separado do gravador de ações. Runner resolve somente versão fixada e credencial autorizada pelo canal de execução.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Delegação de implementação somente quando autorizada pelo usuário ou por instrução aplicável. Steps use checkbox (`- [ ]`) syntax for tracking.

**Tech Stack:** React/TypeScript/Vite, FastAPI, SQLAlchemy/Alembic/SQLite, SSE, Playwright/Edge e Python em Windows.

**Spec:** ../specs/2026-10-12-nexer-reusable-flows-design.md

## Global Constraints

- Credenciais entram somente na execução, em envelope efêmero separado de inputs; nunca em DB, receita, logs ou arquivos.
- HTTP é reservado a fixtures loopback; sites reais usam HTTPS e política de origens explícita.
- Cada fluxo usa processo/contexto/workspace próprio; não compartilhar Playwright síncrono entre threads.
- SGIND/IQOS mantêm gates fechados até validação real no ambiente autorizado.
- Testes sintéticos não provam compatibilidade universal. Preservar o legado e as mudanças locais existentes.
- Não fazer merge, force-push ou publicar implantação como efeito incidental destes planos.

## Review Focus

- URL/redirecionamento/iframe externo inesperado: bloquear sem enviar segredo e sem ampliar permissões pela receita.
- Registro de campos password: não ler valores ou permitir submissão acidental.
- Perfil alterado entre preparação e execução: snapshot por versão; revalidar antes de enfileirar.
- MFA/CAPTCHA/SSO e sucesso falso: sinalizar intervenção/adaptação; não marcar autenticado por ausência isolada do password.
- Expiração/cancelamento/logout durante login: interromper contexto e revogar referências.

### Task 1: Contrato e persistência de perfis

**Files:** Create `apps/backend/app/schemas_login_profile.py`, `apps/backend/app/api/login_profiles.py`, `apps/backend/app/repositories/login_profile.py`, `apps/backend/tests/test_login_profiles_api.py`; Modify `apps/backend/app/models.py`, `apps/backend/app/main.py`; Create próxima migration Alembic disponível (0004 se ainda não consumida).

**Interfaces:** LoginTarget(selector: str, frames: list[str]); LoginProfileVersion(login_url, allowed_origins, username_target, password_target, submit_target, success_rule). CRUD sem credenciais; versão imutável após publicação. SuccessRule é união de marcador DOM ou URL configurada, com formulário de login ausente.

- [ ] Escrever teste de CRUD/versionamento, URL inválida, payload com credenciais rejeitado e referência histórica preservada; observar RED.
- [ ] Implementar schemas com extra=forbid, normalização de origem e DTOs sem valores/defaults.
- [ ] Criar tabelas e migration, registro de rotas e repositório transacional.
- [ ] Testar migration nova e atualização de DB existente; confirmar fixtures sem segredos.

### Task 2: Identificar alvos no Edge

**Files:** Create `apps/recorder/nexer_recorder/login_capture.js`, `apps/recorder/nexer_recorder/login_picker.py`, `apps/backend/app/services/login_recordings.py`, `apps/backend/tests/test_login_recordings.py`, `apps/recorder/tests/test_login_picker_edge.py`.

**Interfaces:** `start_recording(profile_id, version) -> session_id`; `get_recording(session_id) -> status, targets`; `cancel_recording(session_id)`. Resultado restrito a três alvos e metadados permitidos; sessões associadas ao pareamento proprietário.

- [ ] Teste Edge local de seleção usuário/password/submit, input com canários, iframe mesma origem, clique que não submete, timeout/cancelamento e aba do usuário intacta; observar RED.
- [ ] Implementar overlay de instruções e captura estrutural sem qualquer leitura de value/checked/texto/cookies/requests.
- [ ] Usar processo/sessão nova e timeout; não reutilizar o JS do gravador normal removendo sua exclusão de senha.
- [ ] Negar endpoints sem sessão; outra sessão não consulta/cancela gravação. Limitar quantidade de sessões e reter resultado sem credenciais por prazo curto.
- [ ] Demonstrar que password/username/cookies-canário não aparecem em resultados ou arquivos e que árvore de processo criada é encerrada.

### Task 3: Tela Cadastrar login e configuração de sucesso

**Files:** Create `apps/frontend/src/pages/LoginProfilesPage.tsx`, `apps/frontend/src/pages/LoginProfilesPage.test.tsx`; Modify `apps/frontend/src/App.tsx`, `apps/frontend/src/lib/api.ts`, `apps/frontend/src/styles.css`.

**Interfaces:** Lista de perfis com rascunho/executável; botão Cadastrar login; nome e URL; Identificar campos no Edge; regra de sucesso; revisão e nova versão. Usuário/senha não fazem parte do formulário de cadastro.

- [ ] Testes de criar perfil, acompanhar seleção, cancelar e impedir publicação sem regra de sucesso; observar RED.
- [ ] Implementar UI/API/status com mensagem sobre campos selecionados, sem coletar credenciais nesta etapa.
- [ ] Testar navegação durante seleção, respostas atrasadas e perfil desativado. Inspecionar desktop/mobile.

### Task 4: Credential binding genérico e login autorizado

**Files:** Create `apps/runtime/login_profiles.py`, `apps/runtime/tests/test_login_profile_runtime.py`; Modify `apps/backend/app/schemas_execution.py`, `apps/backend/app/execution_credentials.py`, `apps/backend/app/worker_channel.py`, `apps/backend/app/api/executions.py`, `apps/worker/nexer_worker/processor.py`, `apps/frontend/src/pages/NewExecutionPage.tsx`, `apps/backend/app/services/report_options.py`.

**Interfaces:** `profile_credentials` no envelope de submissão, indexado por identidade de perfil/version. `resolve_login_profile(profile_id, version)` devolve configuração confiável; versão é fixada na criação. Secret provider recebe apenas referência opaca vinculada à execução/worker/sessão, mantendo a API especializada corporativa compatível.

- [ ] Teste de login local com nova credencial, sucesso verificável e falha que não expõe canários; observar RED.
- [ ] Generalizar binding sem aceitar segredo em execution.inputs nem alterar política SGIND/IQOS.
- [ ] Implementar navegação/origens confiáveis, preenchimento de dois alvos e submit identificado, com tentativa limitada e autorização revalidada durante operação.
- [ ] Testar redirect externo, origem proibida, iframe hostil, perfil trocado, cancelamento, logout e expiração durante login; cofre/cookies/contexto não sobrevivem.
- [ ] UI de credenciais fora do cache/storage; limpar após submissão/saída. Leitor de catálogos protegidos usa autorização efêmera específica.
- [ ] Documentar MFA/CAPTCHA/SSO não suportados automaticamente. Manter bloqueio se regra não verificável.

### Task 5: Jornada integrada e decisão de disponibilidade

- [ ] Fixture: cadastrar perfil → escolher alvos sem digitar senha → gravar fluxo parametrizado → publicar → execução com credenciais efêmeras → resultado.
- [ ] Demonstrar ausência de canários em DB, receita, eventos, logs e arquivos; não persistir sessão autenticada.
- [ ] Executar suites relevantes, build, revisão independente e handoff. Sites reais só com URL fornecida e participação autorizada do usuário; resultado registrado por perfil, sem abrir gates globais.


## Ledger de execução — 2026-10-12

- Aprovação: usuário respondeu continue após o desenho e planos. Execução inline, sem agentes de implementação, preservando checkout existente e diffs anteriores. Sem commit/push nesta rodada.
- Task1: modelo/API/configuração versionada sem segredos e migrations0004/0005 implementados; testes API perfis RED404 → GREEN3. Publicação exige3 alvos+regra de sucesso; desativação preserva versões.
- Task2: seletor separado no Edge, overlay3 alvos, bloqueio de digitação/submissão, processo privado por stdin/stdout metadata, owner/prazo/capacidade/cancelamento. Teste Edge canários e sem submit RED arquivo ausente → GREEN1. Testes manager owner/gate GREEN2. E2E do processo de seleção completo e revisão ainda necessários.
- Task3: Logins de sites, criar/selecionar perfil, identificar no Edge, salvar versão, regra URL/marcador, publicar/desativar. Teste UI cadastro sem password GREEN1; teste jornada de gravação/publicação e visual QA ainda necessários.
- Task4 em progresso: snapshot configuração por execução; profile_credentials envelope privado; vault/client aceitam identidade profile-id-vversion; worker usa contexto monitorado/política de origem; frontend refs fora do form/cache, limpeza após submit; Studio vincula referência somente. API rejeita credencial ausente para fluxo real. Teste login Edge local comPOST+cookie+marcador GREEN; erro tipadosem segredo; frontend cache-canary GREEN. Catálogos autenticados usam contexto temporário, desabilitam downloads e restringemGET/HEAD após login.
- Ruling: modo de teste realmente simula, sem navegador/login — bug antigo comprovado RED no processor; fixtures que pretendem testar ações reais passaram a test_mode=False. Custo se errado: algum teste antigo pode depender de semântica incorreta; testes de gateway/processador foram atualizados e passaram.
- Ruling: callback route aceita segundo parâmetro request opcional — bridge async fornece2 args; teste real perfil falhou TypeError, corrigido também método da política corporativa para compatibilidade. Revalidar suites monitor/corporate sintéticas.
- Ruling: normalizar ponto final de DNS e validar hostname ao cadastrar — evita bypass do gate corporativo por alias textual. Perfis genéricos não ampliam autorizações de SGIND/IQOS.
- Revisão automática bloqueou comando de edição UI grande com motivo somente blocked by policy. Informado ao usuário; aplicado por patches de arquivos. Nenhuma alteração de permissões ou bypass de autorização.
- Planos de lote/paralelismo ainda não executados. Continuar integração/aceite de perfis antes de iniciar supervisor multiworker.

## Ledger de continuidade — 2026-10-13

- Estado anterior acima é histórico. Perfil/runtime/canal/options e lote/supervisor agora implementados; não inferir validação real corporativa.
- Task2: manager/processo privado opt-in GREEN3; seletor Edge GREEN1, sem coleta de canários/submit. Lifecycle UI sair durante seleção RED0 chamadas → GREENcancelamento; resposta tardia de início também encerra processo.
- Task3/4: interface, Studio binding, credenciais DOM e envelopes separados implementados. Batch UI solicita um acesso por perfil compartilhado; teste segredo fora de Query/Mutationcache e campos limpos GREEN.
- Confirmação de login: marcador visível antes do login REDfill2 → GREENsem fill; username não aceita alvo password/hidden/file; URLsuccess igual àlogin rejeitada no runtime.
- Final: fixed contrato perfil+authentication/secret incompatível — test_recipe_rejects_mixed_login_contracts_before_publication RED→GREEN; validação compartilhada impede publicar fluxo garantidamente inválido.
- Revisão independente read-only da árvore atual:2Important, nenhumCritical estabelecido; outro achado em catálogo de lote corrigido no ledger correspondente.
- Evidência final: backend107 OK(12skips), worker32 OK(1skip), runtime107 OK(10skips), frontend38 OK e build. E2Es opt-in têm resultados específicos no handoff.
- Sites reais, MFA/CAPTCHA/etapas especiais continuam a exigir adaptação; gravador comum permanece loopback. Não marcar todos os critérios arquiteturais como cumpridos por uma fixture.
