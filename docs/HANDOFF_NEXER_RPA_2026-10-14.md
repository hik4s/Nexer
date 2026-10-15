# NEXER — HANDOFF MASTER: transição para RPA de propósito geral

> Continuação em 15/10/2026: ler primeiro [estabilidade e arquivos no histórico](2026-10-15-stability-artifacts.md), incluindo mudança de validação de downloads, evidências E2E e limitações. O texto abaixo preserva a fotografia histórica de 14/10.

**Data de consolidação:** 14/10/2026  
**Natureza:** visão de produto + decisões + inventário de implementação + microtarefas + plano de transição + instruções de continuidade.  
**Destino:** próximo chat (GPT para planejamento ou modelo de código), Codex CLI, VS Code/Copilot ou agente autorizado.  
**Status:** documento de referência. Não significa que funcionalidades ainda planejadas tenham sido implementadas, que o produto esteja homologado ou que alterações estejam publicadas no GitHub.

> **LEIA PRIMEIRO — RESUMO EXECUTIVO:** O Nexer deixou de ser concebido como extrator dedicado de relatórios SGIND/IQOS e passou a ter como objetivo **uma plataforma RPA de propósito geral, desktop-first, distribuível a usuários comuns e empresas**, capaz de gravar, editar, parametrizar, reproduzir e administrar automações web de forma segura, previsível e local. SGIND/IQOS continuam como **primeiro caso real de homologação, quando autorizado**, nunca como dependência obrigatória do núcleo. O software **ainda é uma aplicação web local híbrida em desenvolvimento**, e não um EXE moderno autossuficiente nem um SaaS hospedado. Priorizar confiabilidade do motor, instalador, separação de dados corporativos e distribuição antes de pensar em nuvem. Há **26 microtarefas originais** do piloto, aqui preservadas com IDs e critérios, e um segundo trilho de microtarefas propostas para a transformação em produto RPA.

---

## 1. Decisões firmadas pelo usuário — não reinterpretar

1. **Novo posicionamento:** Nexer será produto de **RPA generalista** para pessoas e empresas que criem e executem suas próprias automações. Não é apenas automação de relatórios Energisa. SGIND/IQOS são casos/adaptadores opcionais e não devem ser distribuídos publicamente sem autorização.
2. **Produto alvo:** primeiro **Nexer Desktop**, no Windows, com interface profissional de gravação/edição/execução; depois **Nexer Studio** mais avançado; **Nexer Cloud** apenas opcional no futuro. **Estratégia desktop-first / local-first, com possibilidade híbrida.**
3. **Arquitetura atual deve ser reaproveitada:** React/TypeScript/Vite, FastAPI, Python/Playwright com Edge, SQLite, gravação inteligente, receitas versionadas, fila/lotes. Evitar reescrever ou duplicar contratos existentes.
4. **Direção técnica proposta, não escolhida em código:** avaliar **Tauri + React** como shell desktop leve e **motor/backend Python empacotado como sidecar** (PyInstaller/Nuitka ou alternativa após comparação). **Electron** é alternativa. O bootstrap CMD+PowerShell já existe, mas **não é instalador autocontido**. Nenhum Tauri, MSI ou novo EXE moderno foi implementado/validado nesta conversa.
5. **Custo inicial zero:** sem exigência de servidor pago, banco cloud ou serviço de IA externo. Testar limites reais de licenças, assinatura de binários, atualização, hospedagem e distribuição antes de comprometer custo zero absoluto. Infraestrutura gratuita no desktop é viável; publicação/distribuição massiva pode ter custos opcionais.
6. **Credenciais corporativas jamais em `.env`, receita, código, logs, print ou chat.** O usuário digita usuário/senha **na interface durante cada execução**; transportar por canal efêmero, descartar/revogar depois. **Distinção técnica:** existe hoje `scripts/setup_auth.py` que gera **usuário LOCAL de administração + hash** em `.env`; esse não é o login SGIND/IQOS. Para produto público, revisar onboarding e armazenamento do login local (cofre do SO, outra estratégia), mas não afirmar que o comportamento atual já mudou.
7. **Modo de gravação:** registrar **somente referências estruturais a seletores, ações e relações**, não dados introduzidos nos campos. **Empresa, datas e outros parâmetros configuráveis no dashboard antes da execução**. Não usar JS arbitrário fornecido pelo usuário nas receitas.
8. **Segurança e evidência:** um botão clicado, elemento visível ou arquivo novo **não significa sucesso**. Um job com resultado incerto não deve ser repetido automaticamente; o CSV só é sucesso se correto, próprio da execução, validado e acessível na UI. Falhar de forma fechada quando não houver correlação forte.
9. **Git:** nunca modificar `master` diretamente; revisar `status`, branch, remotes, diferenças e segredos antes de commit/push; não fazer force push; não descartar dados pendentes, misturar árvores legadas, reinicializar `.git` ou trabalhar às cegas no gitlink aninhado `Nexer`.
10. **Papéis da IA:** usuário decidiu: **GPT Astra = arquitetura, brainstorm, microtarefas, planejamento, revisão de evidências. Outro modelo = codificação.** Ao implementar, manter essa divisão salvo nova determinação explícita. Aplicar TDD quando viável; documentar RED/GREEN, resultados e limites reais.
11. **Acompanhamento:** usuário quer acompanhar decisões, diffs e testes verificáveis; não declarar implementações, homologações ou testes completos sem execução e evidências concretas. Evitar atalhos para "parecer funcionar".
12. **Reaproveitamento seletivo do legado RelatPy:** projeto foi renomeado Nexer em 08/10/2026; preservar somente componentes úteis. Não confundir launchers/README da versão Streamlit com a nova arquitetura.

## 2. Identidade do produto e público-alvo

### 2.1 Missão

**Nexer é uma plataforma de automação RPA local-first que permite que pessoas e organizações gravem tarefas de interface, configurem entradas, revisem decisões, executem lotes e recebam resultados verificáveis, sem programação obrigatória.** Deve ser extensível, mas conservadora em segurança e evidências.

### 2.2 Público-alvo

- **Pessoa física:** operações repetitivas na web, formulários, coleta/exportação de dados próprios, rotinas pessoais e downloads em serviços autorizados.
- **Profissionais e equipes:** processos administrativos, geração de documentos/relatórios, manipulação de formulários e automações de sites internos quando permitidas.
- **Empresas:** instalação local, governança, segregação de perfis/segredos, auditoria, empacotamento e posterior administração de múltiplos agentes.

