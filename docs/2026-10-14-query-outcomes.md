# Consultas com resultado correlacionado — 14/10/2026

O Nexer agora permite configurar, na revisão do fluxo, uma consulta que dispara uma única vez e distingue dados atuais, ausência de dados e erro. O resultado precisa apresentar o mesmo identificador novo confirmado pela solicitação. Visibilidade de tabela, spinner ou botão habilitado, sozinhos, não comprovam conclusão.

## Uso e comportamento

Na etapa Campos do cadastro guiado, abra “Consulta · ID” em um clique simples elegível. Configure confirmação, container do resultado, seletores dos três estados e prazo total. A identificação deve vir do próprio site/adaptador, nos atributos `data-query-id` ou `data-request-id`; seus valores não são guardados. Configurações pendentes bloqueiam o avanço. A navegação para fora da revisão é bloqueada enquanto houver edições pendentes. É possível descartar a edição ou voltar ao clique original durante a sessão, inclusive após ir à publicação e retornar; uma consulta importada volta a um clique simples.

- Dados correlacionados: segue para a próxima etapa.
- Ausência de dados: interrompe com `QUERY_NO_DATA`, exibindo “Consulta concluída sem dados; etapas seguintes não executadas.” O status atual é `FAILED`.
- Erro do site: interrompe com mensagem fixa, sem copiar o texto do portal.
- Resultado antigo: continua aguardando dentro do prazo.
- Resultado de outra geração, contexto trocado ou sinais conflitantes: interrompe.
- Cancelamento: chega ao worker e ao histórico como cancelado.

O clique não é repetido após timeout. O prazo inclui a preparação; varia de 1 a 900 segundos, com padrão de 180 segundos. A transferência de um relatório continua dependendo do contrato separado de downloads.

## Implementação

`query_contract.py` valida a ação declarativa; `query_execution.py` fixa documento/frame, observa confirmação com estado limitado, usa identificadores efêmeros e classifica o resultado em uma leitura DOM. A autorização ocorre antes da leitura DOM final de contexto e resultado; depois dela só são checados cancelamento, prazo e referência da página. O observador preserva evidência limitada de IDs intermediários usando registros de mutação, sem adotar silenciosamente a última geração. Mais de 1000 registros em um lote interrompem conservadoramente; só o atributo de identificação da confirmação é observado com valor anterior. Observadores e handles são liberados em todos os caminhos. Exceções inesperadas são reduzidas a código fixo e não encadeiam mensagens privadas do navegador.

Worker persiste apenas códigos de uma allowlist. A agregação de execução composta exclusivamente de itens cancelados agora mantém `CANCELLED`, mesmo sem outro flag de cancelamento no banco. Não há migração ou novo status.

A suíte revelou uma corrida preexistente no snapshot da central compartilhada: linhas eram lidas e depois contadas em outra chamada ao navegador. A verificação de completude agora acontece na mesma avaliação DOM, com regressão determinística e teste Edge de duas execuções concorrentes.

## Verificação

Verificação executada no worktree `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`, usando Python do checkout principal. Todos os módulos no PYTHONPATH apontaram ao worktree.

| Suíte | Coletados | Passaram | Pulados |
|---|---:|---:|---:|
| Runtime | 161 | 151 | 10 |
| Gravador | 54 | 54 | 0 |
| Worker | 39 | 38 | 1 |
| Backend | 144 | 132 | 12 |
| Frontend | 86 | 86 | 0 |
| Total | 484 | 461 | 23 |

Todas encerraram com exit 0. TypeScript `tsc -b` e build Vite passaram. `NEXER_RUN_RECORDER_E2E=1` habilitou os fixtures sintéticos Edge nas suítes pertinentes. Os 23 skips permanecem opt-ins de pilotos, processos/configurações e jornadas corporativas; não representam validação desses cenários.

