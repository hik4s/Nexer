# Nexer

> Automação de relatórios corporativos com Python, Playwright e Streamlit, desenvolvida para reduzir tarefas manuais, acompanhar execuções em tempo real e simplificar a instalação em computadores Windows.

## Visão geral

O **Nexer** é um projeto de automação criado para extrair, organizar e disponibilizar relatórios de dois sistemas web internos, o **SGIND** e o **IQOS**.

A solução nasceu de um problema operacional: relatórios diferentes exigiam acesso manual aos sistemas, preenchimento de filtros, navegação por tabelas hierárquicas, solicitação de exportações, acompanhamento do processamento e download individual de arquivos. Além do tempo gasto, o processo estava sujeito a falhas humanas, arquivos duplicados e dificuldade para acompanhar o andamento de execuções demoradas.

O projeto transforma esse fluxo em uma aplicação local com interface web. A pessoa usuária informa o período desejado, inicia a execução e acompanha o estado de cada relatório pelo painel. O sistema controla processos em segundo plano, registra logs, organiza os downloads e oferece mecanismos de cancelamento e recuperação de falhas.

## Objetivo do projeto

Os principais objetivos foram:

- Automatizar tarefas repetitivas realizadas em sistemas web corporativos.
- Reduzir o tempo necessário para gerar vários relatórios.
- Padronizar filtros, nomes e resultados.
- Dar visibilidade ao andamento de cada automação.
- Permitir que o projeto seja executado sem configuração manual complexa.
- Tratar falhas de navegação, download, instalação e encerramento.
- Proteger credenciais e dados locais contra versionamento acidental.
- Criar uma solução compreensível, modular e adequada para manutenção futura.

## Demonstração de competências

Este projeto representa prática aplicada em diferentes áreas de tecnologia:

- Desenvolvimento Python assíncrono.
- Automação web com Playwright.
- Desenvolvimento de interface com Streamlit.
- Gerenciamento de processos no Windows.
- Persistência de estado com JSON.
- Manipulação segura de arquivos e diretórios.
- Instalação automatizada de dependências.
- Empacotamento com PyInstaller.
- Tratamento de erros e criação de logs.
- Controle de versão com Git e GitHub.
- Segurança defensiva para credenciais, caminhos e subprocessos.
- Diagnóstico de problemas em ambientes corporativos.

## Relatórios automatizados

A aplicação controla sete fluxos de relatório:

1. Compensação
2. Reclamações
3. Interrupções por Cliente
4. Interrupções por Evento
5. Todas as Ocorrências
6. Dia Crítico
7. IQOS, com navegação hierárquica de resultados e insumos

Cada módulo possui um fluxo próprio, mas segue um contrato comum de retorno:

```python
{
    "status": "CONCLUIDO",
    "arquivo": "caminho/do/arquivo.csv"
}
```

Os estados utilizados pela interface são:

- `PENDENTE`
- `EXECUTANDO`
- `CONCLUIDO`
- `ERRO`
- `REMOVIDO`
- `CANCELADO`

## Arquitetura

O projeto foi separado em componentes com responsabilidades específicas:

```text
Nexer/
├── Nexer.exe
├── launcher.py
├── worker.py
├── main.py
├── downloader.py
├── auth.py
├── config.py
├── requisitos.txt
│
├── ui/
│   └── streamlit_app.py
│
├── core/
│   ├── app_control.py
│   ├── executor.py
│   └── file_manager.py
│
├── relatorios/
│   ├── compensacao.py
│   ├── reclamacao.py
│   ├── interrupcoes_cliente.py
│   ├── interrupcoes_evento.py
│   ├── todas_ocorrencias.py
│   ├── dia_critico.py
│   └── iqos_resultados.py
│
├── assets/
│   └── logo.ico
│
├── downloads/
├── logs/
├── status/
└── venv/
```

### Fluxo principal