**Limite de v1:** foco em automação **web via navegador**. APIs, manipulação local de arquivos e aplicações desktop nativas poderão ser acrescentadas com contratos/autorizações específicos. Não afirmar suporte universal a qualquer site, captcha, MFA, shadow DOM fechado, canvas, apps desktop ou proteções anti-bot.

### 2.3 Arquitetura-alvo em camadas

```text
Nexer Desktop (instalador Windows; shell Tauri em avaliação)
  └─ Nexer Studio (React/TypeScript: fluxos, perfis, variáveis, gravador,
                   edição/reparo, lotes, histórico, artefatos, diagnóstico)
       ↕ API local autenticada (FastAPI; loopback e políticas estritas)
  └─ Nexer Core/Engine (receitas declarativas e versionadas)
       ↕ Agente/worker local (Python + Playwright + Edge)
         ├─ navegador/perfis temporários
         ├─ execuções isoladas e canceláveis
         ├─ gravação/inspeção de elementos
         └─ downloads/artefatos verificados
       ↕ SQLite/arquivos locais/cofre do SO (secrets e estado separados)

Opcional FUTURO: Nexer Cloud (contas, sincronização, equipes, gestão de agentes)
       ↕ canal seguro e consentido com agentes locais — nunca expor o
         backend local publicamente nem presumir acesso remoto à intranet.
```

**Hospedagem na Render/Railway ou similar:** útil para **interface/contas/serviços de coordenação**, não para substituir diretamente um worker que precisa acessar Edge local, arquivos locais ou SGIND/IQOS na rede privada. Um servidor cloud comum não possui acesso à intranet corporativa nem ao navegador do usuário. Conectar cloud↔agent exige desenho de identidade, autorização, criptografia, firewall, conformidade e política corporativa; planos gratuitos têm limites que mudam. **Não é prioridade imediata.**

### 2.4 Fases de produto (direção proposta)

| Fase | Resultado esperado | Gate de saída |
|---|---|---|
| **A — Estabilização (agora)** | Gravação genérica, revisão de passos, variáveis, execução local, artefatos e testes E2E sintéticos reais | Reproduzir e baixar resultado de um fluxo genérico sem intervenção oculta |
| **B — Piloto autorizado** | Primeira receita SGIND "Todas as Ocorrências" sem codificação no núcleo | Usuário confere arquivo certo, de sua solicitação, dentro da UI; sem contornar segurança |
| **C — Nexer Desktop v1.0** | Instalador autossuficiente Windows, onboarding, atualização, logs seguros e exportação/importação de receitas | Máquina nova instala, inicia, grava, executa e remove o produto sem Python/Node manuais |
| **D — Nexer Studio 2.0** | Edição visual avançada, condições, loops, triggers, agendamento e conectores sob política | Testes de determinismo, isolamentos, permissões e UX antes de ampliar superfície |
| **E — Cloud opcional** | Sincronização, equipes, controle de agentes, política empresarial, quando houver demanda | Custos, conformidade e segurança aprovados; desktop continua útil offline |

A existência dessas fases **não implica compromisso com data nem implementação já concluída**.

## 3. Estado do Nexer observado no projeto — evidência versus intenção

| Área | Existe/foi observado | Ainda depende de implementação/homologação |
|---|---|---|
| Frontend | React + TypeScript + Vite; dashboard com fluxos/acessos/execuções; editor de receitas | UX final, onboarding de produto público, polimento, estado do worker e downloads pela UI |
| API | FastAPI, sessão local, endpoints de versão/saúde, rotas de negócios protegidas, SQLite/Alembic | ciclo de vida completo de execução, artefatos autenticados e API pronta para distribuição |
| Runtime | Playwright/Edge; receitas declarativas, query com sinais novos, downloads correlacionados, restrições e cancelamento | interpretação de casos reais diversos, isolamento robusto de jobs, adaptadores de controles adicionais |
| Gravador | Seletores estruturais, inteligência local, revisão/reparo pontual, picker visual em andamento | corrigir revisão/picker e provar replay; interface flutuante movível e sem contar cliques precisa verificação |
| SGIND/IQOS | URLs, pistas do DOM legado, alguns adaptadores/contratos corporativos e receitas preliminares | **nenhum login/consulta/CSV final de SGIND ou IQOS real foi homologado nesta conversa** |
| Execução local | `run_local.py` suporta workers; launcher usado inicia **`--api-only`** | modo explícito de execução com 1 worker saudável; inventário da fila antes de conectar |
| Instalação clone/ZIP | bootstrap `Instalar-Nexer.cmd` + PowerShell **criado e testado** em branch local; migrações e frontend aprovados em ambiente isolado | duplo clique interativo/login local, outra máquina, EXE autocontido, atualização/desinstalação |
| Hospedagem | nenhuma implantação Render/Cloud feita | estudo somente quando necessário; sem expor API/worker local à internet |

**Constatação original 14/10:** API `http://127.0.0.1:8000/version` = HTTP 200 com `Nexer API 0.1.0`; frontend `http://127.0.0.1:5173/` = HTTP 200. Processo Python rodava `scripts/run_local.py --api-only`, processo Node servia frontend; **nenhum processo `secure_main.py` observado**. `/diagnostics` sem autenticação retornou HTTP 401. Não reiniciar, não capturar filas nem assumir worker pronto porque a UI abre. Os PIDs antigos são efêmeros e precisam ser verificados de novo.

### 3.1 Recursos genéricos JÁ implementados — não reescrever sem auditoria

- **Gravador inteligente:** inteligência estrutural de seletores, espera por estados, reparo manual de alvo sem regravar a receita inteira, preservação de edições pendentes, revisão e importação validada.
- **Query correlacionada:** registra baseline; clique único; exige identificação nova específica da solicitação com estado terminal dados/vazio/erro. Resultados obsoletos não avançam; timeout não dispara segundo clique automaticamente.
- **Downloads correlacionados:** `snapshot_downloads` → `request_download` → `download` com referência `generation`; em central compartilhada a identidade precisa corresponder à confirmação **nova** e à linha de arquivo; nunca aceitar simplesmente o último arquivo ou nome/prefixo similar.
- **Picker visual de correção:** implementação histórica registrada, mas o handoff anterior aponta **bug confirmado**: fechar/recolher `details` não cancela imediatamente a sessão de seleção, permitindo resultado tardio em rascunho oculto. Verificar no código novo antes de corrigir; não declarar picker concluído.

