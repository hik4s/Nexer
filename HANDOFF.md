# Handoff — Nexer — 2026-10-13

## Retomar no próximo chat

Leia este arquivo primeiro e depois `CONTINUAR_NEXER_2026-10-13.md`, `docs/development/CURRENT_STATE.md` e os planos em `docs/superpowers/plans/`. Este handoff prevalece sobre referências históricas a alterações ainda não commitadas: o usuário solicitou salvar o checkpoint completo, dar commit e push em uma branch nova.

- Repositório: https://github.com/hik4s/Nexer
- Branch deste checkpoint: `codex/nexer-reusable-flows-2026-10-13`.
- Origem: HEAD `4f7e73c` da branch `feat/etapa1-foundation`, incluindo as alterações locais acumuladas das últimas sessões.
- Workspace: `C:\Users\hikas\Documents\ChatGPT\Nexer`; Windows/PowerShell, timezone America/Sao_Paulo.
- A branch original e o legado são preservados. Não houve merge para main, reset ou exclusão dos arquivos anteriores. A nova branch isola a publicação; não garante ausência de conflitos em um merge futuro.
- O usuário autorizou implementar melhorias reversíveis sem pedir novamente permissão e autorizou explicitamente este commit/push. Não confundir autorização de desenvolvimento com disponibilidade de credenciais ou rede corporativa.

## Objetivo do produto

Nexer deve ser um aplicativo simples e escalável de automações, útil também fora do ambiente empresarial. Pilares: cadastrar configurações de login por site, gravar fluxos reutilizáveis no Edge, personalizar os parâmetros em cada execução e selecionar vários fluxos para iniciar um lote com progresso/cancelamento individuais. Identidade minimalista com os ativos originais de `nexer-logo-kit`.

Requisitos confirmados:

- Gravar locais e ações; nunca persistir os valores digitados ou a seleção usada na gravação como defaults.
- Data inicial/final, empresa e demais campos aparecem com seus tipos e regras no dashboard. As opções de listas são carregadas do site ao preparar a execução, não copiadas da gravação.
- Nomes dos campos vêm dos rótulos da página e podem ser revisados depois de gravar.
- Compartilhar o preenchimento de credenciais entre destinos do mesmo grupo; cada destino mantém configuração e sessão próprias.
- Nomes de downloads mudam entre execuções: usuário escolheu padrão configurável. Procurar de cima para baixo na central do site e baixar a primeira correspondência, preservando o nome atual do arquivo recebido do site.
- Validação SGIND/IQOS será em outro computador com acesso à rede corporativa.

## Implementado neste checkpoint

Arquitetura: React/TypeScript/Vite → FastAPI/SQLite/Alembic/SSE → supervisor com processos de worker independentes → Playwright/Edge. Legado Streamlit preservado.

1. Perfis de login versionados, seleção de três alvos no Edge, sucesso por URL/marcador e credenciais efêmeras. Grupos de acessos para vários destinos; template reaproveita alvos, sem copiar regra de sucesso/origins. Credenciais fora de receitas, banco, eventos e cache de consultas.
2. Gravação parametrizada: cliques, preenchimentos, controles nativos e alguns personalizados, scroll/hover/drag, frames de mesma origem, shadow DOM aberto e abas do fluxo. Inputs viram placeholders, sem valores da gravação.
3. Cadastro guiado Site → Acesso → Gravação → Campos → Publicar, importação de JSON e edição de labels no Studio. Publicar não inicia execução.
4. Toolbar **Parar gravação** na página principal do Edge; conclusão por binding privado, toolbar excluída da receita. Interface segue automaticamente para Campos após DONE. Somente controles efetivamente editados geram parâmetros; nomes vêm de label/aria-labelledby/aria-label/legend. `base_url` é configuração separada de Site.
5. Downloads em tabelas/listas identificáveis registram `collection: {rows, name, button, pattern}`. Padrão glob solicitado na nova execução, ex.: `Relatorio_*.xlsx`. Nenhum nome/conteúdo de arquivo usado na gravação é copiado. Runtime escolhe primeira linha visível correspondente na ordem do DOM, aguarda até timeout, respeita cancelamento, falha sem correspondência e preserva `suggested_filename`. Impede sobrescrever arquivo já salvo na mesma execução.
6. Lotes atômicos/idempotentes, até 20 itens, processos independentes (supervisor padrão 2, configurável 1–4), isolamento de sessões/downloads, cancelamento individual e do lote. Worker perdido não reassocia credenciais.
7. Meus fluxos/Acessos/Execuções; identidade do kit; busca/seleção de fluxos, favoritos, repetição de execução/lote, parâmetros comuns compatíveis, datas rápidas e resumo antes da confirmação. Listas comuns usam interseção das opções atuais por valor e label; mudar período limpa escolhas dependentes.

