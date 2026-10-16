# Nexer — SI-01 a SI-04: detector estrutural de carregamento (16/10/2026)

## Escopo desta entrega

Primeira implementação local e conservadora da camada de observação do **Semantic Intelligence Engine**. **NÃO** implementa ainda o `wait_for_outcome` executável nem modifica automaticamente o JSON de receitas ou o motor de execução. Ver especificação integral em `docs/2026-10-16-semantic-intelligence-engine-spec.md` e SI-05 a SI-09.

### Git e ambiente
- Checkout versionado: `C:/Users/kis/Downloads/Nexer-dev-2026-10-16`, branch `feat/nexer-guided-artifact-validation-2026-10-16` baseada em `a1773c2e1517b31e8b8622c0ddc019b421890bbc`.
- Existem mudanças **pré-existentes** em outros módulos, inclusive staged. Preservá-las; não alterar `master`, não descartar mudanças, e não fazer commit/push sem revisão. Exportação operacional do usuário: `C:/Users/kis/Downloads/Nexer-codex-nexer-stability-artifacts-2026-10-15`, sem `.git`.
- Ferramenta: Remote Desktop Commander em Windows, testes Playwright com canal Microsoft Edge usando fixtures sintéticas; **não houve login SGIND/IQOS**.

### Código modificado

- `apps/recorder/nexer_recorder/intelligence.js`: adicionada observação de `aria-busy`, `role=progressbar` e marcador estrutural PrimeNG `data-pc-name=progressspinner`, com `MutationObserver` já existente e sem leitura de texto, valores ou network.
- Guarda um estado efêmero por **ação, geração e região estrutural** (section, form, main, article, role region ou container explicitamente marcado). Não associa spinners fora da região da ação, preexistentes nem ocultos.
- Diferencia sinais: `busy_seen`, `busy_ended`, `ready_observed`, `state` e `confidence`. Alta só com carregamento concluído e transição de controle relevante no mesmo escopo; média com carregamento concluído sem sinal terminal; baixa se ainda em andamento.
- Exporta apenas `window.__nexerIntelligence.loadingEvidence()` para avaliação **interna**. Não devolve HTML, URLs, labels, mensagens, valores, cookies, tokens, payloads ou seletores. Não persiste observação nem adiciona waits executáveis por enquanto.
- Limita os indicadores ativos a 32 por ação; aproveita limites preexistentes da observação (200 mutation records, 250 controles, 1000 nós em lote). Ao remover uma árvore DOM grande, percorre a lista limitada de indicadores, não todos os descendentes. `reset`, abort e troca de ação eliminam evidências antigas.
- `apps/recorder/nexer_recorder/capture.js`: `recordAction(element)` transmite ao observador o elemento acionado para delimitar o escopo, sem alterar o evento de receita, o clique ou os campos.

### TDD e evidências
- Adicionado `apps/recorder/tests/test_loading_observation_edge.py` com 8 cenários do Edge real (fixture local):
  1. `aria-busy` inicia e termina + controle habilitado → confiança alta;
  2. spinner que aparece e some sem resultado comprovado → confiança média;
  3. spinner em outra região e `aria-busy` que já existia → nenhuma inferência;
  4. nova ação e pausa/resume → evidencia anterior descartada;
  5. texto `Carregando` comum e campo de senha → nenhum sinal, nem segredo no resultado;
  6. spinner removido do DOM → fim identificado;
  7. `aria-busy` num elemento `hidden` → nenhuma inferência;
  8. remoção de subárvore muito grande → operação limitada, sem vazamento de conteúdo.
- Antes da implementação: 6 cenários iniciais retornaram erro por ausência de `loadingEvidence` (RED).
- Após implementação e fortalecimento: 8/8 aprovados (GREEN).
- `node --check` em `intelligence.js` e `capture.js`: exit 0.
- Regressões gerais do gravador com `NEXER_RUN_RECORDER_E2E=1`: **76/76 testes passaram**, `RECORDER_FULL_INTELLIGENCE_EXIT=0` (104,439 s de testes). Incluem Edge, gravador inteligente existente, datas, downloads sintéticos, carregamento e navegação.

### Contratos de segurança e limitações

1. **Inferência não equivale a sucesso**: botão habilitado pode significar outra coisa; sem sinal terminal seguro não inserir wait. O detector produz somente fatos de estado; não verifica conteúdo, tabela renovada, resultado de negócio nem segurança de downloads.
2. `aria-busy` sem transição observada, spinner que já estava visível ou palavra-chave no texto não comprovam vínculo com a ação.
3. A relação por escopo é conservadora: spinner global fora do container, Shadow DOM fechado, iframe diferente e muitos componentes proprietários serão inicialmente ignorados.
4. Tempo de observação máximo por ação: 30 s. Expiração ou overflow resultam na ausência de inferência, não em sucesso.
5. Sem envio a serviços externos e sem persistência dos dados privados do DOM.
6. A cópia exportada só deve ser atualizada **depois** de todas as regressões passarem, com backup das duas fontes modificadas e comparação SHA-256. Nenhuma API ou worker deve ser reiniciada para isso.

## Próximas microtarefas para o modelo de código

- **SI-05:** correlacionar explicitamente evento de conclusão à ação causadora no protocolo recorder → compilador, com ordenação, deduplicação e revisão. Não deixar eventos assíncronos se associarem à ação seguinte.
- **SI-06:** desenhar, validar e executar contrato determinístico de `wait_for_outcome` com cancelamento, prazo e pré-observação (armar antes do clique quando necessário). Sem permitir código da página no JSON.
- **SI-07:** provar por testes RED/GREEN que `hidden` imediato de spinner que ainda não apareceu e resultados antigos não liberam execução antes da hora.
- **SI-08:** garantir que `smart_waits.py` preserve wait manual, não duplica outras esperas e segue idempotente.
- **SI-09:** exibir inferência, confiança, condição, duração e motivo no Studio e permitir ajustes.
- **SI-16:** E2E sintético grava→compila→publica→executa→valida resultado (spinner rápido/tardio, sem-resultados, erro, timeout, cancellation). Piloto SGIND humano autorizado só após passar esse gate.

**Importante:** esta etapa é infraestrutura de observação testada, não o comportamento final de espera automática prometido na especificação.
