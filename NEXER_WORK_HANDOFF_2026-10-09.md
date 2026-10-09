> ATUALIZAÇÃO 09/10/2026: leia primeiro [CONTINUAR_NEXER_2026-10-09.md](CONTINUAR_NEXER_2026-10-09.md). Ele consolida o estado atual, testes, pendências e a autorização expressa de commit/push deste checkpoint.

# Nexer — Handoff para ChatGPT Work

Este documento complementa HANDOFF_NEXER_NEXT_CHAT.md e MASTER_PLAN.md. Leia ambos antes de qualquer alteração. Estado em 09/10/2026.

## Decisão MAIS RECENTE (prioridade sobre instruções antigas)
O usuário escolheu a opção B: credenciais corporativas SGIND/IQOS devem ser solicitadas pela interface web do Nexer e usadas apenas na execução/sessão necessária. NÃO configurar usuário e senha próprios do Nexer em `.env`, NÃO executar `scripts/setup_auth.py`, NÃO guardar credenciais corporativas em `.env`, SQLite, arquivos, receitas, parâmetros persistidos, logs, eventos, capturas de tela, localStorage/sessionStorage ou keyring. A interface atual de login local por PBKDF2 é implementação ANTERIOR e precisa ser redesenhada. Credenciais de cada sistema são distintas e só devem ser enviadas ao respectivo sistema. Nunca pedir senhas pelo chat.

ATENÇÃO: sem uma identidade Nexer independente, a tela de entrada de credenciais corporativas não constitui, por si só, autenticação de acesso à API Nexer. Não substituir proteção por login fictício; definir política local segura e verificar acesso indevido. API FastAPI e worker rodam em processos separados: implementar passagem efêmera segura e vinculada à execução, com limpeza ao concluir, cancelar, expirar, sair ou reiniciar. Evitar persistência e vazamento em exceções. Não afirmar que isso já funciona: ainda NÃO FOI IMPLEMENTADO.

## Identidade e ambiente
- Nome: Nexer (antigo RelatPy, somente referência histórica).
- Projeto local: `C:\Users\kis\Downloads\Nexer` em Windows; branch `feat/etapa1-foundation`.
- Remote verificado em 09/10: `https://github.com/hik4s/Nexer.git`.
- Desktop Commander: dispositivo `feb2623d-1907-477f-a9c5-477d2a82c416`, host `ESSPPEROE-0057D`.
- Repositório contém MUITAS mudanças staged/unstaged/untracked preexistentes de renomeação, autenticação e UI. Preservar absolutamente tudo; não resetar, limpar, trocar branch indiscriminadamente ou sobrescrever arquivos. Não alterar master. Não fazer commit/push sem apresentar diff e receber autorização explícita.
- Custo de infraestrutura obrigatório: R$0. Aplicação local; sem backend hospedado pago.
- Usuário quer acompanhar visualmente no VS Code/navegador e aprovar entregas. Responder em português.

## Arquitetura
React/Vite (`apps/frontend`) → FastAPI (`apps/backend`) → Worker (`apps/worker/nexer_worker`) → Runtime Playwright/Microsoft Edge (`apps/runtime`) → SQLite, SSE/eventos, downloads e validação. Existe legado na raiz que deve ser preservado.

## Regra de negócio principal
Login/entrada de credenciais na interface Nexer → SGIND e/ou IQOS → navegação até relatório → preenchimento de parâmetros escolhidos no dashboard → download → validação → destino. Receitas armazenam apenas COMO executar (seletores, navegação, ações, referências a campos e placeholders), nunca datas, empresa e outros valores específicos de uma execução. Esses valores são definidos no dashboard e salvos como snapshot NÃO SENSÍVEL. Segredos não são inputs comuns.

## SGIND e IQOS
- SGIND: `https://indicadoresenergisaess.scl.corp/sgind/#/home`.
- Em 09/10, Edge/Playwright obteve HTTP 200 e redirecionamento para `/sgind/#/login`; título SGINDWeb. Campos observados: `input[name="cre_username"]`, `input[name="cre_password"]`, botão `Logar`. Nenhuma credencial foi enviada. Seletor de sucesso pós-login desconhecido. Autenticação real e download NÃO testados.
- IQOS: integração real NÃO testada; confirmar URL e seletores em ambiente autorizado.
- Não contornar MFA, SSO ou controles corporativos. Testar com credenciais fornecidas apenas na interface local e autorização do usuário.

