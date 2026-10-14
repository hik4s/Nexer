# Downloads vinculados à solicitação

Entrega de 14/10/2026, seguindo o método B: inteligência local e contrato genérico com adaptadores específicos quando necessários. Sem API de IA ou modelo local obrigatório.

## O que foi implementado

A receita agora pode registrar a central antes de gerar, emitir a solicitação uma única vez, aguardar sua confirmação e baixar somente o resultado identificado por essa confirmação. Duas execuções podem aguardar a mesma central e terminar fora de ordem, inclusive com arquivos de mesmo nome quando existe um identificador de trabalho.

- `snapshot_downloads`: registra em memória até 1000 identidades de uma central materializada, com raiz `collection.container` única e existente. Central vazia é válida; central ausente ou leitura incompleta interrompe antes de gerar.
- `request_download`: vincula a baseline, faz um clique esquerdo simples e aguarda confirmação única, visível e diferente da anterior. Confirmação anterior oculta também é considerada para impedir aceitação de trabalho antigo. Não há retry de geração.
- `download.generation`: referência à solicitação; exige a mesma coleção, frames e aba. Só seleciona identidade confirmada, ausente da baseline, com nome correspondente ao padrão. Ambiguidade interrompe sem baixar.
- O clique final verifica a identidade e o botão no mesmo bloco DOM, suportando reordenação e reconstrução frequente das linhas. Cancelamento e autorização são verificados durante prontidão, confirmação, seleção e espera pelo evento de download.
- Snapshot e identificador ficam fora de inputs, variáveis comuns, eventos, checkpoints e banco; são apagados antes e depois da execução, inclusive em falha/cancelamento.

Confirmação: texto com nome completo do arquivo ou atributo `data-job-id`, `data-report-id`, `data-download-id`. Com atributo na linha, a identidade precisa corresponder ao identificador confirmado. Identificadores aceitos têm até 256 caracteres ASCII: letras, números, ponto, hífen e sublinhado.

Na revisão do fluxo, **Vincular download à solicitação** permite selecionar a ação de geração, a raiz da central, a confirmação, a identidade na linha, a indicação de central compartilhada e o prazo por etapa (1–15 minutos, padrão 3). Alterações pendentes bloqueiam avanço até aplicar. Editar seletores mantém a baseline consistente; remover vínculo compartilhado por outro download é recusado.

Centrais declaradas `shared: true` exigem correlação para validar/publicar. Receitas antigas permanecem compatíveis; sua seleção pelo primeiro nome correspondente não comprova propriedade em uma central compartilhada. O histórico apresenta mensagens fixas para códigos conhecidos; exceções desconhecidas continuam mascaradas pelo worker.

## Verificação

- Runtime: 132 testes, 122 passaram e 10 opt-ins não habilitados foram pulados. Inclui 19 testes de contrato/Edge desta entrega, todos passaram.
- Gravador: 54 testes passaram, incluindo Edge sintético.
- Worker: 34 testes, 33 passaram e 1 opt-in foi pulado.
- Backend de gravação, versões e lotes: 14 testes, 13 passaram e 1 opt-in foi pulado.
- Frontend: suíte completa final com 77 testes passou. Após conferir a integração dos diagnósticos no histórico, os 2 testes dessa página passaram; o cenário novo reproduziu RED antes da correção. TypeScript (`tsc -b`) e build Vite passaram após a alteração final.
- Revisão independente identificou confirmação antiga oculta, geração após cancelamento e espera DOM sem limite. Regressões reproduziram as duas primeiras; os três achados foram corrigidos e a segunda revisão confirmou 19 testes e ausência de novos achados relevantes.
- Interface inspecionada em 1280 px e 390 px com API simulada, sem acesso a serviços reais.

O teste de concorrência usa servidor HTTP sintético, duas instâncias/contextos independentes do Edge, uma central única reconstruída a cada 50 ms e arquivos com o mesmo nome. B fica disponível primeiro; os bytes finais comprovam que A recebeu A e B recebeu B.

## Limites e próximos passos

O SGIND real ainda não tem adaptador de correlação validado. O formato `TodasOcorrencias-XXXXX.csv` informa tipo e nome, mas sozinho não identifica a solicitação. É necessário observar onde o portal fornece o nome completo/protocolo/identificador para a execução que gerou o relatório. Esse sinal não foi presumido.

O contrato genérico cobre coleções CSS DOM materializadas e links/botões HTML. Shadow DOM, paginação, virtualização ou controles que exigem eventos nativos confiáveis precisam de adaptador específico que comprove a abrangência e a correlação. O prazo termina no evento de download; salvar o arquivo mantém o transporte e as proteções existentes. Reinício do processo perde o vínculo e não retoma/reenvia geração automaticamente.

Próxima etapa de inteligência: contrato **consulta → resultado, erro ou ausência de dados**, com condições verificáveis e histórico claro. Em paralelo, obter evidência estrutural autorizada do SGIND para seu adaptador.

Código está no worktree `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`, branch `codex/smart-recorder-foundation`. Diffs da entrega anterior foram preservados. Não houve commit, push, merge, migração do banco existente ou execução corporativa.
