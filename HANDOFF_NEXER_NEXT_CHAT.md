> ATUALIZAÇÃO 09/10/2026: leia primeiro [CONTINUAR_NEXER_2026-10-09.md](CONTINUAR_NEXER_2026-10-09.md). Ele consolida o estado atual, testes, pendências e a autorização expressa de commit/push deste checkpoint.

# Nexer — handoff para continuar no Codex CLI
Atualizado em 09/10/2026, aproximadamente 16:12 (America/Sao_Paulo).
Leia este arquivo antes de executar ações. Ele substitui as instruções antigas de login .env/keyring neste handoff.

## Objetivo e regras obrigatórias
- App LOCAL, infraestrutura R$ 0: React/Vite → FastAPI → worker → runtime Playwright/Microsoft Edge → SQLite, SSE e downloads.
- Responder em português; usuário quer acompanhar cada etapa visualmente.
- Pasta: C:\Users\kis\Downloads\Nexer. Branch esperada: feat/etapa1-foundation.
- Não alterar master, não descartar mudanças, não usar reset/clean/checkout amplo, não fazer commit/push sem revisão e autorização explícita.
- Há muitas alterações anteriores, inclusive renomeações staged e arquivos untracked. Preservar tudo; não assumir que todo diff pertence ao bloco atual.
- Remote anteriormente verificado: https://github.com/hik4s/Nexer.git. Confirmar novamente em leitura antes de integração/push.
- Usuário autorizou continuar desenvolvimento. Não pedir aprovação novamente para tarefas reversíveis já previstas; commit/push continuam separados.
- Não declarar conclusão/testes sem observar resultado e exit code. Não confundir fixture, teste unitário ou probe anônimo com login corporativo real.
- Renomeação RelatPy → Nexer já feita em ampla parte do projeto; reaproveitar legado apenas quando fizer sentido, sem reintroduzir marca antiga.

## Primeira ação no CLI
Usar o filesystem/PowerShell local do próprio CLI; Desktop Commander não é necessário quando o CLI roda na máquina do usuário.
Confirmar diretório, instruções AGENTS.md aplicáveis e Git em leitura:
```powershell
Set-Location 'C:\Users\kis\Downloads\Nexer'
git status --short --branch
git branch --show-current
git remote -v
git diff --stat
```
Não reiniciar os serviços ou executar o worker automaticamente: pode invalidar a sessão ou processar fila existente.
Se estiver fora da máquina do usuário, NÃO confundir scratch/container com este checkout Windows.
Bridge usada no Work: device feb2623d-1907-477f-a9c5-477d2a82c416, host ESSPPEROE-0057D. Chamadas pendentes retornam call_id; consultar get_tool_result, não repetir a mutação.

## Arquivos de referência
1. Este handoff: visão atual e próximos passos.
2. docs/superpowers/plans/2026-10-09-temporary-credentials-spec.md: especificação de credenciais temporárias.
3. docs/superpowers/plans/2026-10-09-temporary-credentials.md: plano e ledger; há registros históricos, notas recentes prevalecem.
4. docs/development/corporate-login-evidence.md: URLs, seletores e evidência real de SGIND/IQOS.
5. NEXER_WORK_HANDOFF_2026-10-09.md: registro detalhado das rodadas Work.
6. MASTER_PLAN.md: plano mestre; notas finais substituem referências históricas a .env/keyring ou seletores desconhecidos.

## Fluxo de negócio
Pareamento local Nexer → sessão local → credenciais SGIND/IQOS por execução → login corporativo → relatório → parâmetros → download → validação → destino.
Login Nexer NÃO autentica automaticamente SGIND/IQOS.
Receita define COMO (ações, seletores e validações); dashboard define valores de negócio (empresa, datas, filtros, destino).
Persistir snapshot dos parâmetros não secretos e versão da receita. Nunca tratar senha/token como input normal.
Recovery fail-closed; não reenfileirar automaticamente trabalho perdido quando puder duplicar efeitos. Retry/checkpoint/recovery/resume são conceitos distintos.
Heartbeat atrasado não prova que worker estrangeiro vivo morreu. Resume exige regras explícitas de idempotência.

