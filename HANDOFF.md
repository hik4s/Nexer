# HANDOFF — NEXER
**Atualizado em:** 2026-10-13 (Brasil, UTC−03)
**Objetivo:** dar continuidade ao Nexer, sem perder contexto, decisões, trabalho local e limitações de validação.
**Leia este documento integralmente antes de editar ou executar qualquer componente.**

## 1. Situação em uma frase
O Nexer é um aplicativo Windows de automação geral de navegador com ênfase em extração de relatórios corporativos (SGIND/IQOS). Há dashboard React, backend FastAPI, gravador Edge/Playwright, runtime/worker, perfis de acesso, rotinas, lotes, gerenciamento de histórico e uma primeira versão de gravação inteligente. Há avanços testados em páginas sintéticas, **mas ainda NÃO está comprovado o ciclo real de gravação → execução → download → validação no SGIND/IQOS**.

## 2. Ambiente e caminhos
- **Desktop Commander:** dispositivo Windows `ESSPPEROE-0057D`, device ID `feb2623d-1907-477f-a9c5-477d2a82c416`. Confirmar a conexão antes de trabalhar; não presumir que o dispositivo esteja online.
- **Raiz atual:** `C:\Users\kis\Downloads\Nexer-codex-nexer-reusable-flows-2026-10-13`.
- Esta pasta é **exportada e NÃO possui diretório `.git`** (verificado em 13/10). O repositório Git legítimo estava em outro computador/ambiente. Não inicializar repositório, mesclar, fazer commit/push ou alterar master sem revisar a origem, o histórico e obter autorização.
- **Novo launcher funcional:** `Nexer-Atualizado.exe` na raiz. `Nexer.bat` foi apontado para ele. **`Nexer.exe` antigo permaneceu bloqueado em uso e pode conter o erro de fonte**; não declarar que foi substituído.
- **UI atual:** `http://127.0.0.1:5173/` (Vite); **API:** `http://127.0.0.1:8000`. Antes de testar novas rotas/código de backend, reiniciar somente a API quando não houver gravação ativa.
- Windows PowerShell, Edge (canal `msedge`), Python 3.12, Node.js v24.19.0 e npm/npx disponíveis. Ambiente corporativo pode bloquear marketplace, DNS, certificados TLS e assets.
- Algumas execuções de teste exibem `Warning: Ignoring extra certs from C:\caminho\certificado-empresa.cer`; aviso ambiental observado, não confundir automaticamente com falha do gravador.

## 3. Regras inegociáveis
1. **Custo zero** para infraestrutura e funcionamento essencial. Não introduzir serviço externo pago obrigatório.
2. **Credenciais efêmeras, digitadas na UI para cada execução**, e usadas apenas naquela execução. Não guardar em `.env`, JSON de receita, gravação, banco SQLite, logs, snapshots, caches ou commits.
3. Gravação armazena **seletores, estados/condições e nomes de parâmetros**, NUNCA valores digitados, senhas, tokens, nomes de arquivos sensíveis da demonstração ou corpos de requisições. No runtime, os valores dos parâmetros são definidos no dashboard.
4. **Não modificar `master`**, nem descartar mudanças existentes. Não fazer commit/push sem auditoria e autorização. A pasta atual não tem Git.
5. **Não iniciar worker/fila real, migração de banco de produção ou autenticação corporativa SGIND/IQOS** sem ambiente/etapa autorizados e confirmação dos efeitos. Usar fixtures locais sintéticas e bancos temporários para testes.
6. Confirmar **evidências reais dos testes** (comandos, códigos de saída, falhas/skips). Não afirmar que um bug do portal foi corrigido só porque passou em fixture.
7. Usuário quer acompanhar desenvolvimento visualmente e passo a passo, com implementação concreta sempre que viável, sem ficar apenas em planejamento.
8. Reutilizar partes do RelatPy **somente se fizerem sentido**. Nome do produto e identidade oficial: **Nexer**. Evitar referências visuais legadas.
9. Compatibilidade geral: **datas, empresa, regional e relatórios são parâmetros opcionais descobertos**, não requisitos do gravador. O mesmo motor precisa funcionar em sites sem formulários e sem downloads.

