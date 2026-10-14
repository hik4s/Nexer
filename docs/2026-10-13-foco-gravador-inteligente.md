# Nexer — foco de desenvolvimento do gravador inteligente

Data: 13/10/2026.

Documento solicitado pelo usuário para preservar a análise anterior do GPT Astra e a direção escolhida na conversa. É uma consolidação do diagnóstico e das decisões, não uma transcrição literal nem uma declaração de implementação concluída.

## 1. Objetivo acordado

Evoluir o Nexer para gravar tarefas do navegador de forma estável, reutilizável e versátil, atendendo uso cotidiano, sites dinâmicos e ambientes empresariais.

O usuário demonstra a tarefa uma vez. O gravador interpreta ações e mudanças da página, produz uma receita parametrizada e permite repetir a tarefa com entradas diferentes. A intervenção humana fica concentrada em alvos e condições ambíguos ou componentes sem estrutura acessível.

Inteligência, neste projeto, significa identificar o alvo certo, reconhecer quando avançar, confirmar o resultado e explicar quando precisa de ajuda.

## 2. Método B escolhido

Nesta conversa, **método B** corresponde à segunda abordagem apresentada no diagnóstico: **motor genérico confiável com adaptadores reutilizáveis por componente ou site**.

Esta escolha é independente da antiga “opção B” de credenciais temporárias mencionada nos handoffs. As regras de credenciais efêmeras continuam aplicáveis.

A inteligência será local, baseada inicialmente na estrutura DOM, acessibilidade, eventos e transições de estado. O funcionamento essencial terá custo zero de infraestrutura e de chamadas externas.

API externa de IA fica fora da direção escolhida. Um modelo de linguagem local também não é requisito desta etapa. Seu uso futuro só faria sentido após demonstrar benefício concreto em casos que o motor estrutural não resolve.

## 3. Base analisada e limites das evidências

- Branch de referência: `feat/nexer-smart-recorder`.
- Commit analisado: `a414983c85bae70e23837d4934609d9824207db2`.
- A leitura foi feita diretamente da referência remota, preservando o checkout local.
- O checkout local, na criação deste documento, está em `codex/nexer-reusable-flows-2026-10-13` e contém uma versão anterior. O código do diagnóstico não deve ser presumido presente nessa branch.
- Os números de testes citados pelos handoffs são evidências históricas. Nenhum serviço ou teste foi executado durante o diagnóstico desta conversa.
- A jornada real de gravação, reprodução, download e validação em SGIND/IQOS permanece pendente.

## 4. O que já existe na branch de referência

- Frontend React, API FastAPI, SQLite, eventos SSE, worker e runtime Playwright/Edge.
- Biblioteca de fluxos, receitas versionadas, parâmetros por execução e publicação com validação estrutural.
- Perfis de acesso sem credenciais persistidas e entrega efêmera de credenciais para execução.
- Gravação integrada ao cadastro de fluxos, preparação manual de login HTTPS e conclusão pela toolbar.
- Captura de diversos controles, abas abertas pelo fluxo, iframes da mesma origem e shadow DOM aberto.
- Esperas manuais e sugestões automáticas de visibilidade e habilitação.
- Downloads individuais e busca por padrão em tabelas/listas.
- Rotinas, lotes, execução isolada por processos, cancelamento e histórico.

Essa base deve ser aproveitada. Gravação inteligente v1 não comprova compatibilidade geral com sites complexos.

## 5. Achados concretos do diagnóstico

### Observação inteligente ainda não integrada

`apps/recorder/nexer_recorder/intelligence.js` contém observação adicional de mudanças estruturais, mas não foi encontrado seu carregamento no caminho atual de `scripts/record_recipe.py`.

O formato de `readiness` produzido por esse arquivo também difere do formato aceito pelo coletor Python. Antes de ativá-lo, é necessário definir um contrato único entre observador, captura, compilador e runtime.

### Seletores frágeis em tarefas gerais