Arquivos centrais:

- UI: `apps/frontend/src/pages/{Dashboard,NewFlowPage,NewBatchPage,LoginProfilesPage,StudioPage}.tsx`; `components/RecipeField.tsx`; `lib/practical.ts`.
- Gravação: `scripts/record_recipe.py`, `scripts/record_flow.py`, `apps/recorder/nexer_recorder/{capture.js,compiler.py}`; serviço `apps/backend/app/services/flow_recordings.py`.
- Downloads: `apps/runtime/actions.py` e `apps/runtime/recipe.py`.
- Perfis/lotes: APIs `apps/backend/app/api/{login_profiles,execution_batches,workspace}.py`; supervisor `scripts/run_local.py`.
- Migrações novas: `0004_login_profiles`, `0005_execution_login_profiles`, `0006_execution_batches`, `0007_practical_workspace`.
- Referências de produto e evidência: `apps/recorder/README.md`, `docs/development/VISUAL_IDENTITY.md`, arquivo de continuidade.

## Próximas melhorias aprovadas para planejamento

Estas seis propostas foram aceitas pelo usuário ao pedir salvar o contexto. **Ainda não foram implementadas**. Prioridade recomendada: 1 e 2.

1. **Gravar sites externos autorizados.** Expandir do HTTP local para HTTPS com política explícita de origens, navegação/redirects/popups e cancelamento seguros. Validar em sites reais fornecidos pelo usuário antes de prometer compatibilidade. Perfis HTTPS existentes não tornam o gravador compatível com qualquer site.
2. **Revisão simples após gravar.** Mostrar nomes e tipos legíveis (Data inicial — data; Empresa — lista), sequência compreensível de ações e deixar identificadores/seletores em Avançado. Hoje o editor ainda expõe `input_001` e os detalhes de seletores.
3. **Verificar padrão de download antes de baixar.** Botão “Verificar arquivo correspondente” mostra o item que seria escolhido na central, sem disparar download. Respeitar acesso efêmero e não persistir conteúdo/credenciais inadvertidamente. Hoje existe seleção por padrão somente durante execução.
4. **Obrigatoriedade e dependências mais claras.** Mensagens como “Escolha a empresa para carregar as regionais”, conservando tipos/regras do site. Hoje regras e invalidação de listas existem, mas explicação explícita de dependências pode melhorar.
5. **Erros com solução e regravação de etapa.** Identificar alvo alterado e permitir “Regravar esta etapa” sem refazer o fluxo inteiro. Hoje não existe reparo seletivo da gravação.
6. **Reexecutar apenas falhas de um lote.** Preparar somente itens que falharam, permitir correção de parâmetros e pedir credenciais novas. Hoje há repetição de execução/lote, mas não este atalho específico.

## Limites e usabilidade real

