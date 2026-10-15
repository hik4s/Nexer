# Continuar o Nexer — 15/10/2026

## Fonte de verdade

- Repositório: `https://github.com/hik4s/Nexer.git`.
- Branch desta entrega: `codex/nexer-stability-artifacts-2026-10-15`.
- Commit da implementação: `6df14cd`.
- Base: `b414fbe`, da branch `feat/nexer-portable-bootstrap-2026-10-14`.
- Checkout atualizado: `C:/Users/hikas/.codex/worktrees/nexer-distribution-audit/Nexer`.
- O checkout `C:/Users/hikas/Documents/ChatGPT/Nexer` está em outra branch e contém documentos pendentes preservados. Não sobrescrevê-lo nem iniciar seus serviços supondo que executa esta entrega.

O usuário autorizou continuidade autônoma e, depois, pediu explicitamente criar este Markdown e fazer push. A publicação Git não representa instalação, implantação ou homologação corporativa.

## O que foi entregue

1. Instalador alinhado ao código de pareamento, sem solicitar usuário/senha legados. `SkipAuthSetup` permanece como alias obsoleto de `NoLaunch`.
2. Fechar uma etapa cancela o picker sem perder o rascunho; respostas tardias são invalidadas.
3. Worker registra arquivos validados e sucesso do item na mesma transação. Download sem validação posterior não conclui com sucesso.
4. `validate_file` calcula SHA-256 sempre. Mudança de bytes com mesmo tamanho e download posterior à validação são detectados.
5. API autenticada lista e entrega arquivos da execução, sem expor caminhos locais. Arquivos alterados, de outra execução, hardlinks, symlinks e junctions são recusados.
6. Histórico oferece download dos arquivos. API e worker compartilham configuração de diretório, inclusive via `.env`.

## Evidências e limites

Registro completo: [estabilidade e arquivos](docs/2026-10-15-stability-artifacts.md). Auditoria inicial: [distribuição](docs/2026-10-15-retomada-auditoria-distribuicao.md).

Na verificação da implementação, **537 testes passaram e 24 foram pulados**; TypeScript/Vite compilaram. A revisão independente encontrou duas falhas de configuração/caminho, corrigidas com RED/GREEN; uma fixture adicional também foi corrigida. As contagens são evidência dessa rodada, não promessa sobre alterações futuras.

O E2E sintético grava no Edge, parametriza duas execuções, executa via API/worker/runtime reais e baixa pela interface React os CSVs distintos esperados. A fixture prepara o cadastro inicial e a sessão; não comprova publicação pelo wizard, worker em subprocesso, concorrência ou conteúdo de negócio. Nenhum login ou relatório corporativo real foi executado.

## Próxima implementação prioritária

**Configuração guiada de validação de downloads.** O gravador/wizard ainda não acrescenta `validate_file` automaticamente. Hoje a revisão deve incluir essa etapa no Studio; caso contrário o worker falha com `ARTIFACT_NOT_VALIDATED`. Resolver a seleção do arquivo quando o site preserva seu próprio nome, sem inferir autoria por padrão de nome ou relaxar correlação.

Depois: validação estrutural de CSV/HTML disfarçado, contrato de artefato obrigatório para `output: file`, pacote sem binário legado, separação completa dos adaptadores corporativos, clean-install Windows e empacotamento autossuficiente. A exposição do banco no histórico continua pendente; não reescrever história incidentalmente.

## Retomada segura

1. Conferir branch, status, remoto e commit antes de editar; ler instruções aplicáveis.
2. Ler este documento e o registro completo de evidências antes dos handoffs históricos.
3. Reusar contratos de consulta/download existentes. Preservar credenciais efêmeras, fail-closed e custo essencial sem IA paga.
4. Usar banco, portas e diretórios temporários para testes; não iniciar workers sobre fila desconhecida nem encerrar processos genéricos.
5. Atualizar evidências e Git ao concluir cada incremento. Não confundir push com release, merge ou implantação.