## Estado técnico verificado
- `apps/backend/app/security.py` mantém sessões em memória; `apps/backend/app/api/auth.py` valida usuário/hash PBKDF2 de `.env` e emite cookie HttpOnly SameSite Strict; `apps/backend/app/main.py` bloqueia APIs sem autenticação configurada. Este modelo está OBSOLETO em relação à decisão mais recente; não simplesmente removê-lo sem substituição segura.
- `apps/frontend/src/pages/LoginPage.tsx`, `apps/frontend/src/auth.tsx`, `apps/frontend/src/lib/api.ts` implementam login antigo, sessão e logout.
- `apps/runtime/credentials.py` usa `KeyringCredentialProvider`; `apps/runtime/session_store.py` persiste estado Playwright no keyring. A decisão mais recente exige NÃO persistir credenciais/estado reutilizável de autenticação corporativa; revisar ambos e chamadas no worker.
- `apps/worker/main.py` carrega storage state do keyring; `apps/worker/nexer_worker/processor.py` usa provider de keyring, auth_guard e salva estado de sessão. Revisar profundamente.
- `apps/backend/app/api/executions.py` persiste `Execution.inputs` em SQLite e proíbe plaintext em variáveis declaradas secret; NÃO passar credenciais pelo campo inputs.
- Últimos testes comprovados ANTES da mudança de requisitos: backend 41 passed; worker 15 passed + 1 E2E skipped; runtime 46 passed + 1 E2E skipped; frontend 17 passed; typecheck e build passaram; `scripts/verify.ps1 -SkipAudit` passou. Auditoria de dependências não executada; esbuild@0.28.2 avisou sobre script não aprovado. Nenhum teste novo após a escolha B.
- Frontend respondeu HTTP 200 em localhost:5173 e 5174 anteriormente, mas verificar processo/checkout atual.
- Tentativas de escrita via Desktop Commander nesta conversa foram bloqueadas pela segurança da ferramenta. NENHUM código foi alterado depois da escolha B. Git status e remote foram lidos; branch `feat/etapa1-foundation`, remote correto, muitas mudanças pendentes.

## Próxima tarefa para Work — execução orientada a entregas
1. Abrir repositório e ler este arquivo, `HANDOFF_NEXER_NEXT_CHAT.md` e `MASTER_PLAN.md`; conferir `git status --short --branch`, `git remote -v`, `git diff --stat` e arquivos untracked. Não sobrescrever mudanças existentes.
2. Projetar modelo seguro de credenciais efêmeras SGIND/IQOS com isolamento por execução e entrega ao worker em processo separado. Garantir que uma falha/restart não resulte em persistência ou vazamento. Considerar que fila SQLite não pode conter senhas. Não chamar login Nexer de autenticação validada sem mecanismo real de proteção da API.
3. Implementar em alterações pequenas e revisáveis: backend, frontend, worker/runtime, limpeza e cancelamento. Desabilitar caminho persistente keyring/storage state no fluxo efêmero e remover instruções `.env`/`setup_auth.py` para senhas.
4. Adicionar testes de não persistência, isolamento entre usuários/execuções/sistemas, limpeza no logout/timeout/cancelamento, bloqueio de API, ausência de segredo em resposta/log/evento e testes de integração worker. Executar suites segmentadas, typecheck, build e verify; reportar resultados reais.
5. Apresentar diff e interface visual para revisão do usuário antes de commit/push. Não declarar login SGIND/IQOS validado sem teste real autorizado.
6. Atualizar handoff e master plan para refletir nova decisão e resultados. Manter custo zero.

## Comandos iniciais
```powershell
Set-Location 'C:\Users\kis\Downloads\Nexer'
git status --short --branch
git remote -v
git diff --stat
git diff --check
# Só após revisar alterações:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify.ps1 -SkipAudit
```

## Regras inegociáveis
Não mexer na master; não descartar alterações; não commit/push sem aprovação; não armazenar segredos corporativos; não inserir credenciais no chat; não gerar custo pago; não declarar etapas/testes concluídos sem evidência; documentar limitações e riscos; manter o usuário informado visualmente.