```text
Nexer.exe
    ↓
launcher.py
    ↓
validação e preparação do ambiente
    ↓
Streamlit
    ↓
streamlit_app.py
    ↓
worker.py
    ↓
downloader.py e executor.py
    ↓
módulos de relatório com Playwright
    ↓
downloads, logs e status.json
```

### Launcher

O `launcher.py` é responsável por:

- localizar a raiz do projeto;
- mostrar uma splash screen em Tkinter;
- encontrar ou instalar uma versão compatível do Python;
- criar e validar a `venv`;
- instalar dependências;
- validar a instalação do Streamlit;
- reparar arquivos estáticos ausentes;
- localizar o Microsoft Edge;
- iniciar o servidor Streamlit sem abrir um terminal;
- aguardar a porta local responder;
- abrir o navegador;
- monitorar o pedido de encerramento.

### Interface

O `ui/streamlit_app.py` oferece:

- configuração inicial de credenciais;
- seleção de datas;
- botão para iniciar relatórios;
- botão para interromper uma execução;
- atualização automática do painel;
- métricas de concluídos, executando, erros, cancelados e pendentes;
- detalhes por relatório;
- downloads dos arquivos gerados;
- visualização do log da execução;
- encerramento seguro do Nexer.

### Worker

O `worker.py` executa a automação em um processo separado. Essa decisão evita que o fechamento ou a atualização da página interrompa os relatórios.

O PID do processo é registrado em:

```text
status/worker.pid
```

A interface valida se o PID ainda pertence ao `worker.py`, remove PIDs obsoletos e impede duas execuções concorrentes acidentais.

### Módulos de relatório

Cada arquivo dentro de `relatorios/` implementa as etapas específicas para um relatório:

- seleção de empresa;
- preenchimento de período;
- alteração de filtros;
- navegação em abas;
- expansão de estruturas hierárquicas;
- solicitação de exportação;
- acompanhamento do processamento;
- identificação do card correto;
- download do arquivo.

## Principal desafio: substituir pausas por ações observáveis

Uma das evoluções mais importantes do projeto foi remover esperas fixas como:

```python
await page.wait_for_timeout(5000)
```

Pausas fixas podem falhar quando o servidor está lento e desperdiçam tempo quando a resposta é rápida.

A automação passou a aguardar resultados reais da interface:

```python
await elemento.wait_for(
    state="visible",
    timeout=0,
)
```

```python
await spinner.wait_for(
    state="hidden",
    timeout=0,
)
```

```python
async with page.expect_download(
    timeout=0,
) as download_info:
    await botao.click(timeout=0)
```

Na árvore do IQOS, a confirmação da expansão passou a depender do surgimento do próximo item esperado:

```text
ATENDIMENTO_CHEIO
    ↓
ATENDIMENTO_CHEIO
    ↓
mês selecionado
    ↓
DIARIO
    ↓
CONJ_ELETRICO
    ↓
RESULTADO
```

Essa abordagem tornou o comportamento mais alinhado ao estado real da aplicação.

## Desafio: overlays que bloqueavam cliques

Durante a automação, algumas abas estavam visíveis e habilitadas, mas um overlay de carregamento interceptava os eventos do mouse.

O erro indicava que o elemento abaixo estava bloqueando a ação:

```text
ngx-spinner-overlay intercepts pointer events
```

A solução não foi forçar o clique. O projeto passou a aguardar o overlay desaparecer:

```python
spinner = page.locator(
    "ngx-spinner .ngx-spinner-overlay"
)

await spinner.first.wait_for(
    state="hidden",
    timeout=0,
)
```

Esse caso reforçou um aprendizado importante: um elemento visível nem sempre está pronto para interação.

## Desafio: eventos de download

Alguns relatórios demoravam mais que o limite padrão do Playwright para iniciar o download.

O projeto passou a:

1. localizar o card pelo nome esperado;
2. confirmar que o card está concluído;
3. aguardar o botão ficar visível e habilitado;
4. aguardar o evento real de download;
5. salvar o arquivo somente após o navegador disponibilizá-lo.