## Segurança aprovada — opção B
- Credenciais corporativas pedidas na web UI, separadas por sistema e execução, somente em memória.
- NUNCA .env, SQLite, receita, snapshot, evento, log, screenshot com segredo, localStorage/sessionStorage, keyring ou storage_state persistido.
- API e worker são processos separados: canal local autenticado, capability efêmera por encarnação, entregue por stdin/pipe herdado; nunca argv/env/arquivo.
- Revogar ao terminar, cancelar, logout, expiração e reinício. Python limpar referências/dicionários NÃO garante zeroização física de strings.
- Não pedir senha, token, cookie ou código de pareamento real no chat.
- Configuração confiável de autenticação é independente das receitas; receitas não escolhem seletores/destinos arbitrários para acessar credenciais.
- Sem scripts arbitrários ou navegação externa no contexto autenticado. Restrições completas deste contexto AINDA precisam ser implementadas.

## Pareamento Nexer — implementado e confirmado pelo usuário
- apps/backend/app/local_pairing.py: código aleatório, uso único, 5 minutos, limite de 5 tentativas, reemissão invalida anterior.
- /auth/login recebe pairing_code SecretStr; cookie nexer_session HttpOnly/SameSite Strict, sessão em memória com relógio monotônico e TTL até 8h.
- /auth/session e /auth/logout; logout/expiração revogam cofre.
- Middleware valida peer loopback, Host e Origin; mutações exigem Origin permitido. NÃO há bypass por NEXER_ENVIRONMENT=test.
- Origens frontend padrão: http://127.0.0.1:5173 e http://localhost:5173. Usar hostname compatível na URL API para cookie SameSite.
- LoginPage tem somente campo Código de pareamento e limpa antes do envio.
- Usuário confirmou acesso real à dashboard com o código local em 09/10; nota antiga API_NOT_LISTENING está superada.
- scripts/setup_auth.py e primitivas PBKDF2 são legado; não executar setup_auth nem restaurar autenticação ativa por .env.
- APIs primitivas de hash/keyring ainda podem existir para testes legados; isso não significa que sejam usadas no fluxo novo.

### Iniciar API sem consumir fila / gerar novo código
```powershell
Set-Location 'C:\Users\kis\Downloads\Nexer'
python .\scripts\run_local.py --api-only
```
Código aparece SOMENTE no console local do usuário. Ctrl+C e repetir gera outro, invalidando sessão/credenciais antigas.
Não capturar stdout desse launcher contendo código real em logs/chat.
Sem --api-only o launcher também inicia worker e pode consumir execuções enfileiradas.
Frontend:
```powershell
Set-Location 'C:\Users\kis\Downloads\Nexer\apps\frontend'
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```
Antes de iniciar, verificar instâncias existentes. UI foi usada em http://127.0.0.1:5173; API em 127.0.0.1:8000.
Não assumir PIDs antigos ainda válidos. Backend não usa auto-reload: alterações entram no próximo reinício; não derrubar sessão do usuário sem necessidade.

## Cofre e canal — implementados
- app/ephemeral_credentials.py: cofre por execution_id/owner/system, cópias defensivas, TTL até 3600s, capacidade128, expiração e revogação.
- app/security.py: credential_vault global, sessões; put_session_credentials serializa put com logout e limita TTL à sessão.
- app/main.py lifespan: sweep_sessions e purge do cofre a cada5s.
- app/worker_channel.py: capability, worker_id por encarnação, owners em memória; resolve exige execução vinculada RUNNING, worker correto, não cancelada e sessão válida.
- Rotas internas: GET /internal/credentials/{id}/{system}, POST /internal/credentials/{id}/release; sem cache.
- nexer_worker/credential_client.py: somente http://127.0.0.1:porta explícita, sem proxy/redirect, respostas limitadas, erros constantes.
- apps/worker/secure_main.py lê bootstrap pelo stdin. scripts/run_local.py configura canal e inicia child pelo pipe.
- Teste com subprocesso separado e servidor HTTP fixture passou. NÃO é E2E completo do launcher/API/worker corporativo.
- Release é idempotente para worker com reserva correta, inclusive após estado terminal.

