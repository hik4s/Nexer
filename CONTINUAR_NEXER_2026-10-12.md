# Continuar Nexer — 2026-10-12

## Solicitações do usuário

- Continuar Nexer; aceitou priorizar importação e edição dos campos no Studio sem JSON.
- Ampliou direção: aplicativo escalável para uso pessoal/profissional, pilares automações, cadastrar login em URL fornecida e identificar campos no Edge, gravar/reutilizar scripts, inserir credenciais somente na execução.
- Confirmou selecionar vários fluxos e iniciar lote, com progresso/cancelamento separados por fluxo.

## Entrega implementada nesta rodada

- Studio importa arquivo JSON v1 local até 1 MB, com FileReader, estrutura inicial mínima e erro constante sem conteúdo do arquivo. Arquivo inválido preserva receita anterior; importação não salva/publica automaticamente.
- Editor de nomes amigáveis em variables.<id>.label, até100 caracteres. Mantém identificadores/placeholders, tipos/regras e exclui variáveis secretas da edição visual. Labels são metadados de apresentação; nenhum default/dado de preenchimento é criado.
- RecipeField e datas de período exibem labels. Runtime valida label string <=100; backend usa validação compartilhada ao validar/publicar.
- Selecionar automação com versão publicada carrega GET da receita correta; antes deixava receita default de outra automação. Respostas antigas descartadas por editorRevision. Mudanças/importação invalidam versão do editor e impedem validar/publicar até salvar nova versão.
- Mutação de save verifica revision antes de aplicar resposta. Troca de seleção durante mutation impedida; respostas de carregamento e importação anteriores não sobrescrevem edição mais nova. Mensagem de rascunho corrigida para não confundir com ausência de publicação.
- Formatação do card de nova automação/editor de campos/botões ajustada. Editor JSON avançado permanece recolhido e disponível.

## Alinhamento de produto e arquitetura

- README diferencia novo núcleo genérico do legado corporativo Streamlit; ROADMAP, CURRENT_STATE e DECISIONS atualizados, removendo estados antigos que negavam frontend/runtime já existentes.
- Desenho: docs/superpowers/specs/2026-10-12-nexer-reusable-flows-design.md.
- Dois planos separados: docs/superpowers/plans/2026-10-12-login-profiles.md e 2026-10-12-batches-parallelism.md. São propostas de implementação ainda não executadas; o usuário confirmou intenção e lote, mas não revisou estes arquivos técnicos ainda.
- Login: perfil/version com URL/alvos/origens/regra de sucesso, modo específico de selecionar campos sem digitar senha ou submeter, botão Cadastrar login, envelope efêmero independente de inputs. Não remover bloqueio de senhas do gravador normal.
- Lote: ExecutionBatch agrupando Execution independente por fluxo, validação/commit/binding atômicos e idempotência. Slots propostos 2, configuráveis1..4; cada processo com Playwright/DB/capability/workspace próprio. Loop atual é serial; concurrency_limit não significa execução simultânea. worker_channel atualmente configura worker único e deve ser generalizado antes de paralelismo.
- Cadastro de login, identificação de seus campos no Edge, login genérico e lote/paralelismo NÃO implementados nesta rodada. Manter esta distinção em toda comunicação.
- Regra de sucesso explícita; não considerar somente sumiço de password como login bem-sucedido. MFA/CAPTCHA/SSO exigem adaptação/intervenção; não evadir.
- SGIND/IQOS permanecem com gates fechados até outro computador corporativo. Nenhum acesso/login real nesta rodada.

## Verificação

- TDD RED: selecionar publicada não carregava receita; botão/import inexistente; label inválida passava no runtime. Implementação GREEN.
- Frontend suite29 testes/12 arquivos OK; testes direcionados finais9 OK; build final OK. Runtime102 OK/9 skips; backend versões5 OK. Não rerodar todos corporate/launcher E2E como se fossem testes desta entrega.
- Review somente leitura pela skill requesting-code-review: nenhum achado concreto; reviewer repetiu frontend9+runtime1 OK. Docs distinguiram implementação atual e futura.
- Visualização do build em Edge headless com APIs mockadas/arquivo fictício: temp/studio-import-desktop-2026-10-12.png e temp/studio-import-mobile-2026-10-12.png; inspect desktop/mobile sem overflow horizontal.
- pip check/git diff --check OK. Patch portátil deve incluir rodadas 2026-10-10 e esta, em temp/NEXER_PATCH_2026-10-12.patch, com reverse apply check.

## Retomada

Rever desenho dos dois módulos maiores com usuário e seguir planos em entregas pequenas, sem presumir que login/capabilities multiworker já funcionam. Preservar todos os diffs locais acumulados, sem sobrescrever legado. Não há commit/push nesta rodada. Handoff anterior CONTINUAR_NEXER_2026-10-10.md mantém os detalhes do gravador/cancelamento/launcher já implementados.
