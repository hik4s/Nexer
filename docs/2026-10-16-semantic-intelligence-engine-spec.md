# Nexer Semantic Intelligence Engine — Especificação de arquitetura e microtarefas
**Data:** 16/10/2026
**Tipo:** planejamento técnico (não implementado por este documento)
**Produto-alvo:** Nexer RPA desktop-first, genérico, local e distribuível, sem dependência obrigatória de nuvem.
**Base auditada:** `C:/Users/kis/Downloads/Nexer-dev-2026-10-16` — branch local `feat/nexer-guided-artifact-validation-2026-10-16`, HEAD `a1773c2e1517b31e8b8622c0ddc019b421890bbc`.
**Cópia operacional:** `C:/Users/kis/Downloads/Nexer-codex-nexer-stability-artifacts-2026-10-15` (exportação sem .git).
**Status Git:** alterações locais de blocos anteriores não commitadas; não sobrescrever, descartar, alterar master ou fazer push sem revisar.

## 1. Decisão de produto

O gravador deve compreender **a intenção de uma interação**, **o componente semântico** e **a condição observável de conclusão**, em vez de persistir cada clique, cada tecla e tempos fixos. Isto deve funcionar com linguagens e frameworks diferentes e sem LLM externo, preservando o requisito custo zero e a execução em rede corporativa.

A meta não é uma IA que adivinhe arbitrariamente a finalidade do site. É um **motor determinístico de evidências, estados e confiança** com revisão humana quando o DOM não comprovar a hipótese.

Exemplo: após clicar `Pesquisar`, aparece um overlay e uma tabela atualiza. A receita ideal não é:
`click('#pesquisar') -> sleep(5000) -> click('#baixar')`.
Ela será algo como:
`click(pesquisar) -> wait_for_outcome(overlay termina + tabela pronta; erro interrompe) -> download(arquivo correto)`.

O limite importante: "escondeu o spinner" **não** comprova que a consulta terminou com sucesso. Um spinner pode sumir antes da tabela aparecer, uma tela antiga pode continuar visível, e um erro/sem-resultados pode ser o estado terminal correto.

## 2. Auditoria real: o que o Nexer já tem

| Arquivo/módulo | Recurso existente | Limitação para o objetivo |
|---|---|---|
| `apps/recorder/nexer_recorder/intelligence.js` | MutationObserver de controles, visibility/enabled, shadow DOM aberto, budgets, geração por ação; não lê valores/textos/requisições | Observa preparação de controle para *a próxima ação*, não o ciclo loading → pronto da ação *anterior* |
| `apps/recorder/nexer_recorder/readiness.py` | `wait_for` automático antes de ação quando há evidência visible/enabled | Não modela conclusão, hidden, erros, múltiplas condições ou causalidade pós-clique |
| `apps/recorder/nexer_recorder/smart_waits.py` | Esperas conservadoras antes dos controles, `--smart-waits`, idempotência, respeita waits manuais | Predominantemente prontidão para interagir; risco de redundância com espera de operação |
| `apps/recorder/nexer_recorder/capture.js` | Fills, clicks, downloads, seleção, calendário PrimeNG compatível, espera manual, eventos sem valores | Falta classificação de widgets/fluxo de ação→resultado para componentes genéricos |
| `apps/recorder/nexer_recorder/compiler.py` | Variáveis sem valores, deduplicação de fills, waits, recipe validada | Precisa correlacionar espera gerada depois do clique; eventos assíncronos e ordem de passos |
| `apps/runtime/actions.py` | `wait_for` visible/hidden/enabled/disabled, `wait_for_any`, downloads vinculados à execução | `wait_for_any` só verifica visibilidade; não há espera composta e livre de corrida para carregamentos |
| `apps/runtime/recipe.py` | Schema v1 validado e lista explícita de ações | Qualquer novo operador requer validação estrita, migração/compatibilidade e limites de tempo |
| `apps/frontend/src/pages/NewFlowPage.tsx` e revisão de passos | Gravação guiada e edição | Faltam explicação da inferência, revisão/edição do sinal e modo conservador |
| `scripts/record_recipe.py` | Playwright Edge, cookies efêmeros, fronteira de origem, preparação manual, tolerância a navegação transitória | Falhas de navegação não equivalem a um estado de conclusão/replay confiável |

