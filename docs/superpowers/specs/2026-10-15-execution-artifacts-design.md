# Arquivos validados no histórico

O usuário autorizou continuar a trilha RPA sem interrupções para aprovação. Objetivo deste incremento: disponibilizar na UI o arquivo que o runtime validou, associado à execução correta. Não homologar conteúdo de negócio nem SGIND com base neste contrato.

Reusar `Artifact`, `ExecutionContext.artifacts` e `validate_file`. O worker registra somente entradas `validated_file`, deduplicadas por caminho, após sucesso do runner e antes de concluir o item. Cada entrada deve estar na pasta `<downloads_root>/<execution>/<item>` sem links simbólicos/junctions, ser arquivo regular, manter tamanho/checksum observados e receber SHA-256. Downloads que a receita realizou precisam de validação correspondente; não alterar o contrato de receitas sem download nem de dry-run.

A API autenticada expõe lista por execução e download por ID dentro da mesma execução, sem caminhos locais ou de rede nas respostas. Somente itens concluídos têm arquivos disponíveis. Derivar o caminho de IDs e nome seguro, conferir confinamento, tamanho e checksum e transmitir pelo mesmo handle aberto usado na conferência. Usar attachment, octet-stream, no-store e nosniff. Nenhum caminho fornecido pelo cliente. O armazenamento é local para um operador; sessão local não implica isolamento multiusuário empresarial.

A UI mostra arquivos apenas na execução selecionada, atualização ao terminar e erros sem detalhes internos. Não tornar receita vazia em prova de arquivo; não tratar validação por extensão/tamanho como validação de CSV de negócio. E2E sintético com Edge e bytes distintos comprova isolamento básico, não acesso corporativo.

Limites: processos locais com permissão de escrita podem alterar arquivos durante leitura; isto não é uma fronteira contra administrador local malicioso. Arquivos e histórico continuam sob a política existente de exclusão; não apagar arquivos automaticamente. Nenhuma migration ou dependência nova.