Fontes técnicas: `HANDOFF.md`, `docs/2026-10-14-query-outcomes.md`, `docs/2026-10-14-downloads-correlacionados.md`, `docs/2026-10-14-step-review.md`, `docs/2026-10-14-contexto-completo.md` e testes associados.

### 3.2 Problemas reportados pelo usuário que exigem reteste explícito

1. Ao gerar novo token para acessar o Nexer: **"Não foi possível exibir o código localmente. Tente novamente em cinco segundos."** Verificar entrega do pareamento/token em janela e estado de sessão em inicialização fria.
2. A barra/janela flutuante do gravador **bloqueia elementos abaixo**: precisa ser **arrastável**, não gerar ações da receita nem contabilizar cliques internos. Confirmar o estado do código atual, pois houve alterações em conversas anteriores mas não há aceite E2E aqui.
3. Aba de lote/nome do arquivo: **"Não foi possível preparar as opções do site."** Em `apps/backend/app/services/report_options.py` a leitura sintética de opções rejeita URL corporativa, fragmentos hash SPA e autenticação. Para SGIND, desenvolver caminho autorizado e restrito com controle de filtros customizados, sem remover guardas globais.
4. Picker visual e sessão Edge podem permanecer ativos após fechar/recolher o editor: achado concreto da revisão histórica, requer teste regressivo e confirmação de correção na branch atual.
5. Interface disponível **não** significa processo executor ativo; execução e pronto/heartbeat devem ser visíveis ao usuário.

## 4. SGIND/IQOS: primeiro piloto real, não acoplamento de produto

**URLs depois de login fornecidas pelo usuário:**
- SGIND: `https://indicadoresenergisaess.scl.corp/sgind/#/home`
- IQOS: `https://indicadoresenergisaess.scl.corp/iqos/#/home`

**Piloto escolhido:** SGIND → **"Todas as Ocorrências"**. Fluxo esperado: usuário abre Nexer; informa credenciais corporativas **só na UI e só na execução**; seleciona empresa, data inicial/final e demais parâmetros; o worker navega autorizado, faz consulta uma única vez, comprova seu resultado e correlaciona a geração/download; valida CSV e disponibiliza na tela da execução.

**Pistas antigas, não evidência atual:** `relatorios/todas_ocorrencias.py`, componente de empresas `app-dd-empresas` / PrimeNG `p-select`, data `input.p-datepicker-input`. Não deduzir seletores, requests, nome CSV nem ID atual sem inspeção autorizada de SGIND real. Fontes `docs/2026-10-14-piloto-todas-ocorrencias-design.md` e plano de auditoria.

**Bloqueios técnicos atuais do piloto:**
- Launcher sem worker; banco/fila em uso ainda precisa de inventário antes de acionar.
- Restrições de origem e `#/home` em múltiplas camadas: cadastro/perfil, serviço de opções, API, runtime e worker; exigir matriz de política completa.
- `p-select` depende de sessão e seleção de overlay; empresa pode alterar opções dos demais filtros; datas e timezone precisam padronização.
- Identificador novo de consulta/download do portal **não observado**. Se não houver correlação suficiente, usar fluxo manual assistido e registrar bloqueio, nunca baixar arquivo de outro job.
- Ainda faltam contrato completo de artefato persistido, validação CSV ligada a `SUCCEEDED`, rota autenticada/lista/download e exposição na UI.
- Ensaio real só com autorização corporativa, usuário presente e credenciais digitadas localmente; **nunca solicitar senha no chat**.

## 5. O repositório, Git e a instalação — fotografia em 14/10/2026

**Repositório:** `https://github.com/hik4s/Nexer.git`.

**Pastas distintas e finalidade:**

| Local Windows | O que significa |
|---|---|
| `C:\Users\kis\Downloads\Nexer-codex-smart-recorder-handoff-2026-10-14` | Exportação/handoff original **sem `.git`**. Contém plano original de 26 microtarefas e dados locais. Não dar `git init` por reflexo. |
| `C:\Users\kis\Downloads\Nexer-bootstrap-test-2026-10-14` | **Checkout Git de trabalho recomendado para a próxima revisão**. Branch local `feat/nexer-portable-bootstrap-2026-10-14` criada a partir da remota abaixo. Arquivos de bootstrap **staged, sem commit/push** no final da sessão. |
| `C:\Users\kis\Downloads\Nexer-portable-acceptance-2026-10-14` | Pasta de aceitação extraída de arquivo gerado com `git write-tree` + `git archive`, sem `.git`, dados ou dependências prévias; ambiente **temporário para testes**, não fonte canônica. |
| `C:\Users\kis\Downloads\Nexer` | Checkout antigo, branch `feat/etapa1-foundation` na auditoria anterior; não sobrescrever. |
| `C:\Users\kis\Downloads\Nexer-codex-nexer-reusable-flows-2026-10-13` | Checkout anterior, branch `feat/nexer-smart-recorder`, com arquivo não rastreado; não descartar. |

**Branch de origem da nova cópia:** `codex/smart-recorder-handoff-2026-10-14`, SHA verificado `6631b6bff1bec6ea05bab430235caa9d4d01b70f`; novo trabalho em `feat/nexer-portable-bootstrap-2026-10-14`. Antes de qualquer alteração, **reexecutar `git status --short --branch`, `git log -1 --oneline`, `git remote -v`, `git diff --cached --check`**; estado pode mudar entre chats.

### 5.1 O que foi modificado para distribuição e está pendente de commit