```python
card = page.locator(
    "div.p-card-content"
).filter(
    has_text=texto_busca
).filter(
    has_text="CONCLUÍDO"
).first

await card.wait_for(
    state="visible",
    timeout=0,
)
```

```python
async with page.expect_download(
    timeout=0,
) as download_info:
    await botao.click(timeout=0)
```

Essa alteração também reduziu o risco de baixar o arquivo associado ao relatório errado.

## Desafio: contratos inconsistentes

Durante o desenvolvimento, alguns módulos retornavam:

```python
info["arquivo_baixado"]
```

enquanto outros retornavam a chave `arquivo`. Isso causava `KeyError`.

O contrato foi padronizado:

```python
return {
    "status": "CONCLUIDO",
    "arquivo": arquivo_baixado,
}
```

A padronização permitiu que o executor tratasse todos os módulos da mesma forma.

## Desafio: persistência entre sessões do navegador

Inicialmente, abrir uma nova aba do painel apagava o `status.json`. Isso acontecia porque o estado global da execução estava vinculado à sessão do Streamlit.

A solução foi separar:

- sessão visual do navegador;
- estado persistente do worker;
- arquivo global de status.

O `status.json` agora é criado somente quando não existe e é limpo apenas quando uma nova execução é iniciada.

Resultado:

- atualizar a página não apaga o status;
- fechar e reabrir a aba não interrompe o worker;
- o painel recupera o andamento da execução atual.

## Desafio: cancelamento seguro

O painel recebeu um botão para interromper a execução atual.

O processo de cancelamento:

1. lê o PID registrado;
2. confirma que o PID pertence ao `worker.py`;
3. encerra a árvore de processos;
4. remove o PID somente após a finalização;
5. preserva relatórios concluídos;
6. marca itens pendentes ou executando como `CANCELADO`;
7. libera novamente o botão de execução.

A solução evita comandos amplos como:

```text
taskkill /IM python.exe
```

Esse tipo de comando poderia encerrar outros programas Python da máquina.

## Desafio: instalação automática

Uma cópia baixada do GitHub não contém a pasta `venv`. O launcher original exigia:

```text
venv/Scripts/python.exe
```

para reconhecer a raiz do projeto, o que impedia a primeira execução.

A lógica foi corrigida para localizar a raiz apenas por arquivos versionados:

```text
ui/streamlit_app.py
requisitos.txt
```

Depois disso, o launcher prepara o ambiente.

Na primeira execução, o `Nexer.exe` pode:

- localizar Python 3.10 ou superior;
- instalar Python 3.12 pelo `winget`, quando disponível;
- criar a `venv`;
- atualizar ferramentas de empacotamento;
- instalar as dependências;
- validar o ambiente com `pip check`.

## Desafio: instalação incompleta do Streamlit

Em uma instalação, o servidor iniciou, mas retornou erro HTTP 500 porque faltava:

```text
streamlit/static/index.html
```

Embora `pip check` não apontasse problemas, o pacote estava incompleto.

O launcher passou a validar explicitamente esse arquivo. Quando necessário, o fluxo de reparo:

1. identifica a versão instalada;
2. remove a pasta incompleta;
3. remove metadados antigos;
4. reinstala a mesma versão;
5. ignora o cache do pip;
6. valida novamente o arquivo estático.

Essa solução tornou a inicialização mais resiliente a instalações interrompidas ou pacotes incompletos.

## Desafio: rede corporativa e Playwright

O download do Chromium apresentou erro de certificado em uma rede que inspeciona conexões HTTPS.

Em vez de desativar a validação TLS, o projeto passou a usar o Microsoft Edge instalado no Windows:

```python
browser = await playwright.chromium.launch(
    channel="msedge",
    headless=False,
)
```

Essa decisão evitou práticas inseguras como:

```text
NODE_TLS_REJECT_UNAUTHORIZED=0
```

A solução manteve a validação de certificados e aproveitou um navegador já gerenciado pelo sistema operacional.

## Desafio: distribuição por executável

O launcher foi empacotado com PyInstaller:

```powershell
.\venv\Scripts\python.exe -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Nexer `
    --icon ".\assets\logo.ico" `
    --add-data ".\assets\logo.ico;assets" `
    ".\launcher.py"
```

Os parâmetros atendem a necessidades diferentes:

- `--onefile`: gera um único executável de entrada;
- `--windowed`: evita abrir um console durante o uso normal;
- `--icon`: define o ícone do arquivo executável;
- `--add-data`: inclui o ícone usado pela janela Tkinter;
- `--clean`: remove resíduos do build anterior.

O executável não contém todos os módulos externos do projeto. A distribuição ainda precisa preservar a estrutura com `ui`, `core`, `relatorios`, `worker.py`, `auth.py` e `requisitos.txt`.

## Segurança aplicada

O projeto incorpora decisões de segurança defensiva:

### Credenciais

- Credenciais não ficam no código-fonte.
- O arquivo `.env` é local.
- O `.env` não deve ser versionado.
- Usuário e senha não são gravados nos logs.

### Arquivos

- A limpeza ocorre somente dentro da pasta `downloads`.
- A pasta principal é preservada.
- Links simbólicos são removidos sem seguir destinos externos.
- Uma nova execução é cancelada se arquivos antigos estiverem bloqueados.

### Processos

- O PID é validado antes do encerramento.
- Apenas o worker atual e seus processos-filhos são finalizados.
- O dashboard fica limitado a `127.0.0.1`.
- O Streamlit e o worker são iniciados sem abrir terminais adicionais.

### Dependências

- As dependências são validadas com `pip check`.
- O arquivo de requisitos possui uma assinatura SHA-256 local.
- Mudanças no arquivo de requisitos acionam nova instalação.
- O reparo do Streamlit evita reutilizar cache danificado.

### Rede

- A validação TLS não é desativada.
- O projeto utiliza o Edge disponível no equipamento.
- Não são aceitos caminhos arbitrários informados pelo usuário para exclusão.

## Limpeza entre execuções

Antes de uma nova execução, o sistema:

1. valida que não existe outro worker ativo;
2. valida credenciais e arquivos necessários;
3. remove downloads antigos;
4. limpa logs do worker;
5. preserva o log ativo do Streamlit;
6. reinicia o `status.json`;
7. cria o novo processo.

A ordem evita perder o estado anterior caso a preparação da nova execução falhe.

## Logs e observabilidade

O projeto utiliza dois logs principais:

```text
logs/streamlit.log
logs/worker.log
```

O primeiro registra launcher, preparação do ambiente e servidor. O segundo registra as etapas dos relatórios.

Exemplo de acompanhamento:

```powershell
Get-Content .\logs\worker.log -Tail 100 -Wait
```

O painel também apresenta o conteúdo mais recente do log da execução.

## Como executar

### Uso normal

1. Baixe ou clone o repositório.
2. Extraia a pasta completa.
3. Execute `Nexer.exe`.
4. Informe as credenciais no primeiro acesso.
5. Selecione o período.
6. Clique em **Executar Relatórios**.

### Execução para desenvolvimento

```powershell
py -3.12 -m venv .\venv
.\venv\Scripts\python.exe -m pip install --no-cache-dir -r .\requisitos.txt
.\venv\Scripts\python.exe -m streamlit run .\ui\streamlit_app.py
```

## Como testar

### Sintaxe

```powershell
Get-ChildItem . -Recurse -Filter "*.py" |
    ForEach-Object {
        .\venv\Scripts\python.exe -m py_compile $_.FullName
    }
```

### Dependências

```powershell
.\venv\Scripts\python.exe -m pip check
```

### Arquivo estático do Streamlit

```powershell
Test-Path .\venv\Lib\site-packages\streamlit\static\index.html
```

### Worker ativo

```powershell
Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -like "*worker.py*"
    } |
    Select-Object ProcessId, CommandLine