- Núcleo funcional em testes locais; não declarar pronto para produção ou compatível com todos os sites.
- Gravador direto ainda aceita somente HTTP loopback, sem query/fragment/credenciais na URL. Sites externos exigem expansão controlada/adaptação; receita preparada pode ser importada.
- Gates SGIND/IQOS continuam fechados. Não há validação corporativa nesta máquina.
- O banco real não foi migrado e nenhuma fila real foi iniciada na última rodada. Aplicar migrações na instalação real antes de uso; validar configuração existente e preservar dados.
- Prévia `http://127.0.0.1:4173` é somente visual, com dados de exemplo. POSTs de mutação bloqueados; consulta de opções devolve catálogo sintético. Não é backend/workers reais. Servidor ignorado `temp/preview_identity.py`, último PID observado 5448; confirmar se ainda existe antes de operar e nunca encerrar processos genéricos do Edge.
- Centrais devem ordenar os mais recentes primeiro: runtime segue ordem do DOM, sem ordenar por timestamp. Estruturas particulares ou nome fora da primeira coluna exigem revisar seletores. Não instrumenta a interface de downloads do próprio Edge.
- Downloads espontâneos/sem controle identificado, uploads, canvas, shadow fechado, frames de outra origem, MFA/CAPTCHA e componentes particulares não têm cobertura universal. Controles Baixar/Download, links `download` ou seletores declarados são reconhecidos.
- Validação de receita no Studio é estrutural; não comprova execução real no site.
- Distribuição final/Nexer.exe não foi atualizada nem validada nesta rodada.

## Evidência mais recente

- Frontend: **50 testes em 17 arquivos**, build TypeScript/Vite passou.
- Recorder: **19 testes com Edge opt-in**, todos passaram; rótulos, canários ausentes, toolbar, downloads em tabela/lista e replay com valores novos.
- Runtime: **109 testes**, OK, 10 skips de cenários opt-in.
- Backend: **112 testes**, OK, 13 skips; migrações verificadas em bancos temporários.
- Protocolo privado de gravação: **2 testes**, incluindo Edge real finalizando pela toolbar, passaram.
- Evidência anterior ainda válida: worker32/1skip; contenção Windows4; dois workers reais com downloads simultâneos, cancelamento individual e sessões isoladas.
- QA desktop/mobile: campos e configuração de central sem overflow/erros. Artefatos ignorados em `temp/recording-fields-*.png` e `temp/practical-*.png`.
- Revisões independentes corrigidas com regressões RED→GREEN: compatibilidade antes de todas receitas carregarem; resumo obsoleto por controles programáticos; texto Baixar contaminando nome em listas. Não repetir revisão apenas para confirmar correções já testadas.
- `git diff --check` passou. Patch cumulativo local `temp/NEXER_PATCH_2026-10-13.patch` regenerado e validado por reverse check; não vai ao Git por ser artefato ignorado.

Comandos úteis na raiz (sem instalar dependências novamente se já presentes):

```powershell
$env:PYTHONPATH='apps/runtime;apps/recorder'
$env:NEXER_RUN_RECORDER_E2E='1'
.venv/Scripts/python.exe -m unittest discover -s apps/recorder/tests
.venv/Scripts/python.exe -m unittest discover -s apps/runtime/tests

$env:PYTHONPATH='apps/backend;apps/runtime;apps/worker'
$env:NEXER_ENVIRONMENT='test'
Remove-Item Env:NEXER_RUN_RECORDER_E2E -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m unittest discover -s apps/backend/tests

Push-Location apps/frontend
npm test
npm run build
Pop-Location
```

## Como continuar

Inspecionar a branch/estado antes de editar; preservar o checkpoint e o legado. Começar pelo suporte a gravação de sites externos e simplificação da revisão, seguindo os requisitos acima. Pedir apenas URLs/informações realmente ausentes; não repetir perguntas já respondidas sobre opções, tipos, lotes ou padrões de nomes. Atualizar este handoff com decisões, novas evidências e limites; não marcar o projeto inteiro ou etapa corporativa concluídos por haver apenas testes locais verdes.


---

## Handoff anterior preservado (histórico; usar o checkpoint acima)

# Nexer — Handoff

Este arquivo é o ponto de retomada quando a conversa atual expirar.

## Bootstrap

Continue o desenvolvimento do Nexer no repositório `hik4s/Nexer`. Leia `MASTER_PLAN.md`, `docs/development/CURRENT_STATE.md`, `HANDOFF.md` e consulte GitHub/Linear/CI. Trabalhe exclusivamente na branch isolada da nova arquitetura e não altere o legado em `master`. Use TDD para código funcional, execute os testes e só registre avanço após verificação real.

