# Seleção visual para reparo de alvo

Continuação da direção escolhida pelo usuário: corrigir etapas sem regravar tudo. Autorização ampla de execução mantida. Base `f1994d5`; worktree/branch de entrega existentes.

## Escopo e experiência

Um botão no editor de alvo abre uma sessão nova e efêmera do Edge no endereço inicial configurado. O usuário prepara manualmente a página da etapa, ativa “Selecionar alvo” e escolhe um elemento. O resultado preenche o rascunho do editor, sem aplicar automaticamente a receita. Aplicar/descartar e sincronização opcional da espera permanecem existentes.

Primeira versão: alvos na página principal, controles de texto, select nativo, checkbox, range/color e elementos de clique/espera/hover/scroll/press/drag (origem ou destino). Controles customizados choose/choose_radio e frames conservam edição manual. Abas/frames da receita não são alterados. Uma janela nova serve somente à aquisição do seletor; o fluxo não é reproduzido automaticamente.

## Arquitetura

Reutilizar lifecycle de sessões privadas do backend (owner, TTL300s, capacidade2/32, cancelamento e reap do subprocesso), com um hook de validação de configuração; comportamento de login/gravação permanece igual. Serviço específico recebe somente URL inicial normalizada e tipo de controle, retorna `{selector}` após validar gramática estrutural permitida. Endpoint local autenticado POST/GET/cancel, respostas no-store, sem banco.

Subprocesso `pick_target.py` usa navegador/contexto próprios, sem perfil persistente ou downloads. Política de origem igual ao gravador: somente origem configurada, redirects e websockets bloqueados, service workers/Worker desabilitados. Preparação permite navegação manual nessa origem; seleção bloqueia métodos diferentes de GET/HEAD. HTTPS/login/SSO não recebem novos gates ou permissões de rede.

Bundle inclui `selectors.js` existente e captura específica, instalada antes do JS da página. Interceptar eventos de ponteiro/mouse/teclado/submit em window capture durante seleção, antes dos handlers usuais. Toolbar também intercepta seus próprios eventos. Seleção aceita apenas clique confiável; a escolha não é um replay do fluxo. Não prometer proteção contra scripts hostis, requisições autônomas ou endpoints com efeitos em GET.

IDs/textos arbitrários, valores, URLs finais, HTML, screenshots e credenciais não são coletados. Seletores usam a política restrita já existente; Python e backend verificam a gramática/atributos permitidos antes de entregar metadados à UI. A origem/frame e unicidade são verificados no documento real. Rejeitar alvo de password, contexto diferente, iframe e canvas; não adivinhar o alvo.

## Estado e concorrência

PREPARING → SELECTING → DONE/FAILED/CANCELLED. Reentrar PREPARING permite ajustar a página. Ativação somente na página principal/origem correta e sem password visível. Documento fixado durante seleção; troca de documento cancela. Binding enfileira pedido; verificações Playwright ocorrem fora do callback. Limite de um pedido pendente evita filas ilimitadas.

Frontend faz polling cancelável por sessão. A seleção preenche somente o rascunho iniciado; edição posterior, descarte, fechamento, receita substituída ou resposta de uma sessão anterior invalidam seu resultado. Cancelar explicitamente também limpa/ignora o resultado antes de aguardar a rede. Falhas usam mensagens fixas e preservam o rascunho manual. Seleção em andamento bloqueia navegação até ser cancelada ou concluída. Remover uma etapa/unmount cancela sua sessão; retorno tardio é cancelado e nunca altera outra etapa.

## Aceitação

Testes RED/GREEN para configuração/gramática, owner/TTL/capacidade e protocolo sanitizado, interação Edge (seleção não aciona handlers usuais, não envia formulário, alvos privados não entram nos metadados, shadow aberto, rejeição de frame/controle errado), endpoints autenticados/no-store, UI (apenas rascunho, escolha antiga versus nova, editar/descartar/cancelar/unmount e preparação). Testes de regressão de login/gravação e editor existentes. Suítes pertinentes completas, TypeScript/build e QA desktop/mobile; registrar skips e limites separadamente.
