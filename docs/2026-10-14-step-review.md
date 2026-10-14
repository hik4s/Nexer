# Revisão e reparo pontual de etapas — 14/10/2026

Direção escolhida pelo usuário: “Revisar e corrigir etapas sem regravar tudo”. A autorização de execução completa da sessão foi mantida. Esta entrega amplia a revisão existente do cadastro guiado, sem criar um contrato de runtime, endpoint ou migração.

## Como usar

Depois de gravar ou importar uma receita, avance até Campos. A seção “Etapas do fluxo” mostra a ordem, o tipo da ação, o nome do parâmetro quando houver e o contexto de aba/frame. Abra uma etapa para editar o seletor do alvo. Em arrastar, também é possível corrigir o destino. Aplique ou descarte a correção antes de avançar ou voltar no assistente.

A correção conserva ID, ação, ordem, parâmetros, valores de referência, frames e configurações que não pertencem ao alvo. Downloads em central continuam em seu editor específico. Navegação, troca/fechamento de abas, snapshots e verificações de arquivo aparecem para conferência, sem edição genérica.

Se houver uma espera automática imediatamente anterior para o mesmo seletor e os mesmos frames, ela pode acompanhar a correção. Essa opção é explícita e inicia marcada. Ao atualizar o alvo, a espera passa a ser uma condição revisada manualmente. Esperas manuais, de outro alvo/frame ou não adjacentes permanecem intactas. Aplicar um seletor inalterado não modifica a origem da espera.

É possível corrigir o alvo de uma consulta e voltar à configuração original de clique sem perder esse reparo. Os campos técnicos de confirmação/resultado continuam nos editores especializados.

## Proteção das edições e importação

- Rascunhos de cada etapa usam o ID estável, de modo que remover uma sugestão anterior não remonta os editores seguintes.
- Uma sincronização de espera não sobrescreve um rascunho pendente naquele editor. O usuário ainda escolhe aplicar sua correção ou descartá-la em favor da configuração mais recente.
- Edições de etapas, consultas e downloads têm controle independente de pendências; salvar uma não libera as outras.
- IDs ausentes, numéricos, vazios ou duplicados e entradas nulas são rejeitados na importação antes de entrar na revisão. Uma importação inválida não substitui a receita anterior.
- A lista não exibe valores literais de ações, credenciais, conteúdo do site ou dados de uma execução. Usa somente tipo, identificador e metadados declarativos do parâmetro/contexto.

## Implementação

`apps/frontend/src/lib/stepReview.ts` descreve a sequência, valida identidades e aplica reparos sobre cópia da receita. `StepReviewEditor.tsx` mantém rascunhos locais por ID. `NewFlowPage.tsx` integra a revisão e as pendências; `QueryOutcomeEditor.tsx` conserva o seletor reparado ao restaurar um clique. Estilos seguem o editor e a navegação existentes.

## Verificação

Testes novos foram executados inicialmente em RED e depois GREEN, incluindo helper, componente e publicação pelo assistente. A revisão independente encontrou três problemas importantes: perda de rascunho por chave posicional, sobrescrita de espera pendente e importação com IDs inválidos. Os três foram reproduzidos por regressões antes da correção. Nenhum achado foi adiado.

Após as correções: **101 testes frontend passaram em 28 arquivos, sem falhas ou skips** (exit 0). `tsc -b` e build Vite passaram. Foram verificados helper, componente, importação, pendências entre editores, navegação no assistente e receita enviada à publicação.

QA do app compilado em Edge, API simulada, 1280×1000 e 390×844: sem overflow horizontal nem erro de página, controles legíveis, pendências bloqueando ida/volta. A correção feita pela interface foi coletada na requisição simulada de publicação e executada com o runtime real em uma página sintética. A receita original falhou na espera pelo alvo antigo; a corrigida concluiu as quatro etapas, preencheu o campo novo e acionou o botão. O canário digitado somente na execução não apareceu na receita publicada nem nos eventos.

A entrega alterou apenas frontend; as suítes backend/worker/recorder não foram repetidas. A execução Edge acima verificou a aceitação e o replay da receita editada pelo runtime existente. Logs, script e screenshots inspecionadas estão em `temp/step-review/` (ignorado pelo Git).

## Limites

O reparo inicial usa seletores informados pelo usuário; não inclui selecionar um elemento visualmente em um navegador conectado. A aplicação da edição verifica estrutura, tamanho e referências de variáveis, mas não comprova unicidade do elemento ou sucesso de negócio. Essas condições continuam sendo verificadas na execução.

Frames e ordem permanecem definidos pela gravação/receita. Mudar tipo de ação, reordenar, reparar frame ou configurar coleções/consultas completas usa as ferramentas específicas ou o Studio. O rascunho da revisão é de sessão; esta entrega não acrescenta persistência após fechar/recarregar a página nem recuperação de gravação interrompida.

Nenhum banco real, serviço ou executável foi alterado. A validação real de SGIND/IQOS continua pendente; os fixtures não a substituem. O worktree atualizado permanece em `C:/Users/hikas/.codex/worktrees/smart-recorder-foundation/Nexer`, na branch `codex/smart-recorder-handoff-2026-10-14`.
