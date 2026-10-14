# Nexer

O Nexer está evoluindo para um aplicativo local de **automações web reutilizáveis**, voltado a tarefas pessoais e profissionais. O núcleo em desenvolvimento usa React, FastAPI, SQLite e Playwright com Edge.

Os pilares do produto são **automações**, **cadastro de perfis de login**, **gravação de fluxos** e **execução de vários fluxos por lote**. Perfis guardam a configuração dos campos, com credenciais informadas somente ao executar. O núcleo inclui seleção de alvos no Edge, receitas versionadas, campos parametrizados, preparação/acompanhamento de lotes e dois workers isolados por padrão. A validação atual usa sites locais sintéticos; os gates SGIND/IQOS continuam fechados.

A interface usa a identidade Percurso do `nexer-logo-kit`: grafite, branco e fundo suave, logo original, navegação lateral, busca de fluxos e cartões selecionáveis. Consulte [a integração visual](docs/development/VISUAL_IDENTITY.md).

O workspace simplificado reúne **Meus fluxos**, **Acessos** e **Execuções**. Inclui cadastro guiado, grupos de acesso com destinos distintos, rotinas favoritas, campos compartilhados com ajustes individuais, períodos rápidos, resumo antes de iniciar e repetição com parâmetros revisados. Gravação direta aceita HTTPS com rotas como `#/caminho`, em modo de preparação para login manual, e HTTP local. A tela de pareamento permite gerar novo token no console; Acessos oferece exclusão confirmada de perfis sem vínculos. Execução autenticada corporativa continua sujeita à validação própria. Aplicar migrações até0007 antes de usar a instalação real.

- [Handoff consolidado e próximos passos](HANDOFF.md)
- [Verificação completa antes do commit](docs/2026-10-14-verificacao-handoff.md)
- [Direção e desenho atual](docs/superpowers/specs/2026-10-12-nexer-reusable-flows-design.md)
- [Roadmap atualizado](docs/development/ROADMAP.md)
- [Gravar, importar e reutilizar receitas](apps/recorder/README.md)
- [Continuidade do desenvolvimento](CONTINUAR_NEXER_2026-10-13.md)

## Versão legada

A documentação abaixo descreve a versão anterior em Streamlit, especializada em SGIND/IQOS. Suas instruções de credenciais e instalação não representam o novo núcleo; esse legado permanece preservado durante a migração.

Automação de relatórios do **SGIND** e **IQOS**, com painel em Streamlit, controle de execução, acompanhamento de status, download dos arquivos e tratamento automático do ambiente Python.

A versão final foi preparada para uso no Windows por meio do executável `Nexer.exe`. Na primeira abertura, o launcher configura automaticamente o ambiente necessário para executar o projeto.

## Funcionalidades

- Painel local em Streamlit.
- Seleção de período inicial e final.
- Execução automatizada dos relatórios do SGIND e IQOS.
- Acompanhamento do status de cada relatório.
- Registro detalhado em arquivos de log.
- Download dos CSVs pelo painel.
- Cópia e validação dos arquivos na rede, conforme a configuração do projeto.
- Cancelamento seguro da execução em andamento.
- Limpeza dos downloads anteriores ao iniciar uma nova execução.
- Limpeza dos logs antigos, preservando o log do Streamlit.
- Armazenamento seguro das credenciais no arquivo `.env` local.
- Instalação automática das dependências na primeira execução.
- Criação e reparo automático do ambiente virtual.
- Detecção de instalação incompleta do Streamlit.
- Reparo automático do arquivo `streamlit/static/index.html` quando necessário.
- Uso do Microsoft Edge instalado no Windows para a automação do Playwright.

## Relatórios automatizados

O projeto executa os seguintes relatórios:

1. Compensação
2. Reclamações
3. Interrupções por Cliente
4. Eventos, correspondente a Interrupções por Evento
5. Ocorrências, correspondente a Todas as Ocorrências
6. Dia Crítico
7. IQOS, correspondente a Resultados e Insumos de `ATENDIMENTO_CHEIO`

Os relatórios são acompanhados individualmente pelo painel, com os estados:

- `PENDENTE`
- `EXECUTANDO`
- `CONCLUIDO`
- `ERRO`
- `REMOVIDO`
- `CANCELADO`

## Requisitos do computador

- Windows 10 ou Windows 11.
- Microsoft Edge instalado.
- Acesso aos sistemas internos SGIND e IQOS.
- Acesso à rede ou aos serviços necessários para salvar os relatórios.
- Acesso ao repositório de pacotes Python configurado no computador.
- `winget` disponível caso o Python ainda não esteja instalado.

O usuário não precisa criar manualmente a pasta `venv` nem instalar previamente as bibliotecas do projeto.

## Instalação e primeira execução

### 1. Baixar o projeto

No GitHub, use **Code > Download ZIP** e extraia todo o conteúdo.

Não execute o programa diretamente de dentro do arquivo ZIP.

### 2. Conferir a estrutura

A pasta extraída deve conter, no mínimo:

```text
Nexer/
├── Nexer.exe
├── launcher.py
├── worker.py
├── auth.py
├── requisitos.txt
├── assets/
├── core/
├── relatorios/
└── ui/
    └── streamlit_app.py
```

### 3. Abrir o programa

Execute:

```text
Nexer.exe
```

Na primeira execução, o launcher realiza automaticamente:

1. Localização da raiz do projeto.
2. Verificação do Python 3.10 ou superior.
3. Instalação do Python 3.12 pelo `winget`, se necessário.
4. Criação da pasta `venv`.
5. Atualização de `pip`, `setuptools` e `wheel`.
6. Instalação das bibliotecas de `requisitos.txt`.
7. Validação das dependências com `pip check`.
8. Validação e reparo da instalação do Streamlit.
9. Localização do Microsoft Edge.
10. Inicialização do painel local.

O painel é aberto em:

```text
http://127.0.0.1:8501
```

## Primeiro acesso

Se o arquivo `.env` ainda não existir, o painel solicitará:

- Usuário
- Senha

As credenciais serão salvas localmente no arquivo `.env`, na raiz do projeto.

O arquivo `.env` não deve ser enviado ao GitHub, compartilhado por e-mail ou incluído em pacotes de distribuição.

## Como usar

1. Abra o `Nexer.exe`.
2. Informe as credenciais no primeiro acesso, se solicitado.
3. Selecione a data inicial.
4. Selecione a data final.
5. Clique em **Executar Relatórios**.
6. Acompanhe os estados no painel.
7. Baixe os arquivos concluídos na seção **Downloads**.

Ao iniciar uma nova execução, o sistema exclui os arquivos presentes na pasta `downloads` antes de executar os novos relatórios. Se algum arquivo estiver bloqueado e não puder ser removido, a execução é cancelada para evitar a mistura de arquivos antigos e novos.

## Encerramento e cancelamento

### Parar execução

O botão **Parar execução** encerra:

- o worker atual;
- os processos-filhos;
- os navegadores abertos pelo Playwright.

Os relatórios ainda pendentes ou em execução passam para o estado `CANCELADO`.

### Fechar Nexer

O botão **Fechar Nexer** solicita o encerramento seguro do servidor Streamlit e do launcher.

## Pastas criadas localmente

Durante o uso, o projeto pode criar:

```text
venv/
downloads/
logs/
status/
__pycache__/
```

Finalidades:

- `venv/`: ambiente virtual e bibliotecas Python.
- `downloads/`: relatórios gerados localmente.
- `logs/`: logs do launcher, Streamlit e worker.
- `status/`: estado atual dos relatórios e PIDs dos processos.
- `__pycache__/`: cache interno do Python.

Essas pastas não precisam ser versionadas.

## Logs e diagnóstico

### Log do painel e launcher

```text
logs/streamlit.log
```

Exibir as últimas linhas no PowerShell:

```powershell
Get-Content .\logs\streamlit.log -Tail 150
```

### Log da execução dos relatórios

```text
logs/worker.log
```

Exibir as últimas linhas:

```powershell
Get-Content .\logs\worker.log -Tail 150
```

### Status dos relatórios