- `.gitignore`: ignorar `.env` reais, segredos, `data/*.db`/SQLite-WAL/SHM, `venv/`, `.venv/`, `node_modules/`, downloads, logs, temporários, screenshots/artefatos gerados. **Preservar** código, assets, receitas, migrações, `package-lock.json`, requisitos e exemplos.
- `.env.example`: removidos campos antigos `SITE_USUARIO` e `SITE_SENHA`; distingue credenciais corporativas efêmeras do usuário **LOCAL** do Nexer.
- `README.md`: aviso no início para nova arquitetura; documentação histórica Streamlit/EXE legado ainda existe e precisa revisão editorial antes de uma distribuição pública.
- `data/.gitkeep`: preserva diretório vazio sem banco.
- `docs/INSTALACAO_DO_GITHUB.md`: instalação manual/assistida e verificações pré-publicação.
- `Instalar-Nexer.cmd` e `scripts/install_nexer.ps1`: bootstrap Windows que verifica Python 3.12 e Node/npm, cria `.venv`, instala requirements e `npm ci`, roda `pip check`, cria SQLite com migrations, chama `scripts/setup_auth.py` para login LOCAL e abre launcher API-only quando permitido. Fails closed se banco preexistente não autorizado, dependência ausente ou portas ocupadas.
- `scripts/requirements-windows-py312.lock.txt`: 32 pacotes Python pinados usados como `pip --constraint`, alinhados ao ambiente testado. Frontend usa lockfile npm.
- `tests/test_portable_distribution.py`: 5 testes sintéticos de layout/distribuição, regras `.gitignore`, exemplos, segurança de inicialização e exclusão do banco do índice.
- `docs/2026-10-14-verificacao-bootstrap-portavel.md`: relato de testes, limites e decisões.
- **`data/nexer.db` saiu apenas do índice Git da NOVA BRANCH** com `git rm --cached`; arquivo original no checkout permaneceu no disco. Na árvore remota/histórico ele **foi versionado anteriormente**. Revisar se continha dados sensíveis e política de remoção/rotação; `.gitignore` não apaga histórico passado. **Não editar `master`, não force-push nem reescrever histórico unilateralmente.**

Arquivos foram preparados no index/staging, mas **não foi feito `git commit`, `git push`, PR, merge ou deploy**. A branch ainda precisa ser revisada quanto a diffs, segredos, dados empresariais, direitos de publicação e histórico.

### 5.2 Evidências de teste de portabilidade — verificadas no turno anterior

1. Checkout isolado de branch legítima; `git status` verificado; source SHA registrado.
2. Pacote criado de Git tree staged sem `.git`, `.venv`, `node_modules`, `.env` ou `data/nexer.db` e com scripts, Alembic e lockfiles. Árvore de auditoria final antes do relatório adicional: `253760b74e3ebe81285a836504a95bad11e93ebf`, 447 entradas; hash **pode mudar** com novas edições/staging.
3. Em instalação extraída limpa: Python **3.12.10**, Node **24.19.0**, npm **11.17.0**, `.venv` criada, `pip install` OK, `pip check` sem conflitos, `npm ci` adicionou **168 pacotes**, migrações até **`0007_practical_workspace`**; exit 0.
4. Frontend `tsc -b` OK e Vite build OK (**119 módulos**).
5. API smoke isolado com `TestClient` usando **host e cliente loopback corretos**: `/version` e `/health` retornaram HTTP **200**; tentativa inicial do cliente padrão `testserver` retornou **403 esperado pela política local**, não falha do backend.
6. Segunda execução de bootstrap em **mesma pasta de QA**, com versões pinadas, `-UpgradeExistingDatabase -SkipAuthSetup -NoLaunch`, também exit 0.
7. Cinco testes `test_portable_distribution.py`: **5 aprovados**, 0 skips; parser PowerShell 0 erros; `git diff --cached --check` exit 0.
8. Teste negativo: bootstrap numa árvore com `data/nexer.db` preexistente e sem autorização bloqueou com **exit 1**, preservando o banco.
9. **Nenhum servidor ou worker foi iniciado** nessas verificações; usuário/senha local foram omitidos de propósito por `-SkipAuthSetup`.

**Ainda NÃO testado:** duplo clique interativo com criação de senha e abertura real em outro Windows com portas livres; ciclo completo iniciar/fechar/reiniciar/atualizar/desinstalar; EXE autocontido; todas as suítes de regressão pós-bootstrap; portal SGIND/IQOS real. O npm 11 exibiu warning de `esbuild`/`allow-scripts`, embora build Vite tenha passado. Rede corporativa pode bloquear PyPI/npm.

**Estado legado:** há `Nexer.bat` que chama `Nexer-Atualizado.exe` antigo; não confundir com novo `Abrir-Nexer.cmd` (API-only) nem com o futuro Tauri. O README antigo promete Streamlit e armazenamento de senha em `.env`, incompatível com a direção atual — manter preservado até limpar documentação explicitamente e sem quebrar quem usa legado.

## 6. Microtarefas ORIGINAIS do primeiro relatório — preservar IDs NX-*

> **Fonte principal:** `docs/2026-10-14-auditoria-microtarefas-primeiro-relatorio.md` na exportação sem Git. **26 IDs**; manter a rastreabilidade. O estado abaixo é fotografia contextual, não atualização automática do arquivo original. Para dar check, exige evidência de aceite e estado de código/branch. Marcadores: `[x]` auditado, `[~]` avanço parcial, `[ ]` pendente.

### G0 — Ambiente e origem versionada

- [x] **NX-AUD-01 [P0] — Auditoria inicial:** inventariar pastas, Git, documentação, API, frontend e worker. **Evidência:** auditoria real de 14/10, API 200, frontend 200, modo API-only, checks AST e testes direcionados.
- [~] **NX-GIT-02 [P0] — Checkout correto/isolado:** verificar remoto/SHA, criar branch limpa separada, preservar origem. **Avanço:** clone da branch `codex/smart-recorder-handoff-2026-10-14` no SHA `6631b6b`, nova `feat/nexer-portable-bootstrap-2026-10-14`; **pendente:** revisar staged, upstream, dados legados e publicação; não assumir aceita até validação final.
- [ ] **NX-OPS-03 [P0] — Inventário SOMENTE LEITURA da fila real:** status/quantidade de QUEUED/RUNNING, versão API, caminho banco e owner de jobs, sem inspecionar segredos/dados de negócio nem consumir fila. **Aceite:** mapa documentado antes de iniciar worker.
- [~] **NX-QA-04 [P0] — Sandbox reproduzível:** DB temporário, downloads temporários, portas isoladas, sem corp auth, shutdown limpo. **Avanço:** instalação/DB/compilação isoladas em ZIP; **pendente:** teste API+worker+Edge completo e cleanup sem órfãos.

### G1 — Operação e launcher

