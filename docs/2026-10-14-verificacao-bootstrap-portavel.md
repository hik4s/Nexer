# Nexer - verificacao do bootstrap Windows (14/10/2026)

## Escopo e fonte
- Repo: `https://github.com/hik4s/Nexer.git`; branch de origem `codex/smart-recorder-handoff-2026-10-14` no SHA `6631b6bff1bec6ea05bab430235caa9d4d01b70f`.
- Nova branch LOCAL, sem commit e sem push: `feat/nexer-portable-bootstrap-2026-10-14`.
- Checkout de desenvolvimento: `C:/Users/kis/Downloads/Nexer-bootstrap-test-2026-10-14`.
- Teste de distribuicao em **ZIP extraido da arvore Git preparada com git write-tree + git archive**, independente de `.git`, `.venv`, `node_modules` e banco.
- Ambiente: Windows corporativo, Python 3.12.10, Node 24.19.0, npm 11.17.0; nao e comprovacao de outras maquinas.

## Mudancas locais aguardando revisao e commit
- `Instalar-Nexer.cmd` e `scripts/install_nexer.ps1`: bootstrap fail-closed; cria .venv, instala requisitos pip com constraints, npm ci, pip check, migrations em banco novo, solicita configurar login LOCAL e abre launcher API-only por padrao.
- `scripts/requirements-windows-py312.lock.txt`: 32 pacotes com versoes exatas observadas no primeiro teste.
- `.gitignore`, `.env.example`, `data/.gitkeep`, `README.md`, `docs/INSTALACAO_DO_GITHUB.md`, `tests/test_portable_distribution.py`.
- `data/nexer.db` retirado **somente do indice Git** da nova branch com `git rm --cached`; arquivo original da copia de desenvolvimento foi PRESERVADO no disco. O arquivo ja estava versionado na branch remota historica: avaliar privacidade/retencao antiga separadamente. Nada foi enviado.
- Gitlink aninhado `Nexer` legado nao foi inicializado ou alterado.

## Evidencias registradas
1. `git clone --single-branch --branch codex/smart-recorder-handoff-2026-10-14`, sem submodulos; criada a branch de trabalho acima.
2. `git archive` da arvore preparada gerou pacote; verificacoes: sem `.git`, sem `.venv`, sem `apps/frontend/node_modules`, sem `data/nexer.db`; com instalador, lockfiles e migrations.
3. Primeira instalacao isolada executada com `-SkipAuthSetup -NoLaunch` (somente QA, sem configurar conta pessoal): ambiente Python criado, pip instalou dependencies, `pip check` sem conflitos, npm ci instalou 168 pacotes, Alembic terminou `0007_practical_workspace`, exit 0. NENHUM worker ou servidor aberto.
4. Smoke da API via FastAPI TestClient com host e cliente loopback: GET `/version` = 200, GET `/health` = 200. Requisicao TestClient padrao (host `testserver`) foi inicialmente 403 conforme middleware de seguranca e nao indica defeito de instalacao.
5. Frontend em ambiente novo: `tsc -b` exit 0, Vite build 119 modulos, exit 0.
6. Segunda instalacao na **mesma pasta TEMPORARIA** com `-UpgradeExistingDatabase -SkipAuthSetup -NoLaunch` e constraints pinadas: `pip check` OK, `npm ci` 168 pacotes, migration head sem erro, exit 0.
7. `tests/test_portable_distribution.py`: 5 testes, todos passaram (sem skips); PowerShell Parser erros=0; `git diff --cached --check`=0.
8. Arvore final preparada: `git write-tree` = `253760b74e3ebe81285a836504a95bad11e93ebf`, 447 caminhos; sem `.env`, `data/nexer.db` e node_modules; com `Instalar-Nexer.cmd`, arquivo de constraints, alembic migrations e package-lock.

## Limitacoes / nao aprovado nesta etapa
- Teste do prompt interativo de senha local e abertura real por duplo clique nao realizados; o instalador novo usa `scripts/setup_auth.py` existente e `scripts/open_nexer.ps1` existente.
- Nao executadas suites completas de backend/runtime/worker nem testes reais SGIND/IQOS.
- Nao foi criado novo executavel Windows nem instalador MSI; `Instalar-Nexer.cmd` exige Python 3.12 e Node/npm previamente instalados e rede de pacotes funcional.
- As portas normais 8000 e 5173 estavam ocupadas pela instancia preexistente; nao foram reiniciadas nem usadas no teste.
- Npm 11 exibiu aviso de `esbuild postinstall` sob `allow-scripts`; frontend mesmo assim compilou corretamente. Manter sob observacao.
- Reproducibilidade dentro dos limites: pins PyPI e lockfile npm; a disponibilidade futura de pacotes/rede, autorizacoes corporativas e versoes de Edge nao e garantida.
- A branch remota ainda tem o banco historico ate que a nova branch seja revisada, commitada e enviada. Nunca empurrar `master` por engano.

## Proximos passos antes de disponibilizar no GitHub
1. Revisar diff staged e scan de dados/segredos (especialmente historia do banco); confirmar branch e remote.
2. Homologar duplo clique em outra maquina ou VM Windows com portas livres e credenciais LOCAlS criadas pelo usuario (sem enviar senha no chat).
3. Opcional: CI de instalacao/teste de portabilidade e consideracao de instalador autocontido para quem nao possui Python/Node.
4. Somente depois do aceite, `git commit` e `git push -u origin feat/nexer-portable-bootstrap-2026-10-14` (sem merge/PR automáticos).
