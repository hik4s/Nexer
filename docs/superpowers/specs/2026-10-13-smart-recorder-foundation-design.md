# Nexer — primeira entrega da inteligência local do gravador

Data: 13/10/2026. Estado: especificação aprovada pelo usuário nesta conversa com a resposta “Continue”. Plano aprovado e primeira entrega implementada; evidências no ledger de implementação.

## Intenção e escopo

O usuário escolheu o método B: motor genérico confiável com adaptadores reutilizáveis, inteligência local e funcionamento essencial sem custo de chamadas externas. O objetivo é demonstrar uma tarefa e obter um fluxo estável, parametrizado e útil em sites dinâmicos e ambientes empresariais.

Esta primeira entrega cobre dois fundamentos no gravador existente: identificação estrutural de alvos e integração da observação de visibilidade/habilitação. O critério é gravar uma interação, alterar a posição do alvo e reproduzir a ação correta; quando o alvo surgiu ou foi habilitado depois de uma ação anterior, a receita deve conter uma espera correspondente.

Downloads de geração longa, detecção de resultado novo em centrais, reconhecimento de ausência de dados, políticas adicionais de origem, revisão visual e novos adaptadores serão entregas seguintes. Eles precisam de contratos próprios e não serão declarados resolvidos por esta etapa.

## Base de desenvolvimento

Usar `origin/feat/nexer-smart-recorder`, commit `a414983c85bae70e23837d4934609d9824207db2`, como base. O checkout atual em `codex/nexer-reusable-flows-2026-10-13` é anterior e contém o documento de foco criado nesta conversa.

Após a revisão da especificação e do plano, desenvolver em checkout isolado a partir da branch de referência, com branch de trabalho `codex/smart-recorder-foundation`. Preservar os documentos desta conversa. Não integrar históricos independentes incidentalmente, publicar ou alterar `master`.

## Arquitetura

### 1. Identificação estrutural

Extrair a construção de seletores de `capture.js` para um módulo JavaScript do gravador, reutilizável para controles, frames, hosts de shadow DOM e destinos de arrastar/soltar.

A entrada é um elemento DOM; a saída permanece um seletor CSS compatível com o runtime atual. Nenhuma nova ação ou versão de receita é necessária nesta entrega.

Ordem de preferência:

1. Identificador estrutural permitido, único no respectivo documento/shadow root.
2. Combinação única de tag e atributos de função do controle, por exemplo `type`, `role`, `aria-haspopup` e `contenteditable`.
3. Ancoragem em ancestral estrutural único e identificação relativa do alvo.
4. Caminho posicional como fallback compatível quando não houver identificação estável verificável.

IDs semânticos já suportados continuam válidos. Novos IDs, `name` ou atributos de teste só podem ser usados conforme uma política explícita de identificadores estruturais. A política padrão usa vocabulário limitado de funções de interface; identificadores arbitrários, números de registros, UUIDs, hashes, endereços, valores de opções, `href` e atributos que possam conter segredos não são candidatos automáticos. Ampliar o vocabulário requer configuração do adaptador e evidência sintética.

Cada candidato deve apontar exatamente para o elemento demonstrado e ser único no escopo. A existência de um atributo não demonstra estabilidade por si só. O fallback posicional deve continuar documentado como frágil; este incremento não oferece reparo automático de seletor durante execução.

Em shadow DOM aberto, compor o seletor do host e do alvo interno, verificando cada escopo. Iframes mantêm a cadeia `frames` existente. Componentes não suportados conservam o diagnóstico atual.

Para coleções de download, o seletor do botão continua relativo à linha. A adoção de seletores estáveis não pode quebrar a extração existente ao trocar um caminho prefixado por um seletor global. A identificação relativa deve ser solicitada explicitamente ao módulo dentro da linha.

### 2. Observação de prontidão

Integrar `intelligence.js` ao script efetivamente instalado no navegador, com ordem de inicialização determinística. A reinicialização de captura deve limpar observers e observações anteriores para não duplicar eventos.

Observar apenas conectividade, geometria/visibilidade e estados estruturais de controles permitidos. Transições relevantes:

- Controle inexistente/oculto que se torna visível.
- Controle desabilitado que se torna habilitado enquanto está visível.
- Mudança de visibilidade do ancestral de um controle.

Uma ação gravada abre uma geração de observação. Uma transição pode sugerir espera somente para uma ação posterior no mesmo documento e na mesma geração, dentro de 30 segundos. Mudanças durante preparação HTTPS, em formulário de login ou na toolbar são ignoradas. O início da gravação cria uma nova linha de base sem aproveitar mudanças da preparação.