- [ ] **NX-OPS-05 [P0] — Modo de execução explícito:** opção de UI/launcher com **1 worker** no piloto e modo `--api-only` separado. **Aceite:** abrir dashboard não consome fila/gera jobs; ativação consciente.
- [ ] **NX-OPS-06 [P0] — Readiness de worker:** registrar worker, heartbeat e capacidade real; não considerar porta API = executor pronto. **Aceite:** job real bloqueado quando worker ausente com mensagem recuperável.
- [ ] **NX-OPS-07 [P0] — Lifecycle seguro:** start/stop/restart; fechar processos filhos Edge, não duplicar portas, não retomar job com resultado incerto. **Aceite:** limpeza e reconciliação testadas.
- [ ] **NX-OPS-08 [P1] — Token/pareamento local:** reinício frio, geração/exibição/expiração, múltiplas janelas, mensagens claras. **Aceite:** token visível ao dono sem log/persistência; erro anterior reproduzido e corrigido.

### G2 — Acesso SGIND e preparação de formulário

- [ ] **NX-AUTH-09 [P0] — Matriz de gates corporativos:** verificar permissões de origem/métodos/paths nas rotas unitárias, lote, opções, perfil e worker. **Aceite:** allow/deny demonstrado, sem permissão global ou bypass.
- [ ] **NX-NAV-10 [P0] — SPA `#/home` segura:** aceitar hash em URL de origem autorizada quando necessário; rejeitar credenciais em URL, redirecionamento de origem, host alternativo e queries sensíveis. **Aceite:** positivos e negativos.
- [ ] **NX-FORM-11 [P0] — Opções empresa em sessão autorizada:** obter catálogo vivo sem enviar segredos ao frontend e sem executar POST não observado/permitido. **Aceite:** opções corretas ou erro explícito, sem efeito externo indevido.
- [ ] **NX-FORM-12 [P0] — `p-select` e filtros dependentes:** relacionar overlay ao controle; não escolher primeira opção às cegas; invalidar dependentes quando empresa muda. **Aceite:** empresa/filtros corretos em fixture e portal autorizado.
- [ ] **NX-FORM-13 [P1] — Datas e timezone:** normalizar início/fim, validar intervalo e preservar fuso/semântica do portal. **Aceite:** valores transmitidos coincidem com o escolhido; entradas impossíveis rejeitadas.

### G3 — Evidência, consulta e geração do primeiro relatório

- [ ] **NX-SGIND-14 [P0, GATE HUMANO] — Inspeção SGIND AUTORIZADA:** identificar rota/DOM, estados query dados/vazio/erro, ID da solicitação, confirmação e vínculo do arquivo com job. **Aceite:** evidência sanitizada e rastreável; sem dados/credenciais no chat/arquivo.
- [ ] **NX-QUERY-15 [P0] — Adaptar contrato query JÁ existente:** confirmação NOVA e única, resultado terminal próprio; stale/vazio/erro/timeout bloqueiam, sem segundo clique silencioso. **Aceite:** testes positivos/negativos por ID de solicitação.
- [ ] **NX-DOWN-16 [P0] — Download em central compartilhada:** snapshot+generation+download correlacionados; A jamais captura B mesmo com mesma extensão/nome/padrão, reordenação e concorrência. **Aceite:** bytes comprovadamente vinculados; **sem ID forte, BLOQUEAR e oferecer inspeção/manual assistido**.
- [ ] **NX-FLOW-17 [P0] — Receita versionada Todas as Ocorrências:** empresa/período como inputs no dashboard; passos/seletores como estrutura; sem dados de login persistidos. **Aceite:** revisar/reexecutar parâmetros sem alterar identidades incorretamente.

### G4 — Artefatos CSV e conclusão verificável

- [ ] **NX-FILE-18 [P0] — Modelo de artefato:** `execution_id`/`item_id`, nome original, MIME, tamanho, hash quando útil, status validação; jamais aceitar caminho arbitrário enviado pelo cliente.
- [ ] **NX-FILE-19 [P0] — Validação real de CSV:** existência, arquivo completo, codificação, estrutura/cabeçalhos autorizados; rejeitar HTML/SSO/arquivo parcial/vazio. **Aceite:** arquivo inválido impede `SUCCEEDED`.
- [ ] **NX-FILE-20 [P0] — Listagem/GET autenticados por owner:** raiz confiável + ID persistido, proteção traversal/symlink/colisão/deleção/usuário não autorizado.
- [ ] **NX-UI-21 [P0] — Download pela tela de execução:** status, erro legível, metadata e botão/link de CSV. **Aceite:** bytes baixados da UI equivalem ao artefato validado.
- [ ] **NX-WORK-22 [P0] — Definição de sucesso e sigilo:** `SUCCEEDED` somente com artefato obrigatório validado; falha/cancelamento/timeout não são sucesso; revogar segredo em toda saída.

### G5 — Homologação e distribuição

- [ ] **NX-QA-23 [P0] — E2E isolado:** UI → API → worker → Edge → CSV → UI; DB/portas/downloads temporários, repetição de parâmetros, hash/bytes e cleanup, sem segredos nos logs.
- [ ] **NX-QA-24 [P0] — Matriz negativa:** senha errada, expiração, ausência de worker, catálogo vazio, timeout, consulta incerta, cancelamento, dois lotes, CSV inválido, reinício. **Aceite:** fail-closed e nenhum efeito duplicado.
- [ ] **NX-QA-25 [P0, GATE HUMANO] — Primeiro ensaio real SGIND:** usuário fornece credenciais apenas na UI, empresa/período, observa jornada; confirma CSV do PRÓPRIO job e conteúdo/filtros válidos. **Não executado; depende de permissão/correlação.**
- [~] **NX-PACK-26 [P1] — Distribuição/launcher:** instalar em pasta limpa, iniciar/fechar, diagnosticar, repetir E2E local sem tocar no executável em uso. **Avanço:** bootstrap a partir do ZIP e build/teste isolado; **pendente:** EXE moderno/autocontido, nova máquina, ciclo completo e homologação funcional.

**Nota de progresso:** NX-GIT-02, NX-QA-04 e NX-PACK-26 estão **parciais**, não “concluídas” apenas porque o bootstrap passou. G0/G1/G2/G3/G4/G5 continuam gates do piloto. Prioridades RPA genérico devem ser coordenadas em paralelo, sem transformar SGIND numa dependência de produto público.

## 7. NOVAS microtarefas propostas para a transição para RPA público

