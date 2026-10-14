# Consulta com resultado verificável

Data: 14/10/2026. Estado: aprovada e implementada; evidências em `docs/2026-10-14-query-outcomes.md`.
Base inspecionada: `04fcece`, branch `codex/smart-recorder-handoff-2026-10-14`.

## Objetivo e decisões preservadas

Após demonstrar uma consulta, o usuário deve poder reproduzi-la e distinguir dados atuais, ausência de dados e erro, sem aceitar a tela da consulta anterior. Mantêm-se método B, inteligência estrutural local, receita declarativa e ausência de IA externa obrigatória. SGIND/IQOS continuam sem validação real.

O usuário autorizou continuar o desenho desse contrato. As escolhas específicas abaixo são propostas, especialmente a exigência inicial de identificador e o tratamento de ausência de dados. O objetivo não é inferir sucesso apenas porque um botão ficou habilitado.

## Alternativas e escolha

1. Ampliar `wait_for_any`: menor mudança, mas visibilidade não identifica a consulta; rejeitada como prova de conclusão.
2. Ação de consulta com confirmação e resultado correlacionados: recomendada. Explicita o vínculo, permite resultados idênticos e cabe no runner sequencial existente.
3. Interpretar livremente mudanças DOM, spinner e textos: maior cobertura aparente, mas mudança não comprova conclusão ou propriedade; não será fallback silencioso.

A primeira versão exige metadado de geração fornecido pela aplicação ou por adaptador verificado. Isso limita os sites atendidos inicialmente. Um adaptador não pode inventar um contador local e apresentá-lo como prova do servidor. Portais sem esse metadado precisam de contrato próprio, a ser especificado com evidências reais.

## Contrato declarativo proposto

Nova ação `query`, que reúne captura de baseline, clique único, confirmação e espera de desfecho. Não separar clique e espera em passos que poderiam ser reexecutados independentemente.

```json
{
  "id": "consultar",
  "action": "query",
  "selector": "button[data-action='search']",
  "frames": [],
  "timeout_ms": 180000,
  "confirmation": {
    "selector": "#query-confirmation",
    "attribute": "data-query-id"
  },
  "result": {
    "container": "#query-result",
    "attribute": "data-query-id",
    "outcomes": {
      "data": "[data-query-state='data']",
      "empty": "[data-query-state='empty']",
      "error": "[data-query-state='error']"
    }
  }
}
```

Seletores de outcomes são relativos ao container, com `:scope` permitido para o próprio container. Seletores CSS DOM, sem JavaScript do usuário, sem shadow DOM nesta primeira versão. Frames usam a resolução existente, com identidade do documento fixada durante a ação. A aba é a página atual; não há troca automática.

Validação rejeita campos desconhecidos nas estruturas novas, seletores vazios ou acima de 2048 caracteres, mais de 16 frames, outcomes faltantes/extras e seletores de outcomes literalmente iguais. Atributos permitidos: `data-query-id` e `data-request-id`. Valores são efêmeros, ASCII `[A-Za-z0-9_.-]{1,256}`, nunca interpolados em seletores. Nomes dos atributos podem persistir; seus valores não.

Prazo total de 1000 a 900000 ms, padrão 180000, contado antes da baseline e incluindo preparação, clique e espera. Um clique esquerdo simples; retry ausente ou `max_attempts: 1`. Proibir `query` com retries maiores. Receitas antigas e ações de download mantêm o contrato existente.

## Evidência e máquina de estados

1. **Preparar:** checar cancelamento/autorização e fixar página/documento/frame. Confirmação e container devem existir de forma única, mesmo ocultos. Ler os identificadores anteriores de ambos; atributo ausente ou vazio é baseline vazia, valor presente malformado é erro. A captura considera marcadores ocultos.
2. **Disparar:** observar a confirmação antes do clique para não perder atualização síncrona. Após checagem final, efetuar exatamente um clique. Falha ou timeout depois da tentativa não autoriza repetir.
3. **Confirmar:** aceitar somente confirmação única e visível com identificador válido diferente dos dois valores da baseline. O contrato do adaptador/site deve garantir que essa confirmação pertence ao clique e que o identificador não é reutilizado. Um marcador global compartilhado que possa refletir outra consulta não atende esse requisito.
4. **Esperar:** container único, conectado e visível deve expor exatamente o identificador confirmado. Resultado antigo permanece pendente, mesmo visível. Identificador novo diferente do confirmado indica substituição concorrente e interrompe; mudança da confirmação para outra geração também interrompe.
5. **Classificar:** ler identidade e os três outcomes numa mesma avaliação DOM, verificando conexão. Cada sinal pode ter no máximo um elemento correspondente; duplicidade é ambiguidade, mesmo com elementos ocultos. Zero sinais visíveis mantém a espera; exatamente um sinal visível determina o resultado; dois ou mais interrompem por conflito. Não escolher por ordem nem dar precedência automática ao erro.
6. **Encerrar:** revalidar cancelamento/autorização/contexto antes de aceitar o desfecho. Limpar referências e observadores em `finally`, inclusive em erro. Estado fica local à invocação, não em variáveis da receita, checkpoints ou banco.

Os marcadores terminais são declarações de conclusão feitas pela aplicação/adaptador. O runtime não exige estabilidade por um delay arbitrário nem trata qualquer mutação como término. Uma aplicação que publica `data` antes de concluir não cumpre esse contrato e precisa de outro adaptador.

Recriação do container no mesmo documento é permitida se unicidade, identidade e sinais forem reavaliados atomicamente; troca de documento/frame/página interrompe. Confirmação transitória removida antes de poder ser comprovada não permite inferência: a ação termina sem confirmação. Observação não deve coletar texto, HTML ou conteúdo de tabelas.