`capture.js` usa principalmente caminhos posicionais com `nth-of-type`. IDs estáveis recebem tratamento privilegiado apenas para alguns campos conhecidos, como datas, empresa e regional.

Mudanças na posição de elementos podem quebrar a reprodução ou apontar para outro alvo. A estratégia precisa servir igualmente a tarefas sem esses campos.

### Esperas não confirmam conclusão de negócio

O otimizador atual insere principalmente condições `visible` e `enabled`. Um botão visível ou habilitado não comprova que uma consulta terminou, que os resultados estão atualizados ou que um arquivo foi gerado.

### Downloads têm associação e seleção limitadas

A correlação automática de download observado com clique recente usa uma janela de até 2,5 segundos, na mesma aba e sem ações intermediárias. Geração demorada exige representação própria.

Downloads em coleção selecionam a primeira correspondência do padrão na ordem do DOM. Isso pode encontrar um arquivo antigo; ainda é necessário distinguir o resultado da execução atual e tratar múltiplas correspondências.

### Documentação e origem precisam ser consolidadas

Há documentos antigos descrevendo funcionalidades como futuras, gravação apenas local e autenticação já substituída. Notas recentes e código devem orientar a atualização.

A referência remota analisada apresenta um commit sem pais, um banco SQLite versionado e uma referência Git aninhada chamada `Nexer`. Antes de integrar trabalho ao histórico existente, revisar a origem e esses itens. O conteúdo do banco não foi examinado.

## 6. Frentes de foco

| Frente | Resultado esperado |
|---|---|
| Identificação de alvos | Usar atributos estruturais estáveis e contexto; verificar unicidade e indicar ambiguidade. |
| Interpretação de ações | Distinguir preenchimento, escolha, consulta, abertura de menu, geração e obtenção de arquivo a partir de sinais verificáveis. |
| Estados e esperas | Relacionar a ação a transições observadas: carregamento, habilitação, surgimento de resultado, erro ou ausência de dados. |
| Downloads | Separar solicitar geração, aguardar disponibilidade e baixar; evitar selecionar arquivo antigo ou arbitrário. |
| Componentes complexos | Adaptadores reutilizáveis para calendários, listas customizadas, tabelas virtualizadas e controles equivalentes. |
| Revisão e reparo | Linha do tempo compreensível, destaque do alvo e correção de uma etapa sem regravar todo o fluxo. |
| Preservação da gravação | Manter etapas válidas como rascunho incompleto quando surgir ação não suportada; impedir execução/publicação sem resolver a pendência. |
| Confirmação e recuperação | Pós-condições verificáveis e regras explícitas de repetibilidade antes de repetir ações com efeitos. |
| Compatibilidade empresarial | Política explícita de origens e recursos necessários por site, autenticação assistida e validação no ambiente autorizado. |

Rótulos e atributos usados para identificar elementos precisam passar por critérios de privacidade. Nem todo texto, ID ou nome existente no DOM é um metadado seguro para persistir.

## 7. Como a inteligência deve funcionar

1. **Observar:** coletar eventos e mudanças estruturais permitidas enquanto o usuário demonstra a tarefa.
2. **Identificar:** associar a interação ao controle correto, ao contexto de frame/aba e a candidatos de seletor verificáveis.
3. **Interpretar:** reconhecer padrões de interação e estados com evidência; marcar incertezas em vez de presumir intenção de negócio.
4. **Compilar:** gerar receita declarativa com parâmetros, condições e origem das sugestões.
5. **Revisar:** mostrar ações, campos, condições e pendências de forma compreensível.
6. **Reproduzir e confirmar:** executar com novas entradas, verificar condições e resultados, e interromper com diagnóstico quando houver divergência.

O motor genérico resolve padrões comuns. Adaptadores acrescentam conhecimento sobre componentes ou sites específicos por interfaces definidas, sem espalhar regras particulares por todo o produto.