```text
status/status.json
```

O painel lê esse arquivo para mostrar o estado de cada módulo.

## Instalação automática e reparo

### Ambiente virtual

Se `venv` não existir, o executável cria o ambiente automaticamente.

Se a `venv` existir, mas estiver inválida, o launcher tenta recriá-la.

### Dependências

O launcher calcula uma assinatura SHA-256 do arquivo de requisitos e registra em:

```text
venv/.nexer_dependencies.sha256
```

As dependências são reinstaladas quando:

- a `venv` é criada;
- o arquivo de requisitos muda;
- `pip check` identifica inconsistências.

### Reparo do Streamlit

Antes de iniciar o painel, o launcher verifica a existência de:

```text
venv/Lib/site-packages/streamlit/static/index.html
```

Se o arquivo estiver ausente, o launcher:

1. identifica a versão instalada do Streamlit;
2. remove a instalação incompleta;
3. remove metadados antigos;
4. reinstala a mesma versão sem usar o cache do `pip`;
5. valida novamente o arquivo estático.

## Microsoft Edge e Playwright

O projeto utiliza o Microsoft Edge instalado no Windows, por meio do canal `msedge` do Playwright.

Isso evita o download adicional do Chromium e reduz problemas em redes corporativas com inspeção HTTPS ou certificados internos.

A inicialização do navegador deve respeitar a variável:

```text
NEXER_BROWSER_CHANNEL=msedge
```

Exemplo no código:

```python
import os

canal = os.environ.get(
    "NEXER_BROWSER_CHANNEL",
    "msedge",
)

browser = await playwright.chromium.launch(
    channel=canal,
    headless=False,
)
```

## Solução de problemas

### A raiz do projeto não foi localizada

Confirme que existem:

```text
ui/streamlit_app.py
requisitos.txt
```

O executável deve permanecer junto da pasta completa do projeto. Não distribua apenas o `Nexer.exe` isoladamente.

### Python não encontrado

O launcher tentará instalar Python 3.12 usando `winget`.

Se o `winget` não estiver disponível, instale o Python manualmente e marque a opção **Add Python to PATH**.

Depois, abra novamente o `Nexer.exe`.

### Internal Server Error

Consulte:

```powershell
Get-Content .\logs\streamlit.log -Tail 150
```

Se faltar `streamlit/static/index.html`, use a versão atualizada do launcher, que executa o reparo automaticamente.

### Microsoft Edge não encontrado

Instale ou atualize o Microsoft Edge e execute novamente o programa.

O projeto não desabilita a validação TLS e não usa `NODE_TLS_REJECT_UNAUTHORIZED=0`.

### Execução presa em uma espera

O projeto utiliza esperas baseadas no estado real da interface, sem pausas fixas. Se o sistema de origem não apresentar o próximo elemento esperado, a execução poderá continuar aguardando.

Use o botão **Parar execução** para encerrar com segurança.

### PID obsoleto

O painel verifica se o PID ainda pertence ao worker. Quando o processo não existe mais, o PID obsoleto é removido automaticamente.

## Desenvolvimento

### Criar a venv manualmente

```powershell
py -3.12 -m venv .\venv
```

### Instalar dependências

```powershell
.\venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\venv\Scripts\python.exe -m pip install --no-cache-dir -r .\requisitos.txt
```

### Validar as dependências

```powershell
.\venv\Scripts\python.exe -m pip check
```

### Validar a sintaxe

```powershell
.\venv\Scripts\python.exe -m py_compile .\launcher.py
.\venv\Scripts\python.exe -m py_compile .\worker.py
```

Para validar todos os arquivos Python:

```powershell
Get-ChildItem . -Recurse -Filter "*.py" |
    ForEach-Object {
        .\venv\Scripts\python.exe -m py_compile $_.FullName
    }
```

## Gerar o executável

Instale o PyInstaller:

```powershell
.\venv\Scripts\python.exe -m pip install --upgrade pyinstaller
```

Remova builds antigos:

```powershell
Remove-Item .\build -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\dist -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\Nexer.spec -Force -ErrorAction SilentlyContinue
```

Compile:

