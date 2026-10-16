# Nexer — validação guiada de downloads (16/10/2026)

## Origem, escopo e Git
- Referência confirmada pelo GitHub: `hik4s/Nexer`, branch `codex/nexer-stability-artifacts-2026-10-15`, commit `a1773c2e1517b31e8b8622c0ddc019b421890bbc`.
- Cópia exportada informada pelo usuário `C:/Users/kis/Downloads/Nexer-codex-nexer-stability-artifacts-2026-10-15` não possui `.git`; foi preservada. Comparação normalizada de 394 arquivos texto versionados entre exportação e clone: 0 divergências.
- Checkout separado: `C:/Users/kis/Downloads/Nexer-dev-2026-10-16`, nova branch **local** `feat/nexer-guided-artifact-validation-2026-10-16`. Não alterar `master`, não incluir `.env` ou banco local, não fazer push sem revisão e autorização específica.
- Prioridade escolhida do handoff de 15/10: arquivo real do site deve ser validado e entregue sem pedir ao usuário que adivinhe ou codifique seu nome, e o wizard deve incluir a etapa básica de validação automaticamente.

## Entregas técnicas
1. Ação `download` publica o caminho resultante em `ExecutionContext.download_outputs[step_id]` **somente após `save_as` concluir**. Mapa é efêmero e `repr=False`, limpo no início e em `finally` de `RecipeRunner.run`. O mapa de correlação da central permanece separado.
2. `validate_file` passou a aceitar `source_download: "<id_da_etapa_download>"` em vez de `path`. `recipe.validate_recipe` exige exatamente uma das referências e, para `source_download`, exige que a etapa referenciada seja um **download anterior na mesma receita**. Sem referência concluída, o runtime falha com `DOWNLOAD_SOURCE_UNAVAILABLE`; não existe fallback para caminho antigo.
3. Reaproveitada a implementação anterior de validação de tamanho/extensão/hash; o SHA-256 vincula os bytes ao item e a API já entrega o arquivo pelo handle verificado. Receitas existentes com `validate_file.path` continuam permitidas.
4. Novo helper puro `apps/frontend/src/lib/guidedFileValidation.ts`: insere uma `validate_file` com `source_download`, `min_size:1`, imediatamente após cada download ainda não associado; é idempotente e evita colisão de IDs.
5. Wizard `NewFlowPage`: integra o helper tanto após a gravação como na importação e antes da publicação. Exibe aviso da validação básica: arquivo não vazio e SHA-256 **não comprovam estrutura CSV nem conteúdo de negócio**. Edições de central mantêm a vinculação ao ID original.
6. Alterado o teste E2E do worker para forçar `preserve_filename=true` e usar fallback de nome diferente do sugerido pelo site, comprovando que o download/artefato continuam sendo `result.csv`. Não usa SGIND, credenciais ou redes reais.

## Evidências desta execução
- RED runtime: 3 novos cenários quebraram no código original (ausência de mapa, validação por `path` e falta de contrato no schema); GREEN: 3/3 passaram.
- Runtime (sem opt-ins Edge): 164 testes, 116 passaram e 48 pularam, exit 0. Skips não equivalem a execução Edge.
- Novo helper frontend: 4/4 testes OK. Wizard com regra atualizada: 5/5 testes OK. TypeScript `tsc -b` exit 0, Vite build 121 módulos exit 0.
- Backend antes do teste novo: 162 coletados, 149 passaram, 13 skips, exit 0. Teste adicional do contrato via API (teste/publicação/negação) passou; testes direcionados de versões: 8/8, exit 0.
- E2E original do worker sintético passou, e a nova versão com `source_download` + nome sugerido diferente do fallback passou (1/1). Envolve site sintético, API real, worker no processo de teste, Edge e histórico frontend. Não é teste de subprocesso do worker, login real ou portal corporativo.
- Os testes de download correlacionado da central SGIND permanecem genéricos, não validados no SGIND real. As falhas da fixture de concorrência não são sinal de sucesso corporativo.
- Frontend completo: 117/117 testes em 32 arquivos, exit 0. Worker completo: 45 coletados, 43 passaram, 2 skips, exit 0.
- A suíte Edge opt-in do runtime teve uma primeira falha intermitente em concorrência de central (A = DOWNLOAD_GENERATION_FAILED, B = B) com conexão TCP abortada pela máquina host; o caso isolado foi repetido e passou, embora a fixture ainda mostre conexão HTTP abortada. Após a correção, uma terceira execução completa do runtime com Edge terminou com 168 testes coletados, 158 aprovados, 10 skips e saída 0. Não ocultar as falhas anteriores nem os abortos HTTP registrados pela fixture.

## Limitações e próximos passos
- Verificação guiada **não** valida CSV, cabeçalhos, tipo MIME real, HTML/SSO disfarçado, valores de negócio nem limites de tamanho de arquivo. Acrescentar adaptadores de validação por tipo em tarefa independente sem supor formato CSV para todos os usuários RPA.
- Receitas antigas no Studio com validação literal permanecem compatíveis; receitas importadas que já contêm uma validação antiga com `path` precisam revisão humana quando utilizarem `preserve_filename`.
- O produto ainda não é um EXE instalável sem Python/Node. Execução real SGIND/IQOS, fila/worker corporativos, scripts com credenciais reais, nuvem e distribuição pública estão fora do escopo.
- Próximas microtarefas: a) orientar validação avançada de CSV em editor visual; b) tornar `output:file` um contrato de arquivo obrigatório para fluxos que o exigirem sem quebrar automações sem download; c) testes de lotes concorrentes/restart e monitoramento; d) remover binários/artefatos legados de distribuições, solucionar histórico de SQLite público após revisão responsável; e) empacotamento RPA Windows.
- Cada trabalho deve conservar credenciais corporativas efêmeras, receita declarativa sem JS do usuário, proteções de origem, retries seguros e nenhum worker ligado à fila do usuário sem inventário.

## Nota
Este relatório descreve código e testes locais; **não implica commit ou push**. O estado do Git e as evidências exatas devem ser revistos no fim da sessão.

## Estabilização adicional de prazos (nesta sessão)
- A suíte opt-in com Edge revelou um timeout de leitura Playwright de 1 ms classificado como DOWNLOAD_GENERATION_FAILED em vez de DOWNLOAD_CONFIRMATION_TIMEOUT. Em uma rodada também houve falha intermitente de um dos dois downloads simultâneos de uma central compartilhada; o caso isolado passou, mas a instabilidade não deve ser omitida.
- Correção delimitada em apps/runtime/download_generation.py: falha fechada na confirmação anterior quando a leitura é incerta, novo polling sem novo clique na leitura posterior transitória e código específico para tempo esgotado na avaliação da central.
- Testes novos apps/runtime/tests/test_download_generation_deadline.py: quatro RED inicialmente, depois quatro GREEN, saída 0. A bateria opt-in completa com Edge foi verificada após a correção: 168 coletados, 158 passaram, 10 pulados, exit 0.