```

### Teste de distribuição

Para simular uma instalação nova:

```powershell
Remove-Item .\venv -Recurse -Force
.\Nexer.exe
```

O launcher deve recriar o ambiente e instalar as dependências.

## Tecnologias utilizadas

- Python
- `asyncio`
- Playwright
- Streamlit
- Tkinter
- PyInstaller
- python-dotenv
- JSON
- subprocess
- pathlib
- Git
- GitHub
- PowerShell
- Windows Process Management

## Aprendizados

O desenvolvimento deste projeto trouxe aprendizados que vão além da automação em si:

- Esperar o estado correto é mais confiável do que esperar um tempo fixo.
- Interfaces web podem apresentar elementos visíveis que ainda não estão interativos.
- Automação precisa de contratos padronizados entre módulos.
- Estado de processo não deve depender da sessão do navegador.
- Logs devem explicar a etapa atual, não apenas registrar o erro final.
- Um pacote instalado pode estar incompleto mesmo quando suas dependências estão corretas.
- Empacotar um launcher é diferente de empacotar todo o sistema.
- Ambientes corporativos exigem atenção especial a certificados, proxies e navegadores gerenciados.
- Cancelamento seguro exige validar qual processo será encerrado.
- Distribuição é parte do desenvolvimento, não apenas uma etapa final.

## Melhorias futuras

Possíveis evoluções:

- Captura automática de screenshot e HTML em falhas.
- Exibição da etapa atual no painel.
- Registro de duração por relatório.
- Validação estrutural dos arquivos CSV.
- Download temporário com extensão `.part` antes da confirmação.
- Testes automatizados com mocks das páginas.
- Rotação e retenção configurável de logs.
- Métricas históricas de desempenho e falhas.
- Tela de diagnóstico do ambiente.
- Pipeline de release no GitHub Actions.
- Assinatura digital do executável.

## Por que este projeto é relevante para uma vaga júnior ou estágio

O Nexer demonstra a capacidade de transformar uma necessidade operacional em uma aplicação funcional, passando por levantamento do problema, implementação, testes, diagnóstico, segurança, empacotamento e documentação.

O trabalho não se limitou a escrever scripts de automação. Foi necessário lidar com:

- interfaces assíncronas;
- estados inconsistentes;
- processos independentes;
- dependências externas;
- erros de instalação;
- particularidades do Windows;
- restrições de rede corporativa;
- experiência da pessoa usuária;
- segurança de credenciais;
- manutenção e distribuição.

Para uma posição de desenvolvimento júnior, estágio em TI, automação, suporte técnico, infraestrutura ou segurança defensiva, o projeto evidencia:

- iniciativa para investigar erros;
- capacidade de decompor problemas;
- evolução incremental de uma solução;
- preocupação com segurança e confiabilidade;
- documentação técnica;
- uso prático de controle de versão;
- disposição para aprender tecnologias conforme a necessidade.

## Cuidados antes de publicar

Este repositório não deve conter:

```text
.env
venv/
downloads/
logs/
status/
__pycache__/
build/
dist/
```

Quando o executável for versionado intencionalmente, não inclua `*.exe` no `.gitignore`.

Antes do commit:

```powershell
git status
git check-ignore -v .\Nexer.exe
git add README.md launcher.py Nexer.exe requisitos.txt
git commit -m "Finaliza projeto Nexer e documentação de portfólio"
git push
```

## Observação sobre confidencialidade

O projeto automatiza sistemas internos. Para apresentação pública em portfólio, recomenda-se:

- remover URLs internas;
- substituir nomes de servidores por exemplos genéricos;
- não publicar credenciais;
- não publicar relatórios reais;
- não publicar dados operacionais;
- usar screenshots com informações sensíveis ocultadas;
- confirmar autorização antes de tornar o código público.

## Autor

Projeto desenvolvido como iniciativa prática de automação e aprendizado em Python, com foco em confiabilidade, segurança defensiva e experiência de uso.

---

Se este projeto estiver sendo avaliado como portfólio, os principais pontos técnicos estão nas seções **Arquitetura**, **Desafios**, **Segurança aplicada** e **Aprendizados**.