**Não duplicar** recursos já implementados de `wait_for`, captura de datas, campos genéricos, download/correlação e proteção de segredos.

## 3. Como detectar carregamentos de modo genérico

**Ordem das evidências, do mais confiável ao menos confiável:**

**A. Semântica estrutural:** `role=progressbar`, `role=status`, `aria-busy=true`, elementos `inert`, bloqueio de interação, atributos/estado de carregamento, overlay modal, indicador de progresso e spinner declarado como componente. Usar a relação com o *container em que a ação ocorreu*. Apenas uma classe CSS contendo `loading` ou `spinner` não basta.

**B. Transição observada:** após o clique, o indicador realmente apareceu/tornou-se visível e posteriormente foi ocultado/removido, ou `aria-busy` mudou `false→true→false`. A evidência só é considerada se aconteceu **após a ação**, no frame/aba/escopo relevante e dentro de prazo limitado.

**C. Saída pronta:** surgimento/renovação de tabela, linhas de resultados, controle de exportação habilitado, mensagem de `sem resultados`, diálogo final, navegação concluída ou outro componente de destino inequívoco. A condição de pronto deve ser avaliada separadamente do indicador de carregamento.

**D. Erro e bloqueio:** modal de erro, alerta relevante, sessão expirada, autenticação adicional, captcha, confirmação humana, falha de carregamento; **não declarar sucesso porque o loading terminou**.

**E. Dicionário de termos como sinal complementar, nunca chave primária:** `carregando`, `aguarde`, `processando`, `pesquisando`, `entrando`, `loading`, `please wait`, `processing`, `fetching`, `loading data`, `chargement`, `cargando`, etc. Não tentar cobrir todas as línguas enumerando palavras. Só usar rótulos **de um elemento previamente identificado como status/progresso**, num classificador local/efêmero opcional, sem armazenar textos; evitar pesquisar por substring em `document.body.innerText` (pode incluir dados privados e falsos positivos).

**F. Sinais auxiliares:** mudança da URL/fragmento quando permitida e metadados de navegação; requisições relevantes ainda em andamento *somente* se isso puder ser observado sem payloads, headers sensíveis, cookies ou destinos não autorizados. `networkidle` não é definição universal de carregamento concluído, especialmente em SPA, polling e WebSockets.

Um carregamento não deve gerar `wait_for(hidden)` **isolado**, porque, no replay, o spinner pode ainda não ter surgido e a condição `hidden` seria imediatamente verdadeira. Necessário par de fases **ocupado observado → desocupado**, ou condição terminal independente comprovada. Quando nenhum sinal for inequívoco, inserir sugestão **para revisão**, não um passo automático arriscado.

## 4. Ciclo de vida e causalidade

Máquina de estados proposta para cada ação de interesse:

`BASELINE -> ACTION_COMMITTED -> OBSERVING -> BUSY_SEEN? -> READY | ERROR | AMBIGUOUS | TIMEOUT | CANCELLED`.

1. Observar o DOM *antes* do clique, criando somente metadados estruturais efêmeros da área relevante.
2. Registrar a ação com um ID estável, `tab/frame`, escopo e geração de observação.
3. Instalar observação de transições após a ação (e, quando tecnicamente viável, uma janela curta de observação começando *antes* de despachar o clique para não perder spinner rápido).
4. Correlacionar mudanças posteriores com o mesmo escopo e ação. Se houve outro clique ou troca de aba, não atribuir arbitrariamente o loading à ação antiga.
5. Quando surgir um resultado terminal verificável, criar candidato de espera **depois do passo que o causou**, antes da próxima ação dependente. Metadados: regra, grau de confiança, motivação e limite de tempo. Não persistir rótulo cru/valor do site.
6. Em erro/cancelamento/autenticação extra, marcar intervenção manual e **não** repetir a ação causadora (evita submissões e downloads duplicados).
7. Finalizar observadores na troca de página/frame, fim da sessão, pause/resume ou excesso do budget. `AbortController` e geração de observação impedem eventos tardios na gravação nova.