## 4. Endereços fornecidos para referência (NÃO testar login automaticamente)
- SGIND: `https://indicadoresenergisaess.scl.corp/sgind/#/home`
- IQOS: `https://indicadoresenergisaess.scl.corp/iqos/#/home`
- Ambos dependem da rede corporativa e possivelmente de autenticação/sessão. Existem guardrails que rejeitam autenticação corporativa ainda não validada (ex.: `CORPORATE_AUTH_NOT_VALIDATED`). Testes locais não removem esses guardrails.

## 5. Componentes e arquivos-chave
- `apps/frontend/`: React + TypeScript + Vite; `src/pages/Dashboard.tsx`, `NewFlowPage.tsx`, `AutomationsPage.tsx`, `ExecutionsPage.tsx`, `ExecutionDetailPage.tsx`, `BatchDetailPage.tsx`, `LoginProfilesPage.tsx`; `src/lib/api.ts`.
- `apps/backend/app/`: FastAPI, schemas e modelos SQLite. `api/automations.py`, `executions.py`, `execution_batches.py`, `workspace.py`; `services/flow_recordings.py`, `services/history_deletion.py`.
- `apps/recorder/nexer_recorder/`: `capture.js` (toolbar e eventos no Edge), `compiler.py` (eventos → receita declarativa), `smart_waits.py` (**motor inteligente v1**).
- `scripts/record_recipe.py`: grava Edge, controle de sessão, correlação de downloads, `--smart-waits`; `scripts/record_flow.py`: protocolo com backend, aciona gravador com modo inteligente.
- `apps/runtime/`: `recipe.py` valida contrato de receita; `actions.py` implementa `navigate`, `wait_for`, `wait_for_any`, `click`, `download`, etc. `download.collection` pesquisa linhas pelo padrão até timeout e preserva o nome fornecido pelo site na execução.
- `scripts/nexer_desktop.py`: launcher GUI Tkinter; `scripts/manage_nexer.ps1` controla API local; `scripts/open_nexer.ps1` inicia dashboard/API; `Nexer.bat` abre o executável corrigido.
- `assets/nexer.ico`, `assets/nexer-horizontal.png`, `nexer-logo-kit/`: identidade visual oficial. PyInstaller embute o ícone e a logo no executável.
- `docs/2026-10-13-gerenciamento-exclusoes.md`, `docs/2026-10-13-launcher-nexer.md`, `docs/2026-10-13-smart-recorder.md`: documentação adicional detalhada.
- `CONTINUAR_NEXER_2026-10-13.md` e handoffs anteriores: histórico incremental, útil para detalhes, mas este arquivo é o ponto central de retomada.

## 6. Funcionalidades implementadas e estado
### 6.1 Dashboard, perfis, rotinas, lotes e histórico
- Fluxos armazenam receitas e versões; painel de parâmetros configuráveis antes da execução; perfis de acesso conceitualmente vinculados e credenciais solicitadas na execução.
- Rotinas e lotes reutilizam fluxos; resultados e históricos acessíveis pelo frontend. Trabalho real com credenciais corporativas segue pendente de validação.
- Exclusão de fluxo via `DELETE /automations/{id}`: sem histórico/rotina, exclusão definitiva; com dependências, arquivamento; com execução ativa, HTTP 409.
- Exclusão de execução via `DELETE /executions/{id}`: apenas terminal e fora de lote; exclui registros dependentes, preserva arquivos físicos. Exclusão de lote `DELETE /execution-batches/{id}`: apenas com todas as execuções terminais, sessão proprietária; arquivos preservados.
- Grupo de acesso `DELETE /access-groups/{id}` não pode ser removido enquanto perfis estiverem vinculados. Rotinas/perfis já possuíam rotas de exclusão; frontend ganhou confirmações e botões.
- O usuário relatou erro genérico `Request could not be completed` ao excluir: provável API anterior ainda em execução; `apps/backend/app/main.py` foi ajustado para mensagem mais útil em HTTP 405. Não afirmar que o problema foi validado visualmente após restart.