```powershell
.\venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name Nexer --icon ".\assets\logo.ico" ".\launcher.py"
```

O arquivo será gerado em:

```text
dist/Nexer.exe
```

Copie para a raiz:

```powershell
Copy-Item .\dist\Nexer.exe .\Nexer.exe -Force
```

Confirme antes de publicar:

```powershell
Test-Path .\Nexer.exe
Get-Item .\Nexer.exe |
    Select-Object FullName, Length, LastWriteTime
```

## Publicação no GitHub

Exemplo de configuração do remoto:

```powershell
git remote add origin https://github.com/SEU-USUARIO/Nexer.git
```

Se o remoto já existir:

```powershell
git remote set-url origin https://github.com/SEU-USUARIO/Nexer.git
```

Publicar a branch atual:

```powershell
git branch --show-current
git push --set-upstream origin master
```

Se a branch se chamar `main`, substitua `master` por `main`.

## `.gitignore` recomendado

Como o executável final será versionado, não inclua `*.exe` no `.gitignore`.

Exemplo:

```gitignore
# Ambiente e cache
venv/
.venv/
__pycache__/
*.pyc

# Credenciais e dados locais
.env
downloads/
logs/
status/

# Build do PyInstaller
build/
dist/
*.spec

# Arquivos temporários
*.bak
*.tmp

# O executável Nexer.exe é versionado intencionalmente.
```

Antes de enviar, confirme:

```powershell
git check-ignore -v .\Nexer.exe
```

O comando não deve retornar nenhuma regra.

## Segurança

- Não envie `.env` ao GitHub.
- Não registre credenciais em logs.
- Não desabilite a validação TLS.
- Não use `NODE_TLS_REJECT_UNAUTHORIZED=0`.
- Não execute o projeto como administrador, salvo exigência da organização.
- Não altere `PASTA_DOWNLOADS` para um caminho fornecido por entrada do usuário.
- Mantenha as dependências atualizadas e revise alterações antes de publicar.
- Distribua o executável junto de todos os arquivos externos do projeto.

## Estrutura recomendada para distribuição

```text
Nexer/
├── Nexer.exe
├── launcher.py
├── worker.py
├── auth.py
├── requisitos.txt
├── assets/
├── core/
├── relatorios/
└── ui/
    └── streamlit_app.py
```

Não distribua:

```text
venv/
.env
logs/
status/
downloads/
build/
dist/
__pycache__/
```

## Estado do projeto

Versão final funcional, com:

- automação SGIND e IQOS;
- painel Streamlit;
- gerenciamento de execução;
- instalação automática do ambiente;
- reparo automático do Streamlit;
- uso do Microsoft Edge pelo Playwright;
- limpeza dos downloads entre execuções;
- geração e distribuição pelo executável `Nexer.exe`.

## Licença e uso

Projeto destinado a uso interno e autorizado. Antes de redistribuir, confirme as políticas da organização sobre credenciais, sistemas internos, dados dos relatórios e executáveis.


### Downloads em centrais compartilhadas

A revisão do fluxo permite vincular um download à confirmação de sua solicitação e aguardar o resultado correto, inclusive em lote com conclusão fora de ordem. Consulte [a entrega e os limites de adaptação](docs/2026-10-14-downloads-correlacionados.md). O contrato genérico está implementado; SGIND real ainda depende de evidência de correlação do portal.

### Consultas com resultado verificável

A revisão também permite converter um clique em consulta com confirmação de dados, ausência de dados ou erro. O resultado deve apresentar a identificação da solicitação atual; dados antigos não são aceitos. Veja [configuração, testes e limites](docs/2026-10-14-query-outcomes.md). A primeira versão exige metadado verificável fornecido pelo site/adaptador.

### Revisão e reparo de etapas

Após gravar ou importar um fluxo, a etapa Campos mostra a sequência de ações e permite corrigir o alvo de uma etapa sem regravar o restante. Esperas automáticas associadas podem acompanhar a correção; edições pendentes são preservadas até aplicar ou descartar. Veja [uso, evidências e limites](docs/2026-10-14-step-review.md).