Recomendar níveis: **alta** (busy→ready observado no mesmo escopo), **média** (tabela/controle habilitou sem indicador de loading), **baixa** (palavra-chave, spinner global desconectado, ausência de prova). Alta pode entrar como wait automático; média como sugestão editável; baixa só como diagnóstico, nunca como step executável por padrão.

## 5. Contrato de receita proposto (NÃO IMPLEMENTADO)

Manter `wait_for` atual para pronto simples. Para fluxos com fases, considerar novo operador declarativo `wait_for_outcome` (ou composição formal equivalente) e validá-lo em `recipe.py`, `actions.py`, frontend e testes. **Não** criar código JavaScript arbitrário no JSON.

Exemplo ilustrativo, sem selectors reais:
```json
{
  "id": "wait_search_001",
  "action": "wait_for_outcome",
  "after_step_id": "search_001",
  "scope": {"selector": "#results-panel"},
  "busy": [{"selector": "[aria-busy='true']", "state": "visible"}],
  "ready": [{"selector": ".results-table", "state": "visible"}],
  "error": [{"selector": "[role='alert']", "state": "visible"}],
  "timeout_ms": 60000,
  "learning": {"source": "automatic", "confidence": "high"}
}
```

**Normas do executor:**
- A espera não dispara clique novamente; começa imediatamente após o `search_001` completar.
- Reconhecer carga que apareceu e sumiu **ou** condição de destino comprovadamente pronta/renovada; não aceitar a tabela velha se já existia antes da pesquisa.
- O runtime precisa de um baseline seguro ou token estrutural de alteração, sem capturar dados dos resultados. Se impossível provar atualização, terminar em `AMBIGUOUS`/timeout revisável.
- `busy` é opcional e não pode ser obrigação de aparecer (operação muito rápida pode terminar direto); `ready` é obrigatória ou substituída por outra condição terminal inequívoca.
- Qualquer erro relevante interrompe a espera com código específico e orienta a intervenção sem prosseguir para download.
- Todos os limites e seletores são validados, com escopo de origem/permissões; sem poll infinito e com suporte a cancelamento.
- Para textos `sem resultados`, tratar como conclusão de pesquisa válida de tipo `empty_result`, não inventar um arquivo. Downloads ainda exigem correlação e validação.

**Compatibilidade:** receitas antigas `schema_version=1` com `wait_for` precisam continuar executáveis. Avaliar introdução em schema v1 como nova ação validada ou versão 2 com migração testada; não alterar uma receita publicada sem nova versão explícita.

## 6. Ontologia de componentes do DOM para gravação inteligente

Interpretar o componente por **tipo, papel ARIA, relacionamentos, estados, sequência temporal e comportamento**, não só `tagName` ou nome da classe CSS:

