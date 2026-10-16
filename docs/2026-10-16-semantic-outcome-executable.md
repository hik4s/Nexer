# Nexer — Semantic Intelligence Engine: espera executável (16/10/2026)

## Contexto e segurança da entrega

- Diretiva: implementar SI-05 a SI-09 da especificação `docs/2026-10-16-semantic-intelligence-engine-spec.md`, evoluindo as evidências estruturais (SI-01 a SI-04) para uma espera automática reproduzível.
- Checkout: `C:/Users/kis/Downloads/Nexer-dev-2026-10-16`; branch `feat/nexer-guided-artifact-validation-2026-10-16`; origem `a1773c2e1517b31e8b8622c0ddc019b421890bbc`. Vários arquivos staged e unstaged já existiam no início desta etapa: **não resetar, não mexer em master, não fazer push/commit sem revisão**.
- Exportação em uso: `C:/Users/kis/Downloads/Nexer-codex-nexer-stability-artifacts-2026-10-15`, sem `.git`. Sincronização operacional deve ocorrer após todas as regressões e backup; sem interferir em instâncias/filas ou credenciais.
- Não foram usados SGIND/IQOS ou logins corporativos para aprender as condições. Os cenários são sintéticos no Microsoft Edge.

## Entrega de implementação

### Gravador — causa e resultado
- `apps/recorder/nexer_recorder/intelligence.js`: amplia o detector anterior para lembrar o indicador de carregamento e o **controle que ficou pronto após a ação**. Somente gera um candidato de espera se: ação anterior foi `click`, indicador ocupado foi observado surgir e terminar no mesmo escopo, resultado mudou para visível/habilitado, os seletores estruturais puderam ser extraídos, e o próximo clique foi no controle que ficou pronto. Antes do fim da gravação, o último candidato também é anexado ao clicar `Parar gravação`.
- `capture.js`: transporta candidato de conclusão como `preceding_outcome` junto do evento seguinte; no encerramento, envia um `outcome_end` com await da confirmação do backend, **antes** de abortar a sessão.
- `scripts/record_recipe.py`: extrai `preceding_outcome` **antes** da normalização de readiness, para preservar causalidade e ordenação; segue recusando contexto fora da origem/frame permitido.
- `compiler.py`: `Recording.accept_outcome` valida exatamente as chaves, alta confiança, clique imediatamente anterior, seletores limitados e ausência de duplo clique; insere `wait_for_outcome` com referência `after_step_id`, sem valores de usuário.
- `readiness.py` e `smart_waits.py`: eliminam waits de visibilidade/habilitação redundantes quando um `wait_for_outcome` imediatamente anterior já confere o mesmo controle. Respeitam waits manuais e idempotência.

### Executor — sem corrida de spinner
- `apps/runtime/outcome_wait.py` (novo): antes da ação `click`, um observador DOM de código fixo é instalado no mesmo documento; captura mudanças de busy, transição **não pronto → pronto**, erros explícitos e deadline. Faz polling de resultado sem ler conteúdo, valores ou rede; remove observador em sucesso, falha e cancelamento.
- `actions.py`, `context.py` e `runner.py`: registram ação, armam a observação *antes* do clique anterior ao wait, utilizam estado efêmero por execução e garantem cleanup. `EXECUTION_CANCELLED` retorna estado de cancelamento, não repete clique.
- `recipe.py`: mantém schema v1 e receitas antigas. Nova ação é estritamente validada com `after_step_id` apontando para clique imediatamente anterior, `ready_selector` obrigatório, `busy_selector` e `error_selector` opcionais, `ready_state` = visible/enabled, timeout 100..180000ms e aprendizado high. Proíbe scripts arbitrários, referências dinâmicas nos seletores, frames (primeira versão), retries do wait e retries do clique causador com efeitos incertos.
- **Critério de sucesso:** não basta o spinner desaparecer. O estado de resultado precisa ter sido observado mudar de indisponível para disponível após o clique; um resultado antigo já visível não libera a espera. Erro explícito retorna `OUTCOME_ERROR_STATE`; timeout retorna `OUTCOME_TIMEOUT`; perda de contexto retorna erro tipado sem URL/dados; cancelamento não segue para ação seguinte.

### Studio — revisão humana
- `apps/frontend/src/lib/stepReview.ts` e `components/StepReviewEditor.tsx`: a etapa `Aguardar resultado da operação` tem editor com condição de carregamento, seletor do resultado, estado visível/habilitado, seletor de erro e tempo limite. O usuário pode ajustar ou remover apenas esse wait, preservando o clique e marcando alterações como revisão manual. A interface apresenta confiança/inferência, sem exibir valores empresariais.

## Como as regras são realmente aplicadas

1. Clique que inicia pesquisa.
2. O gravador observa busy surgir e terminar e um controle de resultado passar a disponível. Se apenas `Loading` aparece como texto, ou spinner global fora de contexto, não é inserido wait.
3. Quando o usuário interage com o controle que ficou pronto **ou para a gravação após uma conclusão comprovada**, o compilador cria `wait_for_outcome` imediatamente após o clique causador.
4. No replay, o executor arma o observador antes de acionar o clique. Conclusão exige uma transição real; tabela/controle antigo e spinner oculto logo no começo **não** caracterizam sucesso.
5. Se faltar prova, prazo expirar, surgir erro, cancelar, navegar para outro documento ou o seletor for inconsistente: execução falha fechada, sem clique/requisição repetida.