## Criação de execução — integração preparada, produção bloqueada
- ExecutionCreate.corporate_credentials usa SGIND/IQOS e username/password SecretStr, fora do repr e ExecutionRead.
- app/execution_credentials.py e api/executions.py ligam criação ao cofre antes do commit que publica QUEUED.
- Sistema precisa corresponder à automação; worker da encarnação atual deve estar ONLINE, sem stopped_at e heartbeat até30s.
- Owner vem do cookie e não é persistido. Bind detecta troca de encarnação. Session lock é liberado antes de channel lock para evitar inversão channel→session→vault.
- Rollback de IntegrityError ou outra exceção pré/durante commit revoga credenciais e vínculo. Dicionário plaintext transitório é limpo.
- Cancelamento revoga antes de commit; logout/TTL/release também exercitados com credenciais existentes.
- require_validated_corporate_auth na API e require_validated_adapter no runtime AINDA bloqueiam fluxo real.
- Somente testes usam dependency override para permitir canários sintéticos. NÃO existe request/.env flag para contornar o gate.
- Novo test_execution_credentials.py tem12 testes: ausência no dump SQLite/respostas, claim, release, rollback, cancelamento, logout/TTL, worker stale/canal ausente, sistema errado, mudança de encarnação e logout durante submissão.
- Pendência: mapa channel._owners pode reter vínculos/tokens após expiração/logout até release/restart. Fazer limpeza periódica segura; evitar inversão de locks.

## SGIND e IQOS — dados já conhecidos; não pedir novamente
Origem: https://indicadoresenergisaess.scl.corp
| Sistema | Login | Após login | Formulário |
| --- | --- | --- | --- |
| SGIND | /sgind/#/login | /sgind/#/home | form#idFormLogin |
| IQOS | /iqos/#/login | /iqos/#/home | form[name="form"] |

Dentro do formulário:
- Usuário: input[name="cre_username"].
- Senha: input[name="cre_password"][type="password"].
- Enviar: button[type="submit"], rótulo Logar.
- Tela inicial: app-home-page visível; não usar atributos Angular _ngcontent/pc nem classes ng-valid/ng-dirty.
- Usuário forneceu HTML de login e home dos dois sistemas após login manual.
- Regra candidata de sucesso: URL home EXATA do sistema + app-home-page visível + formulário login ausente.
- Probe REAL Edge headless em09/10, contextos novos sem cookies/storage_state, TLS padrão, sem preencher credenciais: navegar a ambas as home redirecionou à login do próprio sistema; input de usuário visível e home ausente. Exit0.
- Isso comprova acesso anônimo/redirecionamento e sustenta o indicador; NÃO comprova login automático autenticado/download real.
- corporate_auth.py: CorporateLoginDefinition frozen, get_login_definition e matches_authenticated_home (predicado puro).
- validate_corporate_url agora permite SGIND/IQOS no próprio caminho /sgind/ ou /iqos/, HTTPS/host/porta443 exatos; bloqueia cross-system, userinfo, hosts similares, alias/traversal, backslash/whitespace e caminhos percent-encoded.
- Política ainda não é interceptação de requests do contexto. Não presumir que o navegador inteiro já esteja restringido.
- Mensagem de senha incorreta não foi inspecionada; usar timeout/erro constante, sem copiar erro/browser body para persistência.

## Worker/runtime e interface — limites reais
- Worker ativo não lê/grava keyring/storage_state; provider padrão nega credenciais.
- Processor rejeita authentication.renewal não validada antes de criar navegador e persiste AUTOMATION_FAILED em vez de erro bruto.
- Page/context é fechado no finally. Guard corporativo confiável, preenchimento pelo client e revalidação durante ações AINDA não estão conectados.
- NewExecutionPage exibe CorporateCredentialsFields: campos SGIND/IQOS DESABILITADOS, sem coletar estado/senhas.
- Texto atual: "Telas de login e início identificadas. Integração automática em preparação."
- Ao habilitar depois, enviar corpo corporativo por chamada direta fora do cache/mutation React Query; limpar sucesso/falha/logout/unmount.
- Screenshot anterior de tela VAZIA de pareamento: docs/development/previews/pairing-login.png. Não capturar tela com credenciais.