| Família | Intenção normalizada | Gravação e replay esperados |
|---|---|---|
| Input simples, textarea, rich editor | Fornecer dado | `fill` parametrizado; ignorar conteúdo digitado na gravação |
| Datepicker/date-range/datetime | Informar período | Um parâmetro para início e outro para fim, formato e timezone quando comprovados; ícone/menu são detalhes internos. `readonly` exige adaptador de widget, nunca forçar valor no DOM |
| Dropdown/combobox/listbox/multiselect | Escolher opção | Capturar controle dono + variável + método de seleção. Não gravar busca interna, abertura do popup e cada clique como operações isoladas |
| Autocomplete | Consultar e escolher sugestão | Distinguir texto de busca da escolha final; replay reconsulta opções permitidas e seleciona por identidade estável, sem valores presos à gravação |
| Radio/checkbox/switch | Definir estado | Estado alvo parametrizado; `check`/`uncheck` sem toggle cego que inverta o estado |
| Slider/spinbutton/masked number | Definir número | Valor e escala/locale; operar controle acessível em vez de simular arrastar por coordenadas |
| Botão pesquisar/aplicar/filtrar | Iniciar operação | Ação `click` + espera de resultado correlacionada |
| Spinner/skeleton/overlay/busy | Estado temporário | Não gravar clique; detectar transição e disponibilidade de resultado |
| Toast/status/alert | Resultado ou erro | Diagnóstico/espera terminal conforme papel, sem gravar texto bruto ou tratar qualquer toast como sucesso |
| Modal/dialog/drawer | Contexto de trabalho | Esperar abrir/fechar, limitar seletor ao modal ativo; preservar operações explícitas do usuário |
| Tabela/grids virtuais | Seleção de registro | Agir por linha/chave contextual e estado de resultado; não depender de índice visual, posição fixa ou scroll efêmero |
| Paginação/ordenação/filtros | Modificar coleção | Parametrizar filtro significativo, esperar atualização, evitar registrar movimentos internos de DOM |
| Accordion/tab/menu | Navegar componente | Manter a intenção de trocar seção; evitar clicks internos redundantes |
| Upload | Informar arquivo | Seleção com permissão local, sem capturar bytes/nomes privados; confirmar upload concluído |
| Download/exportação assíncrona | Produzir artefato | Correlacionar requisição, central e arquivo desta execução; validar arquivo real, checksum e tipo |
| Iframe/shadow DOM | Domínio de componente | Seletores escopados e respeitar origem; shadow fechado/cross-origin sem acesso = revisão manual |
| Captcha/MFA/SSO/segredos | Verificação humana | Não inferir, armazenar nem automatizar bypass; exigir ação humana autorizada |
| Canvas/mapa/gráfico sem DOM semântico | Interação não suportada com segurança | Não inventar seletores; orientar revisão e adaptador específico |

**Regras de identidade/escopo:** priorizar acessibilidade (`role`, label associado), `id`/atributos estáveis e relação com o container; depois CSS estrutural que resista a re-render. Rejeitar seletor ambíguo, dinâmico ou que aponte para outro campo após mudança de layout. Para máscaras, inferir formato apenas de metadados estruturais estáticos e reconhecidos; nunca da data ou segredo digitado.

## 7. Compatibilidade, desempenho e segurança

- **Local e custo zero:** primeira versão 100% regras locais determinísticas, sem LLM externo/telemetria. IA ou modelos locais opcionais apenas em fases futuras, sempre sem envio de DOM corporativo à nuvem.
- **Privacidade:** não capturar valores de controles, texto das linhas, corpo de requisição, respostas, cookies, tokens, URL com parâmetros privados, credenciais ou conteúdo de e-mails. Observações efêmeras e descrições de causas não persistem dados de negócio.
- **Origem/credenciais:** manter autenticação efêmera em cada execução e preparação manual. Não relaxar whitelist/origin nem contornar WAF/captcha/CSP/SSO.
- **Runtime reproduzível:** separação entre *gravar* e *executar*. Não inserir waits dinâmicos que só funcionam na sessão gravada. A solução deve resistir à página já renderizada, spinner rápido ou inexistente, componente recriado e acesso simultâneo a abas.
- **Não repetição:** erro, timeout ou resultado incerto em `Pesquisar`/downloads nunca devem disparar clique de novo automaticamente.
- **Budgets:** conservar limites de `intelligence.js` (atualmente 200 registros/250 controles/1000 nós por lote), com coalescência, `MutationObserver` seletivo e limpeza. Medir custo real em fixtures antes de elevar limites.
- **Revisão humana:** Studio deve mostrar o passo `Aguardar conclusão da pesquisa`, gatilho/resultado detectado, origem da inferência, nível de confiança, timeout e ação para editar/remover. Sugestões de confiança média não entram silenciosamente como condições obrigatórias.
- **Erros legíveis:** diferenciar `LOADING_TIMEOUT`, `RESULT_NOT_READY`, `PAGE_ERROR_STATE`, `AMBIGUOUS_OUTCOME`, `UNSUPPORTED_WIDGET`, `FRAME_ACCESS_DENIED` e `EXECUTION_CANCELLED`; não enviar mensagens genéricas que ocultem o estágio.