## Resultado na execução

- `data`: passo concluído; runner segue normalmente. Não comprova integridade do relatório nem sua correlação de download, que continua usando o contrato existente.
- `empty`: interrompe antes das próximas etapas com `QUERY_NO_DATA`. Nesta versão o status persistido será `FAILED`, com mensagem específica: “Consulta concluída sem dados; etapas seguintes não executadas.” Isso evita introduzir um novo status e migração de todos os consumidores. É uma limitação explícita da primeira entrega.
- `error`: interrompe com `QUERY_SITE_ERROR`, sem copiar a mensagem do portal.
- `dry_run`: valida estrutura e simula a ação; não emite afirmação de resultado real.

Não há ramificações, sucesso antecipado do fluxo ou retomada após restart nesta entrega. Essas extensões exigem semântica própria. Reexecutar o fluxo manualmente é uma nova execução; nunca há reenvio automático provocado por timeout incerto.

## Prazos, cancelamento e diagnósticos

Relógio monotônico e operações limitadas pelo prazo restante; polling de até 100 ms e limite de 250 ms por operação DOM/dispatch quando suportado. Não bloquear esperando uma condição por todo o prazo. Documentar a janela entre checagem e dispatch nativo, sem prometer cancelamento distribuído atômico. Observadores devem ser desconectados ao sair e armazenar apenas identidade limitada, sem histórico ilimitado de mutações.

Usar as verificações de autorização existentes, rejeitando página substituída. Cancelamento deve chegar ao estado cancelado do worker, não ser apresentado como erro do portal. Testar a integração, pois o runner atual converte exceções em resultado de falha.

Allowlist proposta: `QUERY_BASELINE_UNAVAILABLE`, `QUERY_IDENTITY_INVALID`, `QUERY_CONFIRMATION_TIMEOUT`, `QUERY_RESULT_TIMEOUT`, `QUERY_CONTEXT_MISMATCH`, `QUERY_SUPERSEDED`, `QUERY_OUTCOME_AMBIGUOUS`, `QUERY_NO_DATA`, `QUERY_SITE_ERROR`, `QUERY_AUTHORIZATION_REVOKED`, `QUERY_EXECUTION_FAILED`. Cancelamento reutiliza `EXECUTION_CANCELLED` e a tradução existente do worker. Erros inesperados são reduzidos a `QUERY_EXECUTION_FAILED`.

Histórico reutiliza checkpoints/status e `error_detail` já existentes, ampliando a allowlist do worker e mensagens fixas do frontend. Nunca persistir IDs de consulta, seletores resolvidos, texto de resultados, parâmetros, HTML ou exceções originais. Não criar novo canal de eventos persistidos para esta entrega.

## Integração e experiência de revisão

- Runtime: módulo puro `query_contract.py` para validação e códigos; `query_execution.py` para protocolo de navegador; integração em `recipe.py` e registry de `actions.py`. Evitar generalizar o módulo de downloads incidentalmente.
- Backend: validar/publicar receitas com a ação nova usando o mesmo validador; testar round-trip sem perda de campos.
- Gravador: a captura continua registrando o clique. Na revisão, o usuário pode convertê-lo em consulta configurada; não atribuir automaticamente significado de negócio às observações de prontidão. Preservar metadados de frame e remover opções de clique incompatíveis mediante validação explícita.
- Frontend: editor de consulta na revisão de fluxo, com confirmação, container, três estados e prazo. Validar alterações antes de avançar; permitir voltar ao clique original. Exibir a exigência de identificação da consulta e a interrupção em caso de ausência de dados. Sites sem adaptador permanecem como clique/esperas sem promessa de resultado verificado.
- Worker/histórico: códigos fixos legíveis e comportamento de interrupção/cancelamento. Nenhuma migração de banco nesta etapa.

## Critérios de aceitação e testes planejados

Fixtures locais com Edge e dados sintéticos devem cobrir:

1. Resultado anterior visível nunca conclui a nova consulta; confirmação anterior oculta também não.
2. Nova consulta com dados idênticos é aceita quando a geração é nova e correlacionada.
3. Estados data, empty e error; apenas data permite executar o passo seguinte.
4. Confirmação síncrona no clique e resultado tardio; um único clique mesmo após timeout.
5. Dois outcomes visíveis, seletores duplicados no DOM, identidade inválida e raiz ausente.
6. Recriação do container e troca concorrente de geração; nenhum resultado de outra geração aceito.
7. Cancelamento/revogação antes do clique, durante preparação/espera e antes de aceitar resultado; perda de página/frame/documento.
8. Prazo inclui preparação e não reinicia por mutação; limpeza em sucesso, erro e cancelamento.
9. IDs e conteúdo sintético sensível ausentes de eventos, checkpoints, erros persistidos e logs.
10. Validação de retry, limites, campos desconhecidos e compatibilidade das receitas anteriores.
11. Editor conserva frames, bloqueia configuração incompleta, desfaz conversão e round-trip backend preserva o contrato.
12. Worker interrompe corretamente em empty/error e traduz cancelamento; histórico apresenta mensagens fixas.

Os testes serão executados na implementação, não foram executados por esta especificação. A revisão visual do editor e regressões de downloads fazem parte da futura entrega. Teste sintético não comprova SGIND/IQOS.

## Limites e próximo passo

Sem instalação/serviço corporativo, mudanças de banco real, integração de históricos Git, APIs de IA ou alteração de executáveis. Sem suporte inicial a navegação completa durante a consulta, resultados virtualizados como evidência, canvas ou shadow fechado.

Após revisão desta especificação, produzir plano de implementação com sequência de testes e execução. A revisão precisa confirmar principalmente a cobertura inicial por identificador e a decisão de representar ausência de dados como interrupção diagnosticada no status existente.