## Atualização Work — 09/10/2026: desenho aprovado e primeiro módulo
A decisão de credenciais temporárias da opção B prevalece sobre passos antigos de .env/setup_auth/keyring.
Documentos: docs/superpowers/plans/2026-10-09-temporary-credentials-spec.md e 2026-10-09-temporary-credentials.md.
Criados apps/backend/app/ephemeral_credentials.py e apps/backend/tests/test_ephemeral_credentials.py. Cofre isolado, em memória, por execução/proprietário/sistema, com TTL e revogação; ainda NÃO conectado à API, worker ou frontend.
Evidência real: cinco testes novos falharam inicialmente por módulo ausente e depois passaram; suite backend 46 testes OK, exit 0, com PYTHONPATH apps/backend;apps/worker;apps/runtime e NEXER_ENVIRONMENT=test.
Primeiro comando da suite tinha PYTHONPATH incompleto e falhou em test_etapa1_gate (import nexer_worker); comando corrigido sem alterar código.
Aviso StarletteDeprecationWarning sobre httpx/httpx2 observado. Não executar migração de dependências automaticamente.
Diff dos dois novos arquivos revisado. Nenhum commit/push; alterações preexistentes preservadas.
Pendente: pareamento local, canal entre processos, integração do cofre/ciclo de limpeza, substituição keyring no fluxo ativo, formulário corporativo e testes ponta a ponta. Cofre atual expira acesso em get/put, mas remoção periódica sem consultas e limite de capacidade serão responsabilidade da integração.
Nenhuma nova UI entregue nesta rodada; frontend/worker/runtime não retestados porque não foram alterados.
Login SGIND real permanece bloqueado por indicador de sucesso desconhecido; IQOS por URL/seletores desconhecidos. Não solicitar segredos no chat.

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

Verificação desta atualização de texto: teste de CorporateCredentialsFields observado RED pelo aviso antigo e depois GREEN; suite frontend completa 18 testes/10 arquivos passaram; npm run typecheck exit0. Runtime alterado apenas em comentário, sem mudança de política. Não executado build nem login real nesta rodada.

### Evidência home e probe anônimo — 09/10/2026
Usuário forneceu URLs pós-login /sgind/#/home e /iqos/#/home e HTML com app-home-page em ambos. Sucesso candidato composto: URL home exata do sistema + componente visível + formulário login ausente.
Probe REAL na máquina do usuário via Playwright/Edge headless, contextos novos sem cookies/storage state e sem preencher credenciais: home SGIND -> /sgind/#/login, login_visible=true, home_visible=false; home IQOS -> /iqos/#/login, mesmos estados. TLS padrão, exit0. Esta evidência valida redirecionamento anônimo; NÃO é um login automático/E2E autenticado.
corporate_auth.py agora define CorporateLoginDefinition congelada para SGIND/IQOS, URLs/selectores confiáveis independentes da receita e matches_authenticated_home (predicado puro). validate_corporate_url reconhece IQOS e restringe cada sistema ao seu caminho, bloqueando troca SGIND/IQOS, aliases, traversal, caminhos percent-encoded, userinfo, host semelhante, porta externa e HTTP.
Cinco novos testes observados RED (política IQOS ausente, caminhos não restritos, definições/matcher ausentes), depois GREEN. Runtime Ran53 tests OK skipped=1, exit0. Worker Ran19 tests OK skipped=1, exit0. Esses skips são E2E Edge opt-in, não executados. O probe Edge anônimo é separado desses testes.
Interface SGIND/IQOS agora diz "Telas de login e início identificadas. Integração automática em preparação." Campos seguem desabilitados. Teste de texto observado RED antes da alteração.
Ruling: evidência manual+probe permite fixar URL/home/seletores; manter gates API/require_validated_adapter enquanto login seguro do worker não está conectado. Custo: usuário ainda não pode enviar credenciais corporativas por esta UI. Não pedir novamente URL/HTML home já recebidos.
Pendências de implementação, não de dados home: interceptar destinos e restringir scripts no contexto; preencher e validar usando client efêmero; revalidar credenciais/cancelamento durante ações; formulário fora de React Query/storage; teste launcher/E2E autenticado com senha digitada pelo usuário apenas na UI. Mensagem de erro de senha desconhecida pode ser tratada por timeout/código constante. Não habilitar guard de renovação de receita arbitrária.
Branch feat/etapa1-foundation confirmada; mudanças preservadas, sem commit/push. Próxima etapa é ligar definição confiável ao worker, não solicitar nova aprovação para continuar desenvolvimento autorizado.

Verificação final deste bloco: frontend 18 testes/10 arquivos passaram; npm run typecheck exit0. git diff --check exit0 (avisos LF/CRLF). Não executado build, backend sem alterações neste bloco. Nenhum login automático real testado. Testes e predicado não equivalem à integração final do worker; campos corporativos permanecem bloqueados.
