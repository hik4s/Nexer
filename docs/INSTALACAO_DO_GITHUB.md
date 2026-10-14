# Instalar Nexer a partir de um clone/ZIP do GitHub (nucleo atual)

> Documento de desenvolvimento (14/10/2026). **O launcher do nucleo React/FastAPI nao instala dependencias automaticamente.** O procedimento abaixo prepara uma maquina Windows nova. A automacao SGIND/IQOS ainda requer validacao corporativa; nao confundir inicializacao do app com liberacao do primeiro relatorio.

## Requisitos previos
- Windows 10/11 com Microsoft Edge instalado.
- Python **3.12** (com `py -3.12` disponivel) e Node.js/npm compativeis com o `apps/frontend/package-lock.json`.
- Acesso aos registros de pacotes Python e npm; redes corporativas podem bloquear instalacao.
- Pasta extraida integralmente (nao executar de dentro do ZIP); terminal PowerShell aberto na raiz do projeto.
- Nao requer arquivos `.env`, banco SQLite ou `node_modules` publicados no GitHub.
- Acesso corporativo ao SGIND/IQOS **nao e necessario** para instalar ou testar apenas a interface.

## Instalação assistida do zero — recomendada

Na pasta extraída ou clonada, dê duplo clique em **`Instalar-Nexer.cmd`**. O instalador verifica Python 3.12/Node/npm, cria `.venv`, executa `pip install` e `npm ci`, aplica migrações em um banco novo, solicita a criação do usuário LOCAL e, se as portas estiverem livres, abre a interface no navegador.

Ele **não instala Python, Node ou Edge**, não altera um banco existente silenciosamente e **não inicia worker de relatórios**. Se já existir `data/nexer.db`, ele interrompe com orientação; para atualizar uma instalação existente, faça backup e analise antes de usar a opção `-UpgradeExistingDatabase`. Para verificar sem abrir serviços: `powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\install_nexer.ps1 -NoLaunch`.

## Instalar manualmente — somente em uma pasta nova

Alternativamente, execute estes comandos **na raiz do projeto clonado**, sem reutilizar banco existente:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\apps\worker\requirements.txt -c .\scripts\requirements-windows-py312.lock.txt

Push-Location .\apps\frontend
npm ci
Pop-Location

New-Item -ItemType Directory -Path .\data -Force | Out-Null
.\.venv\Scripts\python.exe -m alembic -c .\apps\backend\alembic.ini upgrade head

# Cria credenciais de administracao LOCAIS do Nexer (hash, nao senha em claro).
.\.venv\Scripts\python.exe .\scripts\setup_auth.py

# Abre API e frontend locais para acesso ao dashboard.
.\Abrir-Nexer.cmd
```

**Diferenca importante:** `Abrir-Nexer.cmd` inicia o backend com `--api-only`, deliberadamente sem consumir uma fila antiga. **Nao ha worker executando relatorios nesse modo.** Iniciar o worker real exige o bloco de operacao/homologacao do piloto e o inventario da fila. Nao remova `--api-only` para testar uma instalacao desconhecida.

## O que entra no Git

- Codigo Python/TypeScript, receitas declarativas permitidas e scripts de inicializacao.
- `apps/frontend/package.json` e **`apps/frontend/package-lock.json`** para `npm ci`.
- Os `requirements.txt` do backend/runtime/worker e `scripts/requirements-windows-py312.lock.txt` (versões testadas como constraints), `apps/backend/alembic.ini`, `apps/backend/alembic/versions/*.py` e configuracoes de exemplo.
- Imagens, icones e assets `assets/`, `apps/frontend/public/`, documentacao e testes.
- `data/.gitkeep` para manter a pasta vazia num checkout limpo.
- `*.spec` de PyInstaller **se** existir um spec revisado e necessario para build reproduzivel.

## O que NAO entra

- `.env`, `.env.local`, dados de autenticao corporativa, cookies, tokens e arquivos de chave privada.
- `venv/`, `.venv/`, `node_modules/`, caches e arquivos compilados gerados.
- `data/nexer.db` e demais bancos `*.db`, `*.sqlite*`, WAL/SHM/journal: a estrutura e criada pelas migrations no clone.
- Downloads CSV de usuarios, historicos, logs, screenshots, videos, tracers e estado da execucao.
- Um executavel legado (`Nexer-Atualizado.exe` ou `Nexer.exe`) pode estar presente em branches antigas, **mas nao equivale ao build do nucleo novo**. Nao e fonte de verdade de instalacao.

## Verificacao antes de publicar

No checkout **Git verdadeiro** que recebera o commit, revise:

```powershell
git status --short --branch
git ls-files .env data/nexer.db apps/frontend/package-lock.json apps/backend/alembic.ini
git check-ignore -v --no-index .env data/nexer.db apps/frontend/node_modules/index.js
git check-ignore -v --no-index apps/frontend/package-lock.json apps/backend/alembic.ini apps/backend/alembic/versions/0007_practical_workspace.py .env.example
```

Nos comandos acima, `git ls-files` que ainda mostre `data/nexer.db` ou `.env` e **um problema**, mesmo que a nova regra ignore o arquivo. Remova esses itens apenas **do indice**, apos inspecao e backup apropriados, sem apagar o arquivo local. Um arquivo ja publicado pode continuar no historico Git; trate exposicao de dados/segredos separadamente.

O segundo `git check-ignore` idealmente nao retorna nenhum dos arquivos de projeto indispensaveis. Nao execute `git add -f` em dados ou segredos para contornar protecoes.

## Gate para afirmar que o clone funciona

1. Preparacao numa pasta limpa, com `data/nexer.db`, `.venv` e `node_modules` ausentes no ZIP/clone.
2. `pip install` e `npm ci` com sucesso, sem referencias a caminhos de outra maquina.
3. Migrations `alembic upgrade head` concluindo em banco novo e `pip check` passando.
4. Autenticacao local configurada pela instalacao, API `/version` e frontend iniciando no loopback; pareamento sem impressao de segredos nos logs.
5. Testes sintéticos e verificacao de inicializacao **sem ativar workers em banco de terceiros**.
6. Como etapa separada, worker + SGIND real + relatorio CSV exigem homologacao. **Nao considerar esses passos ja aprovados.**

## Credenciais e separacao entre versoes

A senha de administracao **LOCAL** do Nexer tem hash em `.env` gerado pelo `scripts/setup_auth.py`; nao eh a senha SGIND/IQOS. Credenciais **corporativas** sao informadas na UI em cada execucao e nunca copiadas para `.env`.

A documentacao extensa na raiz do README contem uma secao de **Streamlit/EXE legado**. Nao seguir aquelas instrucoes para instalar o nucleo novo. `Nexer.bat` invoca o executavel legado; para React/FastAPI use `Abrir-Nexer.cmd`.