Para componentes sem estrutura acessível, a direção alinhada é seleção ou correção assistida pelo usuário. O método concreto desse recurso ainda precisa de desenho: selecionar um elemento não resolve, por si só, canvas ou shadow DOM fechado.

## 8. Ordem recomendada de entregas

### Entrega 1 — base coerente

Consolidar a documentação operacional, definir a base Git para desenvolvimento e unificar o contrato de observação inteligente. Mapear os cenários sintéticos já existentes e as lacunas de gravação/reprodução.

### Entrega 2 — estabilidade do fluxo principal

Melhorar identificação de alvos e seletores, esperas por resultado e downloads demorados. Esta é a primeira entrega funcional prioritária.

### Entrega 3 — revisão e reparo

Oferecer revisão visual das etapas, explicação das condições inferidas, correção pontual e preservação de rascunhos incompletos.

### Entrega 4 — compatibilidade empresarial

Definir e validar políticas necessárias por site, componentes especiais, login em etapas, intervenção para MFA e tratamento de sessão expirada. Validar SGIND/IQOS com acompanhamento no computador autorizado.

### Entrega 5 — operação cotidiana

Ampliar diagnóstico de falhas, perda/reinício de workers, cancelamento, filas e instalação Windows reproduzível. Retomada depende de regras explícitas de repetibilidade.

## 9. Critério da primeira entrega funcional

Gravar uma tarefa com consulta e resultado; reproduzi-la com parâmetros diferentes; tolerar mudanças na posição dos elementos e demora na geração; identificar e baixar o arquivo novo correto; reconhecer erro ou ausência de resultados sem apresentar sucesso indevido.

Cenários necessários:

- Formulário com e sem datas.
- Inserção de elementos antes do alvo e alteração de layout.
- SPA com carregador e resultado atualizado após atraso.
- Botão inicialmente desabilitado.
- Central contendo arquivos antigos, geração tardia e correspondências ambíguas.
- Frames e abas suportados, recarregamento e conclusão da gravação.
- Cancelamento durante espera e ausência de dados.
- Canários sintéticos ausentes da receita, dos eventos e dos artefatos de gravação.

Evidência sintética comprova esses cenários; compatibilidade corporativa exige validação própria.

## 10. Regras preservadas

- Operação essencial local no Windows e infraestrutura de custo zero.
- Valores da demonstração não viram defaults da receita.
- Credenciais, cookies e tokens não entram em receitas, banco, logs ou gravação.
- Segredos são fornecidos na execução e permanecem efêmeros.
- Condições automáticas devem ter origem identificável e ser revisáveis.
- Falta de certeza sobre alvo ou resultado deve gerar pendência ou diagnóstico.
- Replay automático de ação com efeito depende de regra explícita de repetibilidade.
- Os gates corporativos só evoluem mediante evidência correspondente.

## 11. Estado da decisão e próximo passo

O usuário escolheu o método B e confirmou a direção de inteligência local do gravador. As frentes acima orientam a continuação, mas ainda não constituem uma especificação técnica completa nem um plano de implementação executado.

Próximo bloco: detalhar a Entrega 2, começando pelo contrato de alvos e observações, compatibilidade das receitas existentes e critérios de confirmação de resultados. A prioridade específica entre relatórios e outras tarefas continua a ser refinada; o motor deve permanecer genérico.

## Referências

Consultar os arquivos abaixo **na branch de referência**, pois o checkout local contém uma versão anterior:

- `HANDOFF.md`
- `CONTINUAR_NEXER_2026-10-13.md`
- `docs/development/CURRENT_STATE.md`
- `docs/development/ROADMAP.md`
- `docs/development/DECISIONS.md`
- `docs/2026-10-13-smart-recorder.md`
- `apps/recorder/README.md`
- `docs/superpowers/specs/2026-10-12-nexer-reusable-flows-design.md`
- `docs/superpowers/plans/2026-10-13-recording-fields-downloads.md`