## Estado atual

Branch: `feat/etapa1-foundation`

A Etapa 1 já possui:
- FastAPI + SQLite + Alembic;
- automations + versionamento/teste/publicação;
- executions + cancelamento + snapshot da versão;
- inputs parametrizados;
- SSE persistido;
- Worker com lifecycle, heartbeat, claim e processor;
- Runtime declarativo v1 + ActionRegistry;
- Edge via Playwright + Browser Manager;
- download/validação de arquivo;
- credenciais via keyring/credential_ref;
- AuthenticationGuard com tentativa única + verificação antes dos passos;
- frontend React/TypeScript com Dashboard, Automações, Execuções, Nova execução, Diagnóstico e Destinos;
- piloto real Worker → Edge → download → persistência no Windows;
- teste de Gate API → Worker → Runtime;
- scripts de continuidade e verificação.

## Evidência

Últimas validações locais:
- backend: 29 testes OK;
- worker: 9 testes OK (E2E real opt-in);
- runtime: 30 testes OK (E2E real opt-in);
- frontend: 9 testes OK + typecheck + build;
- cancelamento cooperativo: OK;
- política de segredo: OK;
- Edge real: OK.

## Trabalho em andamento

1. validar CI verde da branch isolada após correções do filtro Windows e harness frontend;
2. concluir integração de autenticação real, incluindo diagnóstico e restauração de sessão autorizada;
3. frontend de destinos;
4. manutenção/criação de receitas pelo Studio;
5. watchdog, retry, checkpoints e recovery;
6. migração controlada de automação real;
7. gate formal da Etapa 1.

## Regras

- `master` é legado e não deve ser substituído;
- nenhuma credencial/token em código, logs, fixtures ou receitas;
- não considerar código escrito como concluído sem teste e evidência;
- preferir desenvolvimento remoto; usar Windows/Edge real apenas quando a validação do comportamento local exigir;
- ao final de um bloco relevante, atualizar `CURRENT_STATE.md` e este arquivo.

## Latest verification - 2026-10-08

- Backend: 31/31 tests OK after the verification harness PYTHONPATH fix.
- Worker: 9 tests OK; real Edge E2E remains opt-in.
- Runtime: 30 tests OK; real Edge E2E remains opt-in.
- Frontend regression: 3/3 targeted tests OK.
- Frontend typecheck and production build: OK.
- Commit pushed: `328624db3c17d809584b2ade0e5beeaa9dc7eee9`.
- GitHub Actions run 277 is still in progress.

## Latest dependency/auth verification - 2026-10-08

- Local `.venv` created and all declared Python dependencies installed successfully; `pip check` passed.
- Frontend dependencies installed; lockfile generated; npm audit: 0 high-severity vulnerabilities found.
- Backend 31/31, Worker 11/11, Runtime 39/39, legacy smoke 4/4 passed.
- Real Edge Runtime pilot + Worker E2E: 2/2 passed.
- Authentication foundation now restores/persists Playwright session state through OS keyring and supports controlled form renewal without exposing secrets.
- Python `pip-audit` was attempted but did not complete; keep security audit open until CI/local audit finishes.

## CI blocker found and fixed - 2026-10-08

- CI run 281 exposed a pre-existing syntax error in the legacy `splash.py` (truncated file).
- The missing splash/bootstrap tail was restored on the feature branch.
- Exact CI-style syntax check now passes for 98 Python files; legacy smoke remains 4/4.

## Authentication diagnostics - 2026-10-08

Added non-sensitive authentication configuration counters to `/diagnostics` and surfaced them in the frontend. Backend full suite is 32/32; runtime 43/43, worker 11/11, legacy smoke 4/4; frontend targeted diagnostic test 1/1.

## Destination CRUD - 2026-10-08