> IDs complementares `NX-RPA-*`; são **propostas de planejamento**, não itens já implementados. Ordenar pelos gates P0→P1→P2 e reciclar componentes existentes.

### P0 — Núcleo RPA independente de qualquer cliente/site

- [ ] **NX-RPA-01 — Contrato de produto/escopo e nomenclatura:** formalizar Nexer Desktop, Studio, Engine, Agent, receitas e conectores; requisitos de pessoa física/empresa; separar público do legado corporativo. **Aceite:** ADR + lista explícita do que v1 suporta/não suporta.
- [ ] **NX-RPA-02 — Extração da configuração corporativa:** SGIND/IQOS em adaptador/perfil privado e opcional; auditoria de strings, URLs, seletores, logs, exemplos, testes e binários antes de distribuição. **Aceite:** instalar e criar fluxo genérico sem rede/identidade corporativa; nenhum dado interno inadvertidamente publicado.
- [ ] **NX-RPA-03 — Happy path genérico mínimo:** fixture web local segura: gravar → revisar → parametrizar → executar → identificar conclusão → obter artefato → consultar histórico. **Aceite:** E2E real com Edge, duas execuções e resultados distintos.
- [ ] **NX-RPA-04 — Gravador flutuante movível e isolado:** posicionamento/drag, preferência de posição efêmera, limites de viewport e cliques da barra ignorados. **Aceite:** ações abaixo são acessíveis; arrastar/clicar no HUD não gera passo nem submissão da página; regressões mobile/desktop.
- [ ] **NX-RPA-05 — Correção do picker ao fechar editor:** quando `details` fecha, cancelar sessão imediatamente e invalidar resposta tardia; preservar alterações manuais. **Aceite:** teste RED/GREEN, reabertura coerente, Edge encerrado.
- [ ] **NX-RPA-06 — Campos dinâmicos e variáveis genéricas:** input (texto, data, empresa, arquivo autorizado, escolha), dependências e defaults explícitos; não gravar dados da sessão. **Aceite:** recipe JSON sem segredo e execução com parâmetros diferentes.
- [ ] **NX-RPA-07 — Contratos de ações e evidências:** matriz click, fill, select, navigate, wait, query, download, validate_file; tipos permitidos, retries apenas em ações idempotentes, timeout/cancelamento e limites documentados. **Aceite:** ambiguidade bloqueia e UX explica reparo.
- [ ] **NX-RPA-08 — Execução isolada por usuário/job:** browser context, diretórios, logs, filas, cancelamento, cleanup, concorrência limitada. **Aceite:** execução A não lê sessão/arquivo de B; falhas não deixam subprocessos.
- [ ] **NX-RPA-09 — Artefatos genéricos e UX de histórico:** tipos CSV e arquivos permitidos; vínculo por execution ID e download autorizado. **Aceite:** nenhuma execução sem artefato obrigatório conclui quando a receita o exige.

### P1 — Qualidade de distribuição e confiança

- [ ] **NX-RPA-10 — ADR desktop shell e empacotamento Python:** protótipo controlado Tauri+React+sidecar Python; comparar Electron e alternativas em tamanho, inicialização, WebView2, integração Edge, empacotamento, manutenção e licença. **Aceite:** decisão baseada em benchmark, não só preferência.
- [ ] **NX-RPA-11 — Instalador autossuficiente Windows:** pacote sem exigência manual de Node/Python, isolamento de dados por usuário e migrations transacionais/backup; fallback/rollback. **Aceite:** máquina virtual Windows limpa instala, inicia, executa fixture e desinstala.
- [ ] **NX-RPA-12 — Onboarding e segurança dos segredos:** primeiro usuário local, cofre do SO, política de credenciais efêmeras, recuperação de sessão/token, multiusuário e permissões; revisar `.env` local hash. **Aceite:** nenhum segredo em receitas/logs/artefatos/telemetria.
- [ ] **NX-RPA-13 — Exportação/importação de receitas:** formato versionado, validação schema, sem credenciais e sem dados corporativos; manifest/permissões; migração de versões. **Aceite:** fluxo exportado em A é validado/importado/executado em B, com consentimento.
- [ ] **NX-RPA-14 — Atualização/rollback e integridade de release:** distribuição confiável, verificação de integridade/assinatura quando viável e release notes/migrações reversíveis. **Aceite:** atualização preserva receitas e DB, falha tem recuperação.
- [ ] **NX-RPA-15 — CI e matriz de instalações:** lint, Python tests, TS/Vite, E2E Edge sintético, testes `.gitignore`/pacote e Windows clean smoke; medir dependências e avisos npm. **Aceite:** pipeline reproduzível com relatório de skips e executáveis.
- [ ] **NX-RPA-16 — Política de dados e publicação:** licença de código, nome/marca, componentes terceiros, privacidade, termos, política de vulnerabilidades, classificação de automações corporativas e arquivos de exemplo; revisão do histórico de SQLite. **Aceite:** autorização clara antes de tornar repo/release público.
- [ ] **NX-RPA-17 — Diagnóstico e suporte:** versões, worker health/heartbeat, logs sanitizados, relatórios de erro opcionais, export de suporte sem dados sensíveis. **Aceite:** usuário resolve falha comum sem intervenção de desenvolvedor.

### P2 — Expansão posterior, não bloquear MVP

- [ ] **NX-RPA-18 — Studio avançado:** condições, loops, subfluxos, variáveis entre etapas, agendamento e triggers com limites de segurança. **Aceite:** contratos declarativos e testes de corrida/retomada.
- [ ] **NX-RPA-19 — Conectores extensíveis:** interfaces para APIs/arquivos/apps desktop, política por permissão/origem, sem JS arbitrário do usuário. **Aceite:** conector de exemplo isolado sem afetar motor.
- [ ] **NX-RPA-20 — Cloud/agent opcional:** estudo de conta, sincronização e equipes, com agente local autenticado; multi-tenant/consentimento; custo real e permissões de rede. **Aceite:** protótipo seguro; nenhum acesso corporativo assumido só pela hospedagem.

### Critério comum de execução das microtarefas

Para cada item: problema e aceite verificável → teste RED (quando aplicável) → implementação mínima GREEN → regressões → `exit code` → diff → análise de privacidade/segurança → limites → status Git e documentação. **“Skip” não é “pass”; fixture não é SGIND; pacote que abre não prova que o RPA executa.**