## Limitações explícitas (não confundir com suporte universal)

- Primeira versão atua no **documento principal e em CSS selectors únicos**. Não automatiza inferência entre frames de outra origem, shadow DOM fechado, navegações que destroem o documento ou spinners globais sem vínculo estrutural.
- Uma tabela que muda apenas valores de linhas, sem modificar estado de um controle ou estado estrutural da região, **ainda não comprova conclusão**. É necessário revisar/estender o adaptador de resultado (versão futura), não presumir sucesso.
- O momento exato da transição pode ter duração menor que um `MutationObserver` consiga observar; nesses casos a automação não cria wait de alta confiança, exigindo revisão. A operação é mais conservadora que um sleep arbitrário.
- Não garante correção de dados/CSV, conteúdo de negócio, autorização de acesso, MFA ou recuperação automática de login.
- Não faz chamadas a modelos LLM, web ou serviços pagos.

## Evidências reais desta sessão

- TDD do runtime `apps/runtime/tests/test_outcome_wait_edge.py`: casos de spinner rápido, tabela/botão antigo, spinner permanente, erro explícito, prazo e cancelamento **passaram**.
- Protocolo `apps/recorder/tests/test_outcome_recording_edge.py`: contratos estritos, ordem de etapas, gravação/replay com Edge sintético e finalização após Pesquisar **5/5 aprovados**.
- `smart_waits.py`: ausência de espera redundante, manutenção dos waits manuais e idempotência **7/7 aprovados**.
- Runtime completo Edge opt-in: **176 testes, 10 pulados, exit 0 na segunda rodada**. Primeira rodada apresentou uma falha em `test_download_generation_edge.GenerationEdgeTests.test_delayed_new_job_with_same_filename_is_selected`, com `DOWNLOAD_GENERATION_TIMEOUT` porque a fixture não disponibilizou a tabela a tempo; esse mesmo teste **passou isoladamente** e toda a suíte foi repetida com sucesso. **Intermitência documentada; não ocultar**.
- Gravador completo Edge opt-in: **82/82 aprovados, exit 0**.
- Frontend: `tsc -b` e build Vite (**121 módulos**) exit 0; Vitest completo **120/120 aprovados em 32 arquivos, exit 0**. Editor da condição, remoção e revisão humana cobertos.
- Backend completo: **163 testes, 13 pulados, exit 0**. Acrescentado teste de API que cria/testa/publica versão contendo `wait_for_outcome` e recusa predecessor inválido: suíte direcionada de **9/9 aprovada** após essa adição.
- Worker completo: **45 testes, 2 pulados, exit 0**.
- Instalação/portabilidade: **20/20 aprovados, exit 0**.
- `git diff --check`, `node --check` em `intelligence.js/capture.js` e `py_compile` em módulos alterados: sem erro.
- Nenhum teste SGIND/IQOS real nesta rodada; não há comprovação do portal real, inclusive sua tabela pós-Pesquisar.

## Próximos gates

- Registrar resultados das suítes e qualquer falha intermitente (tests HTTP/Edge corporativo). Não declarar aprovado antes da execução final.
- E2E autorizado SGIND: gravar período e clicar Pesquisar, esperar conclusão, baixar relatório validado, conferir campos parametrizados e manter credenciais efêmeras. Somente após homologar essa jornada classificar como pronto para piloto real.
- SI-10+ (adapters para datepicker readonly, selects, tabelas virtuais, mensagens empty/error) e revisão de cloud/instalador desktop seguem blocos posteriores.

## Implantação local confirmada após as regressões

- Sincronizados **20 arquivos** da branch local para a exportação em uso, com comparação SHA-256 individual e backup dos arquivos anteriores: `temp/semantic-outcome-slice2-backup-2026-10-16/`.
- Testes repetidos **na exportação**: 13 testes Edge dos módulos gravador/runtime de outcome (exit 0), nove testes da API de versões (exit 0), 14 testes de revisão no frontend (exit 0) e TypeScript (exit 0).
- Verificação somente leitura do SQLite operacional: nenhuma execução, execução-automação ou worker registrado; nenhum gravador ou worker em execução. Dados locais mantidos intactos.
- Reiniciada **somente a API verificada da pasta operacional**, usando `scripts/manage_nexer.ps1 -Action restart`, exit 0. Processo anterior na porta 8000 era `run_local.py --api-only` da mesma pasta; novo PID **20172**, também `--api-only`. O Vite permaneceu na porta 5173.
- Após o reinício: GET `http://127.0.0.1:8000/version` = HTTP 200; GET `/health` = HTTP 200; GET `http://127.0.0.1:5173/` = HTTP 200.
- Estado Git local confirmado: `feat/nexer-guided-artifact-validation-2026-10-16`, sem `git commit`, `git push`, merge ou alterações na `master`; mudanças staged/unstaged preexistentes preservadas e `git diff --check` sem erro; `.env` e `data/nexer.db` não estão no índice.
- **Homologação SGIND/IQOS continua pendente.** A detecção só cria espera quando há forte evidência de atualização de um controle dentro do mesmo contexto; não promete tratar toda tabela SPA ou carregamento apenas textual.
