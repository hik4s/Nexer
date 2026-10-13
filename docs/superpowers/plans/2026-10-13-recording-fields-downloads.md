# Gravação, nomes de campos e central de downloads

Pedido: abrir o site ao gravar, capturar ações e campos efetivamente editados, apresentar os campos somente ao finalizar, obter nomes dos rótulos da página e não persistir valores da gravação. Parar pelo botão na página aberta. Baixar o primeiro relatório correspondente a um padrão configurável, pois os nomes mudam entre execuções.

Autorização existente: continuar implementando as alterações sem pedir permissões intermediárias. A pergunta sobre os nomes foi respondida: usar padrão configurável.

- [x] Rótulos estruturais por label/aria-labelledby/aria-label/legend, snapshots antes da edição; somente controles editados geram parâmetros.
- [x] Toolbar excluída da captura, binding privado de conclusão, fechamento do contexto próprio e transição para revisão dos campos.
- [x] Coleção estrutural para downloads em tabelas/listas/roles; padrão glob solicitado na nova execução, sem copiar nomes de arquivos gravados.
- [x] Runtime seleciona primeiro item visível correspondente na ordem do DOM, aguarda disponibilidade, suporta cancelamento, falha sem correspondência e preserva o nome atual recebido do site.
- [x] Revisão independente: corrigido texto do botão contaminando nome em listas, reproduzido RED→GREEN no Edge.

Limites: ordem do DOM deve representar a ordem de cima para baixo da central. Seletores de nome/linhas/botão podem ser revisados após gravação; centrais com estruturas particulares exigem configuração no Studio. Cliques de download precisam ser identificáveis; eventos espontâneos não são inferidos. HTTP local continua sendo o escopo autorizado e validado do gravador, sem alteração nos gates corporativos. A prévia visual não executa gravações reais.