### 6.2 Gravador Edge
- Preparação em HTTPS: login manual fora da gravação; iniciar na URL/rota definida após login; credenciais não entram na receita.
- Captura de eventos via `capture.js`, incluindo seleção, formulário, radio, check, clique, scroll, abas, download, frames suportados, controle de conclusão via toolbar.
- F5/reload e finalização funcionaram em testes Edge sintéticos; **o bug real relatado em SGIND/IQOS não foi isolado/conclusivamente resolvido**.
- Erros `RECORDER_EMPTY`, `RECORDER_CONTEXT_UNSUPPORTED`, `RECORDER_DOWNLOAD_UNSUPPORTED`, `RECORDER_BROWSER_FAILED`, `RECORDER_CANCELLED` recebem orientação legível em `NewFlowPage.tsx`.
- Download assíncrono: `record_recipe.py` reconcilia download confirmado pelo navegador com **último clique na mesma aba em até 2,5 s, sem ações intermediárias**. `compiler.py` só promove clique correlacionado; não inventa associação nem copia o nome do arquivo. Download atrasado/ambíguo pode continuar falhando de propósito.
- Para centrais, `download.collection` permite padrão como `Relatorio_*.xlsx` definido na execução e busca linha correspondente. Dependente de seletores revisáveis e da estrutura da página.

### 6.3 Gravador inteligente v1 (IMPLEMENTADO; não é IA semântica)
- `smart_waits.py`: transformação determinística, conservadora e idempotente de receita validada, inserindo `wait_for visible` antes de ações usuais e `wait_for enabled` antes de downloads individuais. Marcadores `learning={source:automatic, confidence:medium}`.
- Para downloads em `collection`, **não** adiciona espera em botão/linha original, pois o executor já aguarda a linha pelo padrão; inserir espera do botão antigo bloquearia exportação assíncrona.
- `capture.js` observa mudanças estruturais `disabled`/`aria-disabled` e marca quando controle ficou habilitado antes da ação; backend grava espera automática `confidence:high` quando há transição observada.
- Toolbar do Edge possui **Marcar espera** para apontar elemento e indicar `visible`, `enabled`, `hidden`, `disabled`. Marcador manual preservado com prioridade; não depende de IA.
- `scripts/record_flow.py` passa `--smart-waits` nas gravações iniciadas via dashboard; uso direto do CLI legado permanece opcional.
- `NewFlowPage.tsx`, etapa **Campos**, agora contém resumo de esperas, distinguindo automáticas de manuais; permite remover sugestões automáticas. Datas não são obrigatórias; fluxos sem download têm output `none` quando pertinente.
- Limites: heurísticas gerais não equivalem a aprender todo negócio, não identificam todos loaders, SPAs, estados assíncronos complexos, desafios de login, PDFs gerados minutos depois nem seletores instáveis. Não existe ainda modelo IA local/Ollama integrado ou aprendizagem semântica universal.

### 6.4 Launcher novo e erros já tratados
- Painel local com **Abrir dashboard**, **Reiniciar API**, **Finalizar API**; encerra apenas processo local validado, solicita confirmação, não inicia worker.
- Corrigido `_tkinter.TclError: expected integer but got "UI"`: remover `window.option_add("*Font", "Segoe UI 10")`; fontes definidas por widget.
- Corrigida procura de `scripts/manage_nexer.ps1` quando executável estava em `temp/new_exe`: `find_project_root` pesquisa ancestrais.
- Build corrigido foi aberto e constatado como processo respondendo; **`Nexer-Atualizado.exe` é o binário correto na raiz**. O `Nexer.exe` antigo estava em uso/bloqueado e **não pôde ser sobrescrito**, por isso não deve ser utilizado.
- Teste real destrutivo de stop/restart API não foi realizado para evitar interromper sessões; testar com sessão ociosa.

## 7. Últimas evidências de testes (13/10/2026)
- Gerenciamento de exclusões: backend completo **143 testes, 13 skips, exit 0** na rodada correspondente; frontend **69 testes em 20 arquivos**, typecheck/build Vite OK naquela rodada.
- Correlação assíncrona de downloads no Edge: **25 testes OK**, incluindo ícone sem rótulo com download sintético e cenários de segurança.
- **Gravador inteligente v1 (rodada final): 31 testes Edge sintéticos OK (exit 0), 6 testes unitários smart-waits OK, 4 testes de NewFlowPage OK, TypeScript typecheck OK, `node --check capture.js` OK.**
- Testes usam fixtures/servidor HTTP local e banco SQLite temporário. Nenhum resultado comprova execução corporativa SGIND/IQOS.
- Não foram feitos login corporativo real, worker/fila real, migração em produção, commit/push ou merge.
- Se testar de novo, executar testes segmentados para evitar consumo excessivo. O teste Edge completo com `NEXER_RUN_RECORDER_E2E=1` pode demorar cerca de 1 minuto.