- Backend Destinations now supports create/list/get/update/delete.
- Update validates duplicate codes and required path references.
- Frontend Destinations now supports create/edit/enable-disable/delete with confirmation.
- Frontend API helper now handles HTTP 204 responses correctly.
- Destination backend tests: 6/6 passed.
- Frontend full suite: 8 files / 14 tests passed.
- Frontend typecheck: OK.
- Frontend production build: OK.
- Integrated verification: backend 35/35, worker 11/11 (1 real Edge test skipped without opt-in), runtime 43/43 (1 real Edge test skipped without opt-in).
- GitHub Actions run 289 for commit a1979b7 is green, including Python dependency security audit and frontend dependency audit.
- Local pip-audit did not complete on this Windows executor; do not claim the local audit green.

## Latest continuation - 2026-10-08

- Remote branch confirmed: `feat/etapa1-foundation`.
- Current remote HEAD before the Studio changes: `e76618a93d7566befc089ef63680cc2b1d1b89e2`.
- GitHub Actions run 293 (`37821114007`) is **green** for that commit; Python and frontend jobs passed, including dependency audits.
- Added Studio foundation: create automation → edit declarative JSON recipe → save version → test → publish.
- Added `/studio` frontend route/navigation and API helpers.
- Studio regression: 1/1; frontend full suite: 9 files / 15 tests; typecheck/build: OK.
- Next recommended work remains resilience/recovery and then controlled real-automation migration, while keeping the formal E1 gate explicit.

## Final evidence - Studio block - 2026-10-08

- Studio implementation is pushed at `1d5bd08c6357e202865095f1936cbd1ec69aa658`.
- GitHub Actions run 295 (`37822119458`) is green for that commit, including dependency security audits.
- Local verification without the blocking Windows pip-audit step passed: backend 35/35, worker 11/11 (1 opt-in Edge E2E skipped), runtime 43/43 (1 opt-in Edge E2E skipped), frontend 9 files / 15 tests, typecheck and build.
- Next priority: resilience/recovery (watchdog, retry, checkpoints, recovery) followed by controlled migration of one real report automation and the formal E1 gate.

## Resilience microblock - 2026-10-08

- Implemented bounded, explicit per-step retry policy in Runtime v1.
- Syntax: `retry: { "max_attempts": 2, "backoff_ms": 500 }` on a recipe step.
- `max_attempts` is limited to 1-5 and `backoff_ms` to 0-60000.
- Default is one attempt; existing recipes keep current behavior.
- Verified success-after-retry and hard retry limit with tests.
- Full runtime suite: 46/46; integrated verification passed without local pip-audit; frontend 9 files / 15 tests, typecheck/build OK.
- Next resilience increments: checkpoint persistence/resume and controlled whole-execution recovery, with care around duplicate side effects.

## Latest resilience/recovery block - 2026-10-08

- Added persistent Runtime checkpoints through the existing `checkpoints` table.
- Added WorkerService stale-execution recovery with process-liveness protection and `WORKER_LOST` fail-closed semantics.
- WorkerLoop performs recovery once after registration; previous Worker incarnations are covered.
- Worker: 14/14; Runtime: 46/46; Frontend: 9 files / 15 tests; typecheck/build OK.
- The automatic whole-execution replay path is intentionally not implemented yet because unsafe duplicate side effects must be handled explicitly.

## Latest resilience block - watchdog - 2026-10-08

- Added a background Worker maintenance loop with configurable 5s default interval.
- Heartbeat and stale-execution recovery now continue during long-running automations instead of waiting for `process_once()` to return.
- Recovery remains conservative: live foreign processes are not recovered from heartbeat staleness alone, and lost executions are failed with `WORKER_LOST` instead of auto-replayed.
- Worker suite: 15/15; Runtime: 46/46; Backend: 35/35; Frontend: 9 files / 15 tests; typecheck/build OK.
- Local integrated verification passed with `scripts/verify.ps1 -SkipAudit`; local `pip-audit` is still not used as a green signal because the Windows executor can block there.
- Next priority: controlled manual whole-execution retry/resume semantics with explicit side-effect/replay safeguards, then real automation migration and formal E1 gate.