## 8. Microtarefas para o modelo de código (TDD, em sequência)

| ID | Prioridade | Mudança implementável | Critério de aceite verificável |
|---|---|---|---|
| SI-01 | P0 | Inventariar waits/replay atuais, congelar regressões e fixtures | Suite base verde, testes novos RED com spinner e resultado atrasado |
| SI-02 | P0 | Detector estrutural ocupado/desocupado scoped no `intelligence.js` | `aria-busy`, progressbar, overlay detectados; falsos positivos da página não |
| SI-03 | P0 | Correlacionar `click -> transition -> ready` por aba/frame/generation | Spinner de outro painel/aba ou antes do clique não produz wait |
| SI-04 | P0 | Contrato interno de evidências tipadas sem valores/textos | Testes inspecionam JSON de eventos e impedem canários pessoais |
| SI-05 | P0 | Atualizar `capture.js`/protocolo e `compiler.py` para passos pós-ação | Espera após `Pesquisar`, antes da próxima ação; nenhuma duplicação |
| SI-06 | P0 | Validar schema de espera composta + implementar executor cancelável | Operação rápida, lenta, spinner ausente, resultado atrasado, erro explícito |
| SI-07 | P0 | Eliminar race `hidden` antes de spinner aparecer | Não prossegue sobre tabela velha, sem sleep fixo, sempre timeout limitado |
| SI-08 | P0 | Preservar `readiness.py`/`smart_waits.py` sem esperas redundantes | `optimize_recipe` idempotente; espera manual tem prioridade |
| SI-09 | P0 | Status do Studio para espera inferida e revisão | Usuário vê o que aguarda, por quê e timeout; pode ajustar sem JSON manual |
| SI-10 | P1 | Ontologia de `datepicker`, inclusive readonly sob adapter controlado | Date start/end parametrizados; readonly não recebe `fill` inseguro |
| SI-11 | P1 | Combobox, autocomplete e multiselect sem clicks efêmeros | Um parâmetro por escolha; testes PrimeNG e HTML/ARIA genérico |
| SI-12 | P1 | Modais, toasts, erro e sem resultados com condições terminais | Erro bloqueia download, resultado vazio encerra consulta corretamente |
| SI-13 | P1 | Tabela virtual, paginação e seleção relativa por identidade | Mudança de paginação/layout não clica linha incorreta |
| SI-14 | P1 | Upload, slider, máscara de número, switches e rich text | Parametrização estável sem gravação de bytes/conteúdos |
| SI-15 | P1 | Orquestrar iframes, abas, SPA e Shadow DOM aberto com cancelamento | Não mistura gerações nem atravessa origens não autorizadas |
| SI-16 | P0 | E2E em Edge com cenários de loading + clique + exportação | Grava→compila→publica→executa→valida artefato local em fixture |
| SI-17 | P1 | Testes negativos e de privacidade/segurança | Login/MFA/captcha excluídos, nenhum dado/cookie/segredo exportado |
| SI-18 | P2 | Métricas locais de confiança e latência com opt-out | Sem armazenar valores, sem degradar recorder ou travar interface |
| SI-19 | P2 | Avaliar adaptadores opt-in por framework/site e seletor alternativo | Sem adicionar código SGIND ao core do RPA; limites explícitos |
| SI-20 | P0 | Piloto humano autorizado SGIND/IQOS sem logs sensíveis | Evidência de gravação persistente após Pesquisar, datas trocadas e relatório validado, respeitando acesso corporativo |