## 8. Ordem sugerida para o próximo modelo de código — duas frentes sincronizadas

**Frente A: Core RPA público** (evita que o produto nasça acoplado ao primeiro cliente):

1. **Preparação:** rever Git/staged e banco no histórico (`NX-GIT-02`), artefatos do bootstrap e `NX-RPA-01/02/16`; decidir o que pode ser publicado. Não fazer push automático.
2. **Qualidade do gravador:** reproduzir/resolver picker (`NX-RPA-05`), HUD arrastável e clicks ignorados (`NX-RPA-04`), token local (`NX-OPS-08`). Não considerar bug histórico atual sem reteste de código.
3. **Motor genérico demonstrável:** sandbox E2E `NX-RPA-03/06/07/08/09` junto de `NX-QA-04/23/24` e artefatos `NX-FILE-18..22`. Um fluxo genérico com CSV validado deve funcionar **antes** de declarar MVP.
4. **Operação:** `NX-OPS-03/05/06/07`, com UI de modo execução e worker 1, fila isolada e diagnósticos.
5. **Distribuição:** `NX-RPA-10/11/12/13/14/15/17`, reaproveitando bootstrap já feito. Instalar do zero e repetir E2E em VM Windows sem Python/Node pré-instalados.

**Frente B: Piloto SGIND sob autorização** (prova empresarial, mas nunca requisito para usuário comum):

6. `NX-AUTH-09` + `NX-NAV-10` + `NX-FORM-11/12/13`; usar fixture com SPA hash/custom controls, guardas estritas.
7. **Gate humano** `NX-SGIND-14`: sessão autorizada, mapear consulta e identificadores download sem gravar dados sensíveis. Se insuficiente, não avançar geração automática.
8. `NX-QUERY-15`, `NX-DOWN-16`, `NX-FLOW-17`; integrar backend/runtime/worker já existentes, sem duplicá-los.
9. `NX-QA-25` ensaio real com empresa/período fornecidos no Nexer e evidência de CSV correto; gerar documentação sanitizada.

**Produto:** lançar Desktop v1 apenas depois de motor genérico validado e pacote autossuficiente; **não bloquear produto público indefinidamente por falta de acesso SGIND**, mas também **não anunciar SGIND validado** sem a homologação.

## 9. Segurança, privacidade, governança e riscos (bloqueadores de publicação)

- **Código corporativo em projeto público:** não subir nomes internos, URLs de intranet, perfis, selectors sensíveis, relatórios, amostras CSV, usuários, senhas, tokens, cookies, hashes privados ou metadados de negócio sem revisão e autorização. Mesmo nome/caminho do cliente pode revelar informação interna; tratar pelo critério de publicação.
- **SQLite no histórico:** `.gitignore` e `git rm --cached` só afetam versões futuras. Avaliar se dados confidenciais foram publicados; nunca reescrever histórico à força sem plano de comunicação, backup e permissões.
- **Por padrão, local loopback somente:** o backend usa checagens explícitas de origem/host/client; não desabilitar em nome de conveniência de Tauri, proxy ou Render. Desktop shell precisará de integração autenticada, com CSRF/origin/webview testados.
- **Execução arbitrária:** receitas declarativas, não scripts JS livres; URLs/domínios autorizados por perfil, política de método/origem, anti-SSRF e download em raiz confiável. Não executar ações que burlam captcha/MFA ou políticas do site.
- **Segredos:** credenciais digitadas a cada execução; canal efêmero e revogação em erro, logout, timeout, cancelamento e encerramento; nada em receitas/exports. `setup_auth.py` salva **hash do login LOCAL**, não a senha corporativa — decisão a rever na camada de identidade do produto distribuído.
- **Processos:** worker ausente = bloquear execução; não associar instância nova a fila desconhecida, não matar processos por nome genérico e não iniciar outro backend sobre portas ocupadas.
- **Arquivos:** garantir autoria da solicitação, rejeitar SSO HTML, CSV parcial, symlinks/traversal e dados cruzados. Não marcar job completo sem validação positiva.
- **Legal/comercial:** licenças de dependências, marca, assinaturas de código, LGPD/privacy policy e suporte são requisitos reais para distribuir a indivíduos/empresas. Custo zero de hospedagem não equivale a ausência universal de custos.
- **Cloud futura:** Render não tem acesso automático à VPN/intranet/Edge da máquina do usuário; cloud deve coordenar agente local com consentimento, não transportar senha corporativa para serviço externo sem base legal/contratual.
- **Dados de teste:** fixtures sintéticas e credenciais falsas, nunca dados reais em Git/MD. Evidências corporativas devem ser sanitizadas.

## 10. Registros de testes — para não confundir evidências históricas

- **Suite histórica antes de entrega principal:** 441 coletados, **418 passed/23 skipped** nos módulos runtime, recorder, worker, backend e frontend; com opt-ins limitados. Fonte: `docs/2026-10-14-verificacao-handoff.md`. Outras contagens posteriores de entregas (consultas/picker) estão em `HANDOFF.md` e `docs/2026-10-14-contexto-completo.md`; **não somar contagens entre momentos ou chamar todos de testes desta sessão**.
- **Auditoria direcionada da exportação:** AST de **186 arquivos Python** sem erro; `apps/backend/tests/test_report_options.py` **3/3 pass** com Edge sintético; frontend selecionado **12/12 pass** em 3 arquivos.
- **Portabilidade deste período:** bootstrap de ZIP da árvore staged, Python/npm instalados, 7 migrations até `0007`, `pip check`, TypeScript/Vite, smoke API 200/200, 5 novos testes `test_portable_distribution.py` pass, verificação de exclusões Git pass, 2a rodada com pins exit 0.
- **Não comprovado:** gravação→reprodução→arquivo entregue do **Nexer atual** em um ambiente totalmente separado ponta-a-ponta com worker real; teste de duplo clique interativo em máquina nova; SGIND/IQOS real; segurança de distribuição em múltiplos usuários; cloud.

## 11. Procedimento de retomada para PRÓXIMO CHAT — execução segura