## 8. Comandos úteis no PowerShell
```powershell
cd 'C:\Users\kis\Downloads\Nexer-codex-nexer-reusable-flows-2026-10-13'
Test-Path .git
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/manage_nexer.ps1 -Action status
# Só quando nenhuma gravação estiver ativa:
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/manage_nexer.ps1 -Action restart
$env:PYTHONPATH='apps/recorder;apps/runtime;apps/backend;apps/backend/tests'
python -m unittest apps.recorder.tests.test_smart_waits -v
$env:NEXER_RUN_RECORDER_E2E='1'
python -m unittest discover -s apps/recorder/tests -p 'test_*.py' -q
cd apps/frontend
npm run typecheck
npx vitest run src/pages/NewFlowPage.test.tsx --pool=threads --maxWorkers=1
```
Não iniciar automaticamente testes integrados que conectem a sistema corporativo, worker ou banco de produção.

## 9. Próximas prioridades recomendadas
1. Verificar conexão Desktop Commander, existência de arquivos acima, hashes/executável ativo, processos da API/UI e mudanças sem Git. **Não substituir `Nexer-Atualizado.exe` pelo legado.**
2. Fazer teste local ponta a ponta autorizado da gravação inteligente: formulário SEM datas, formulário com datas, SPA sintética com carregador, botão inicialmente desabilitado, centro de downloads que gera linha tardiamente, abas/iframe, conclusão após F5. Validar a receita produzida e replay no runtime, não apenas testes unitários.
3. Melhorar **reconhecimento automático de loaders/SPA e condições de término de consultas** usando mudanças de estado do DOM; preservar origem/frames, sem coletar payloads, URLs sensíveis ou valores de usuário.
4. Melhorar estabilidade dos seletores (prioridade a atributos estáveis e verificáveis, verificação de unicidade; evitar `nth-of-type` quando frágil), e revisão visual de etapas com aprovação de condições ambíguas.
5. Evoluir download: observação de linha nova, disponibilidade de item correto, polling, limites e feedback. Não converter cliques arbitrários em download; manter safety checks.
6. Executar teste end-to-end com worker **somente sintético/autorizado**, cancelamento, resultados, artifacts, exclusões e restart/stop do launcher. Usar SQLite de teste.
7. Depois de estabilizar a base, validar SGIND/IQOS em ambiente corporativo autorizado com credenciais efêmeras e roteiros fornecidos, mantendo guardrails.
8. Recuperar Git legítimo, auditar divergências e planejar integração em branch separada; somente depois revisar commit/push.
9. IA opcional local, se útil: Ollama ou heurísticas complementares **sem enviar dados corporativos a terceiros** e sem executar código arbitrário; não tornar componente obrigatório nem assumir capacidade da máquina.

## 10. Segurança, fontes de verdade e observações
- Receita salva declara seletores, estados, labels e referências `{{variavel}}`. Não armazenar dados que usuário digitou durante a demonstração. Em particular, não persistir senhas ou arquivos/nomes provenientes da gravação.
- Não mostrar supostas evidências visuais que não foram capturadas. Logs de teste ≠ prova de funcionamento corporativo.
- Handoffs antigos podem conter afirmações sobre um executável da raiz já substituído; **prevalece o diagnóstico posterior que constatou `Nexer.exe` bloqueado e estabeleceu `Nexer-Atualizado.exe` como o launcher corrigido**.
- Diretório de backup de código anterior: `temp/NEXER_ALTERACOES_DESKTOP_COMMANDER_2026-10-13.zip` (criado antes das últimas melhorias do gravador inteligente; não substitui os arquivos atuais).
- Este arquivo é documento de transferência; **não constitui validação executável**. O próximo agente deve ler código/testes antes de modificar e registrar o que efetivamente rodou.

## 11. Pedido do usuário vigente
O usuário pediu um **gravador inteligente de scripts gerais com excelente compatibilidade para tarefas nichadas**, incluindo esperas de página, geração/ disponibilidade de download, campos opcionais, minimização da edição manual e eventual IA auxiliar. A versão v1 foi implementada e testada em Edge local, mas **não encerra** esse objetivo. Seguir desenvolvendo com segurança, foco em robustez e validação incremental.