## 9. Matriz mínima de testes sintéticos

**Carregamento:** nenhum spinner; spinner 30ms; spinner tardio; spinner permanente; dois spinners independentes; busy true→false; spinner desaparece mas resultado atrasa; resultado antigo já visível; erro de permissão; alerta de sessão expirada; "Carregando" como texto comum de tabela; SPA troca de rota; scroll e popup; página fechada durante espera; cancelamento humano.

**Widgets:** dois calendários text-mask; data `readonly`; data e hora em componentes diferentes; dropdown sobreposto; multiselect; autocomplete assíncrono; switch e radio; seletor repetido em modal e no fundo; tabela virtual com linhas recicladas; download central com nome do site alterado; sombra aberta; iframe restrito; vários idiomas.

**Segurança:** campo senha em mesmo formulário; página de login antes de iniciar; captcha/OTP; projeto exportado sem valores; cross-origin abortado; progressbar falso surgido em outro frame; mutações acima do budget; memória/cache zerada após abort; old schema continua válido.

**Aceitação geral:** para cada operação automaticamente classificada, replay deve produzir o mesmo **estado verificável**, e nunca ser aprovado apenas pela ausência do spinner ou pelo decurso de um temporizador. Toda inferência ambígua é revisável e nenhuma tarefa dá retry com efeitos colaterais sem decisão explícita.

## 10. Sequência recomendada e papel dos modelos

**Bloco A — SI-01 a SI-09 + SI-16:** esperar corretamente após pesquisar, sem erros e sem regressões. É a prioridade antes de generalizar interpretação de outros widgets.

**Bloco B — SI-10 a SI-15 + SI-17:** identidade semântica de objetos e generalização para plataformas RPA de terceiros. Priorizar calendários e combos; depois tabela, modais, outros widgets.

**Bloco C — SI-18 e SI-19:** indicadores locais de qualidade e adaptadores. Cloud permanece **opcional e futura**, não dependência do motor.

**Bloco D — SI-20:** homologação corporativa autorizada com evidências reais, após estabilidade sintética. Não fingir teste SGIND só porque uma fixture se parece com o portal.

Conforme a regra do projeto, o modelo Astra deve definir arquitetura, riscos, gates e microtarefas; Codex/Copilot ou outro modelo de código implementa tarefas pequenas com RED→GREEN→refactor→suite. Verificar branch e alterações atuais antes de qualquer implementação, **sem alterar `master`, sem descarte e sem commit/push automático**.

## 11. Perguntas técnicas a resolver em implementação

1. Como o gravador aprende uma saída estruturalmente igual à tabela anterior quando apenas os registros mudam e os valores de negócio são proibidos de capturar? Se não houver sinal estrutural ou ID de consulta não sensível, classificar como **ambígua** e pedir confirmação humana.
2. Como representar `sem resultados` e `erro` como estados finais distintos para fluxos cujo objetivo é gerar CSV? Execução pode terminar sem arquivo com erro de negócio próprio, não "sucesso vazio" inventado.
3. Quais componentes reais de frameworks diferentes expõem informação suficiente sobre propósito, sem conhecer os nomes das classes CSS? Detector genérico deve tentar ARIA/estrutura antes de adaptadores.
4. Quando uma ação causa navegação para um novo documento, que parte do snapshot do frame pode ser correlacionada sem manter referências DOM inválidas? Usar geração por documento + vínculo no host autorizado.
5. Como garantir nenhuma regressão no tratamento de downloads assincrônicos correlacionados e no login efêmero? Gates obrigatórios antes da expansão dos objetos.

**Status deste documento:** auditoria + proposta revisável. Nenhum `wait_for_outcome` novo foi implementado por esta especificação.