Uma observação é consumida uma vez. Reinicialização, reload, pausa ou troca do contexto invalidam o estado que não pertence ao documento atual. O observador precisa cobrir os contextos atualmente suportados ou se abster de emitir sugestão quando não conseguir observar o contexto.

Limitar o trabalho por lote de mutações e quantidade de controles. Ao atingir um limite, omitir a inferência; não transformar observação incompleta em condição de alta confiança. A implementação deve evitar reter elementos removidos e observers de documentos anteriores.

O marcador de confiança indica que uma transição estrutural foi observada, não que uma intenção de negócio foi compreendida nem que a ação anterior foi sua causa.

### 3. Contrato captura → compilação

Unificar `readiness` como objeto estrito `{"state": "visible" | "enabled"}` para eventos das ações `click`, `download`, `fill`, `select`, `check`, `choose`, `choose_radio` e `set_value`.

Extrair a validação e normalização da prontidão para uma função Python testável, usada pelo caminho real da CLI. A normalização produz um evento `wait_for` antes da ação, com o mesmo alvo e frames, timeout de 30 segundos e `learning={source: automatic, confidence: high}`.

Recusar tipos, campos ou estados fora do contrato. Não introduzir valores da demonstração no evento. O compilador mantém os contratos atuais de seletores, ações e variáveis.

Esperas manuais imediatamente anteriores no mesmo alvo/frame têm precedência. Não duplicar condição já registrada. O otimizador de esperas genéricas continua idempotente.

Em `download.collection`, preservar o polling existente sem adicionar espera do botão da linha original. As alterações desta entrega não ampliam a janela de correlação clique/download.

### 4. Integração e revisão

Instalar os módulos como um conjunto ordenado no caminho real da CLI e reutilizar o mesmo conjunto nos testes de captura. Não depender de ordem não garantida entre chamadas separadas de `add_init_script`.

A revisão de esperas existente no frontend continua apresentando as novas condições como sugestões automáticas removíveis. Ações sem transição observada conservam as sugestões genéricas de confiança média, quando `--smart-waits` está habilitado.

Preservar o comportamento do comando sem `--smart-waits`, incluindo esperas de transição já emitidas pela captura; documentar a distinção entre observação estrutural e o otimizador genérico.

## Privacidade e operação

Nenhuma leitura de valores de inputs, escolhas, conteúdo de downloads, cookies, tokens, screenshots ou payloads de rede é necessária. Identificadores estruturais têm política restrita; rótulos de campos continuam sob as regras existentes.

Testes usam exclusivamente páginas sintéticas, canários fictícios e diretórios temporários. Não iniciar fila real, migrar banco existente ou autenticar nos portais corporativos para desenvolver esta entrega.

## Verificação e critérios de aceite

1. Gravar clique/preenchimento em alvo estrutural único, inserir um irmão antes dele e reproduzir com novos parâmetros. O alvo correto deve receber a ação e o irmão não deve receber efeito.
2. Identificadores duplicados, dinâmicos ou sensíveis não são promovidos a seletores estáveis. Os seletores devem continuar únicos no escopo demonstrado.
3. Regredir controles comuns, shadow DOM aberto, frames de mesma origem, toolbar, reload e botões relativos de coleção.
4. No caminho real CLI, uma ação que habilita ou revela o próximo controle deve gerar condição correta, exportar receita e reproduzi-la numa página sintética com atraso diferente.
5. Preparação HTTPS não emite eventos nem aproveita mudanças anteriores ao início. Reinicializar o conjunto não duplica captura/observadores.
6. Mudanças sem uma ação anterior, observações expiradas e sinais em elementos sensíveis não geram prontidão aprendida.
7. Contratos inválidos são recusados; espera manual permanece prioritária; otimização repetida não altera novamente a receita.
8. Canários de valores preenchidos, credenciais, nomes de arquivo e identificadores dinâmicos ficam ausentes dos eventos/receitas exportados.
9. Testes direcionados novos devem demonstrar falha antes da implementação, depois aprovação. Executar suíte do gravador com Edge sintético e regressões pertinentes do runtime e protocolo backend. Validar sintaxe JavaScript e registrar resultados, skips e limitações.

## Resultado desta entrega

Um gravador que encontra melhor os mesmos controles após mudanças de posição e registra condições de prontidão que efetivamente observou durante a demonstração. Funciona com o formato de receita e a revisão existentes, sem serviço de IA externo.

Isso estabelece a base do método B. A etapa seguinte será desenhar o ciclo consulta → resultado/erro/sem dados e geração → arquivo novo → download confirmado.