## Últimas verificações realmente observadas
Executadas em rodadas distintas em09/10; não alegar execução simultânea de um gate final inteiro.
- Backend: Ran74 tests, OK, exit0 após bloco de submissão/cofre. Não reexecutado no último bloco, que não alterou backend.
- Worker: Ran19 tests, OK (skipped=1), exit0 no último bloco.
- Runtime: Ran53 tests, OK (skipped=1), exit0 após5 testes novos de política/definição/sucesso.
- Frontend:18 testes/10 arquivos passaram; npm run typecheck exit0 no último bloco.
- Build frontend passou em rodada anterior do pareamento; NÃO foi rerodado nas últimas mudanças de texto/runtime.
- git diff --check exit0; avisos LF/CRLF. Sem commit/push.
- Skips são E2E Edge opt-in, não testes reais de credenciais. Probe anônimo Edge descrito acima é separado.
- StarletteDeprecationWarning sobre httpx/httpx2 é legado observado; não migrar dependências automaticamente.
- Auditoria de dependências não foi executada. Evitar verify.ps1 indiscriminado: pode instalar dependências.
- Testes novos de política e submissão tiveram falhas RED observadas antes da implementação; casos adicionais de robustez também verificaram comportamento já implementado.
- Revisão das fatias pelo próprio autor; revisão independente da branch completa ainda pendente.

### Comandos segmentados
```powershell
Set-Location 'C:\Users\kis\Downloads\Nexer'
$env:PYTHONPATH='apps\backend;apps\worker;apps\runtime'
python -m unittest discover -s apps\backend\tests -v
python -m unittest discover -s apps\worker\tests -v
$env:PYTHONPATH='apps\runtime'
python -m unittest discover -s apps\runtime\tests -v
Set-Location 'C:\Users\kis\Downloads\Nexer\apps\frontend'
npm test -- --pool=threads --maxWorkers=1
npm run typecheck
npm run build
```
Executar conforme mudança; não repetir suites já verdes sem motivo. Ler exit code imediatamente no PowerShell.
Testes backend de negócio usam tests/test_client.py com sessão sintética explícita; rotas de auth usam clientes próprios.

## Próxima etapa no Codex CLI
1. Ler spec/ledger atuais e inspecionar worker processor/main, runtime browser_manager/actions/runner/auth_guard, API de execução e frontend Nova execução. Não reimplementar módulos já concluídos.
2. Ligar definições confiáveis de SGIND/IQOS ao worker por sistema da automação, separadas da receita. Login via client efêmero somente após reserva válida; verificar URL final antes de preencher e regra de home depois do envio.
3. Implementar/testar restrições do contexto autenticado: destinos permitidos, redirecionamentos, popups/iframes conforme necessário, bloqueio de scripts/ações capazes de extrair segredos. Não usar seletores de renovação arbitrários vindos da receita.
4. Revalidar autorização/TTL/cancelamento durante execução e fechar contexto ao revogar; limpar owners expirados/terminais sem deadlock.
5. Completar testes API→worker em processos reais e cleanup, incluindo falhas/restart. Somente então substituir gates constantes por política confiável completa.
6. Habilitar campos efêmeros da UI e envio direto fora de cache/storage, com testes de limpeza em sucesso/falha/logout/unmount. Não liberar formulário antes de o worker suportar o fluxo.
7. Usuário digita credenciais exclusivamente na UI local para teste autenticado. Validar sucesso SGIND/IQOS e posteriormente relatório/download, sem registrar segredos. Não inventar resultados nem testar login usando sessão pessoal capturada.
8. Apresentar evolução visual e diffs, manter branches/mudanças preservadas; revisão final antes de qualquer commit/push.
Não há mais falta de URL/HTML home para continuar desenvolvimento. O bloqueio atual é implementação e validação do fluxo integrado.

## Prompt para iniciar a próxima sessão
"Continue o Nexer lendo HANDOFF_NEXER_NEXT_CHAT.md e os documentos indicados. Confira Git em leitura e preserve todas as mudanças. Não altere master nem faça commit/push. Continue a ligação segura dos adaptadores SGIND/IQOS ao worker e às credenciais temporárias. URLs, seletores e regra de home já foram fornecidos e o redirecionamento anônimo foi verificado. Não restaure .env/keyring/storage_state nem habilite o formulário antes de completar o fluxo seguro. Trabalhe em etapas verificadas e mostre o progresso."

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
