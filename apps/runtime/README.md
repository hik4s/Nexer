# Nexer Runtime

Interpretador declarativo das receitas do Nexer.

Escopo inicial da Etapa 1:
- schema de receita v1;
- resolução segura de variáveis;
- ActionRegistry;
- ações navigate/click/fill/select/press/wait_for/wait_for_any/switch_tab/download/validate_file;
- execução ordenada com eventos e checkpoints;
- dry run.

O Runtime não deve importar módulos específicos de relatórios. Relatórios são representados por receitas.

## Downloads correlacionados

O runtime suporta `snapshot_downloads` imediatamente antes de `request_download`, seguido de `download` com referência `generation`. Uma central declarada `shared: true` exige esse vínculo. Confirmação nova identifica o resultado; padrão e novidade da linha sozinhos não comprovam propriedade.

Consulte [contrato, configuração, verificação e limites](../../docs/2026-10-14-downloads-correlacionados.md). O estado de correlação é efêmero, limitado e limpo em `RecipeRunner.run`; não é mecanismo de retomada após restart.