1. **Ler este arquivo por inteiro** e depois os documentos listados na seção 12. Tratar regras de segurança, custos, papéis de IA e aceite como mandatórias.
2. Confirmar Desktop Commander online e localizar checkout **`C:\Users\kis\Downloads\Nexer-bootstrap-test-2026-10-14`**. Não supor a conexão, cwd ou branch.
3. **Antes de editar:**

   ```powershell
   Set-Location 'C:\Users\kis\Downloads\Nexer-bootstrap-test-2026-10-14'
   git status --short --branch
   git branch --show-current
   git log -1 --oneline
   git remote -v
   git diff --cached --check
   git diff --cached --stat
   git ls-files -- data/nexer.db .env
   ```

4. Revisar o staged: os arquivos de bootstrap e exclusão `data/nexer.db` estavam preparados, **sem commit**. Procurar conteúdo sensível no diff e no histórico; não apagar banco local nem empurrar branch pública sem autorização.
5. Se for **chat de arquitetura/Astra**, priorizar microtarefas, dependências, ADR do shell, modelo de segurança/distribuição e **entregar prompt/critério de aceite ao modelo codificador**. Se for **modelo de código**, implementar em etapas pequenas com TDD e sem tocar em produção.
6. Validar serviço existente antes de qualquer nova API/worker; se portas ocupadas, usar sandbox isolado, não `taskkill` genérico nem alterar banco real. Credenciais corporativas só em janela local.
7. **Primeira ação de produto recomendada:** concluir revisão de Git e fronteira público/corporativo (`NX-GIT-02`, `NX-RPA-01/02/16`), depois fechar bugs críticos da UI/picker/pareamento, e montar E2E genérico UI→API→worker→arquivo→UI antes de anunciar RPA funcional.
8. Somente com testes e aprovação do usuário decidir commit/push **da branch `feat/nexer-portable-bootstrap-2026-10-14`**, não da `master`. Não criar merge/PR por reflexo.
9. Atualizar este documento e documentação de gates à medida que houver evidências. Marcar cada tarefa parcial/concluída somente com teste/data/commit correspondentes.

### Pedido pronto para colar no próximo modelo de código

> Continue o Nexer a partir de `HANDOFF_NEXER_RPA_2026-10-14.md`. Respeite o novo objetivo de RPA desktop-first de propósito geral, as 26 microtarefas NX-* existentes e as NX-RPA-* propostas. Verifique conexão com Desktop Commander, branch/remoto, staged e histórico sensível antes de editar. Não altere master, não descarte dados nem execute workers/SGIND real sem autorização. Primeiro audite publicação segura e separe SGIND/IQOS do núcleo genérico. Em seguida corrija picker/overlay/pareamento com TDD e monte E2E sintético UI→API→worker→artefato→UI. Preserve contratos query/download, credenciais efêmeras, custo zero e evidências com exit codes. Não faça commit/push sem revisar e registrar diff.

## 12. Arquivos de referência e mapa de leitura

**Fontes nesta conversa / máquina do usuário:**

1. **Este handoff master** — produto, prioridades, auditorias e instruções de retomada.
2. `C:\Users\kis\Downloads\Nexer-codex-smart-recorder-handoff-2026-10-14\docs\2026-10-14-auditoria-microtarefas-primeiro-relatorio.md` — **26 microtarefas originais** e seus critérios mais detalhados.
3. `C:\Users\kis\Downloads\Nexer-codex-smart-recorder-handoff-2026-10-14\docs\2026-10-14-piloto-todas-ocorrencias-design.md` — fluxo e riscos de SGIND.
4. No checkout Git de bootstrap: `docs/2026-10-14-verificacao-bootstrap-portavel.md` e `docs/INSTALACAO_DO_GITHUB.md` — prova da instalação e limites.
5. `HANDOFF.md` — histórico técnico e contratos do gravador/runtime, integrações e seus limites; seções 12–14 importantes.
6. `docs/2026-10-14-contexto-completo.md` — histórico anterior, commits, picker e achados da revisão.
7. `docs/2026-10-14-verificacao-handoff.md` — 441 testes coletados/418 passed/23 skipped, antes da entrega principal.
8. `docs/2026-10-14-query-outcomes.md`, `docs/2026-10-14-downloads-correlacionados.md`, `docs/2026-10-14-step-review.md` — não reimplementar contratos já existentes.
9. `README.md`, `apps/README.md`, `apps/recorder/README.md`, `apps/runtime/README.md`, `apps/frontend/package.json`, `apps/backend/requirements.txt`, `apps/worker/requirements.txt`, `scripts/open_nexer.ps1`, `scripts/run_local.py`, `scripts/install_nexer.ps1` — verificar código/versões atuais.
10. `MASTER_PLAN.md`, `docs/development/ROADMAP.md`, handoffs anteriores `HANDOFF_NEXER_NEXT_CHAT.md` e `CONTINUAR_NEXER_*.md` — úteis historicamente, mas suas promessas antigas de Streamlit/senhas persistidas podem estar desatualizadas.

## 13. Critério final de “Nexer RPA funcional e distribuível”

**Não chamar de produto RPA funcional apenas por abrir dashboard ou empacotar `.exe`.** Mínimo verificável:

1. Novo usuário instala em Windows limpo sem dev tools manuais (quando a versão autocontida estiver pronta), com desinstalação e preservação de dados sob controle.
2. Abre o Studio, aprende fluxo por gravação, move HUD, edita/corrige alvos, não registra inputs confidenciais e configura variáveis claras.
3. Salva receita versionada, importa/exporta sem segredos e sabe quais sites/ações são permitidos.
4. Inicia worker saudável, executa em contexto isolado, cancela e visualiza erros e progresso com estados confiáveis.
5. Prova sucesso por resultado/artefato ligado ao job; baixa o arquivo correto pela interface. Ambiguidade = falha segura.
6. Resiste a testes negativos e concorrência; reinício não duplica ações de efeito incerto, não perde segredo para logs e não consome fila alheia.
7. Passa teste sintético E2E e clean-install, revisão de licenças/dados/histórico e, caso seja anunciado conector SGIND/IQOS, **homologação corporativa autorizada separada**.

**Frase orientadora:** **“Nexer: grave, personalize e execute automações confiáveis no seu próprio computador — com evidência do resultado e controle dos seus dados.”** Esta é uma proposta de posicionamento, não slogan aprovado nem promessa comercial já validada.

---

**Fim do HANDOFF MASTER — 14/10/2026.** Não excluir informação crítica sem atualizar a evidência correspondente; se o código atual discordar de qualquer afirmação histórica, a verificação empírica do checkout legítimo prevalece. Nenhuma credencial foi incluída neste documento.
