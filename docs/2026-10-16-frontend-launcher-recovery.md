# Nexer — recuperação do launcher e do primeiro uso (16/10/2026)

## Diagnóstico confirmado

- A captura de tela de `Nexer-Atualizado.exe`/central Tk mostrava **"Frontend dependencies are missing"** em `scripts/open_nexer.ps1` da exportação `C:\Users\kis\Downloads\Nexer-codex-nexer-stability-artifacts-2026-10-15`.
- A exportação não possuía `.git`, `apps/frontend/node_modules` nem `.venv`. Já possuía `apps/frontend/package-lock.json`, Node v24.19.0 e npm 11.17.0 no Windows.
- A API em `127.0.0.1:8000` estava **ativa na própria exportação**, PID 19556, `scripts/run_local.py --api-only`, `/version` = HTTP 200. Reiniciar a API não instala Vite.
- O diretório `data` continha apenas `.gitkeep`; não existia banco SQLite nem `.env` na exportação. Portanto HTTP 200 da API não bastava para garantir funcionamento das telas após autenticação.

## Reparos reais realizados (Desktop Commander)

1. Executado `npm.cmd ci --prefix apps/frontend --no-audit --no-fund` **na própria exportação**: exit 0, 168 pacotes; Vite e esbuild comprovados.
2. Iniciado Vite para o frontend da mesma exportação, `127.0.0.1:5173` com `VITE_API_URL=http://127.0.0.1:8000`, sem worker. API conservada.
3. Como o SQLite não existia, aplicadas as migrações oficiais **0001 → 0007** em banco novo e vazio na exportação. Comprovação por verificação SQLite em modo read-only: `0007_practical_workspace`, 15 tabelas, exit 0. Nenhum banco anterior foi substituído.
4. `scripts/open_nexer.ps1`: preflight de dependências antes de inicializar nova API, com mensagem orientando `Preparar-Frontend-Nexer.cmd`; mantém `--api-only`.
5. `scripts/manage_nexer.ps1`: ações `start`/`restart` recusam frontend ausente **antes** de interromper uma API ativa.
6. Novos `Preparar-Frontend-Nexer.cmd` e `scripts/prepare_frontend.ps1`: reparação só do frontend via `npm ci` e lockfile, verificação do Node/npm, idempotência sem reinstalar quando Vite existe. Não mexem em banco, credenciais, API ou workers. `-Reinstall` é explícito, não usado aqui.
7. `docs/INSTALACAO_DO_GITHUB.md` atualizado e `tests/test_frontend_recovery.py` adicionado.
8. Arquivos sincronizados, com SHA-256 idêntico, entre a branch local `feat/nexer-guided-artifact-validation-2026-10-16` (`C:\Users\kis\Downloads\Nexer-dev-2026-10-16`) e a exportação usada pelo usuário. Scripts originais da exportação preservados em `temp/recovery-launcher-backup-2026-10-16/` dentro dela.

## Evidências observadas

- 4 testes novos específicos de preparação/preflight: **4/4**, exit 0.
- Suíte inteira em `tests/` da branch local: **20/20**, exit 0.
- Script de recuperação na exportação após instalação: `[OK] Interface ... ja preparada`, exit 0, sem reinstalar.
- `manage_nexer.ps1 -Action start` na exportação: `API_RUNNING`, exit 0; `/version`, `/health` e página React `/` no frontend: **HTTP 200**.
- Microsoft Edge headless real abriu `http://127.0.0.1:5173`, confirmou título de login **Entrar no Nexer** e botão **Gerar novo token** visível; exit 0. Não gerou token nem efetuou login.
- API não foi reiniciada por esta reparação; nenhum worker, relatório SGIND/IQOS, fila real ou migração de banco preexistente foi executado.

## Persistência e limitações

- O Nexer está acessível na máquina em `http://127.0.0.1:5173/`. Se o processo de desenvolvimento do frontend for encerrado, clique em `Abrir dashboard` ou execute `Abrir-Nexer.cmd`; as dependências agora estão instaladas.
- O frontend e a API atuais continuam ferramentas locais, **não** um instalador autossuficiente; para clone em outro PC use `Instalar-Nexer.cmd` em ambiente novo. Se já houver SQLite, revisar backup e política de atualização antes de usar `-UpgradeExistingDatabase`.
- Para entrar, o usuário deve gerar/visualizar o código de pareamento na máquina; nenhum código ou senha foi capturado pelo assistente.
- A exportação não é um checkout Git. A branch de trabalho local, criada a partir de `codex/nexer-stability-artifacts-2026-10-15`, já contém alterações **não commitadas** de validação guiada de downloads de sessão anterior. Nesta etapa somente foram acrescentados os scripts, os testes e a documentação de recuperação; **nenhum commit, push, merge ou alteração da master**.
- SGIND/IQOS real, worker com fila, empacotamento EXE standalone e auditoria do histórico Git permanecem pendentes e separados.