Casos novos incluem geração nova com conteúdo idêntico, raiz reconstruída, confirmação síncrona/obsoleta/transitória, timeout, IDs inválidos, múltiplos sinais, duplicidade oculta, cancelamento, revogação, troca de documento/frame e privacidade. Backend publica e relê o contrato sem perda de campos. Worker foi exercitado com runner real e ação controlada para verificar persistência e interrupção. Frontend cobre dois editores de consulta mais download pendentes, reversão, publicação e histórico.

Testes iniciais foram observados em RED antes da implementação. Casos de aceitação adicionais do runtime foram expandidos após o primeiro GREEN; não se atribui RED individual a todos eles. Regressões de snapshot de download e de encadeamento de exceções tiveram seu próprio RED→GREEN.

QA visual do app compilado com API simulada em Edge: 1280×1000 e 390×844, campos/botões legíveis, edição bloqueando avanço, aplicação liberando avanço, sem overflow horizontal nem erro de página. Logs, script e screenshots locais estão preservados em `temp/query-outcomes/` (ignorados pelo Git).

## Limites

Primeiro contrato atende aplicações que fornecem uma identificação por solicitação verificável e não reutilizada. Um marcador global que pode refletir a consulta de outro usuário não cumpre o contrato. Não inventar contador local como substituto.

Sem validação SGIND/IQOS real. Sem navegação completa durante a consulta, shadow DOM, ramificações, retomada após restart ou repetição automática. Os estados terminais devem significar conclusão no site; o runtime não deduz isso a partir de mutações. Há janela nativa de dispatch de até 250 ms entre checagem e clique; não se promete cancelamento distribuído atômico. Avaliações JS síncronas locais não oferecem preempção de um navegador bloqueado.

Próximos avanços dependem de evidência dos componentes/portais reais e de revisão guiada mais acessível. Não houve alteração de executável, instalação, banco real ou gate corporativo.

Spec: `docs/superpowers/specs/2026-10-14-query-outcomes-design.md`. Plano e decisões de execução: `docs/superpowers/plans/2026-10-14-query-outcomes.md`. Revisão independente realizada sobre `3fb7062..477ff5d`, por agente separado (Astra). Encontrou três problemas importantes: autorização posterior ao último snapshot, perda de gerações intermediárias em mutações agrupadas e navegação que prendia edições pendentes. Todos foram reproduzidos em RED e corrigidos em uma passagem. A perda de opções originais do clique foi inicialmente classificada como menor, mas reclassificada como importante porque alterava o timeout configurado; uma asserção de igualdade direta confirmou o problema, e a regressão passou após conservar o snapshot na sessão do assistente. Correções registradas em `ede8813`. Sem achados adiados. A suíte completa foi repetida depois das correções; não houve segunda revisão independente.

## Decisões durante a execução

- Usar bookkeeping PowerShell no lugar dos scripts bash da skill: mantém ledger por plano e evidências, com custo de controle manual.
- Permitir `confirmation` de query no validador geral de downloads, mantendo as demais restrições: necessário para compartilhar o schema; regressões de download cobrem o risco de compatibilidade.
- Tornar snapshot de downloads atômico: corrige a comparação entre duas gerações da central; muda uma leitura preexistente e exige regressão de concorrência.
- Agregar todos os itens cancelados como execução cancelada, sem depender de outro flag do banco: evita diagnóstico de falha; conjuntos mistos preservam a regra anterior.
- Rejeitar duplicidades de sinais, inclusive ocultos, e lotes de mutação acima de 1000: decisão conservadora, que pode exigir adaptador em páginas muito ruidosas.
- Preservar as opções originais do clique em memória no pai do assistente: evita perder prazo ao navegar; adiciona estado de sessão, reiniciado ao importar/gravar outra receita.
- Preservar o worktree e a branch local, conforme escopo do plano; integração e publicação não foram executadas. SGIND/IQOS, dispatch nativo e navegador bloqueado mantêm os limites descritos acima.


A revisão automática de permissões bloqueou o comando que incluía remover o scratch do plano (mensagem: blocked by policy). A pasta temporária ignorada foi preservada; isso não interfere no código ou nos testes.
