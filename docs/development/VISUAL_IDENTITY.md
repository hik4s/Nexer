# Nexer — integração da identidade Percurso

Pedido: aplicar o nexer-logo-kit existente, melhorar beleza e interação mantendo minimalismo. Público: automações pessoais e profissionais; o dashboard prioriza receitas reutilizáveis, perfis de login e execução por lote.

## Aplicação

Logo horizontal original no workspace e na entrada, faviconSVG/ICO e apple-touch-icon do kit. Arquivos copiados para apps/frontend/public; originais do kit preservados. Assinatura160px ou maior, proporções preservadas, sem alterar caminhos. Símbolo branco original como elemento de fundo do dashboard.

Paleta: grafite#171719, branco#FFFFFF, fundo#F5F5F7. Cores semânticas de status permanecem pontuais. Tipografia do logo em paths; textos da interface usam fontes do sistema, sem downloads externos.

Navegação lateral em desktop e faixa rolável no celular. Cartões de fluxo com seleção de lote independente da busca; limpar busca preserva seleção. Atalhos para Studio, logins e acompanhamento. Formulários, upload, botões, foco, seleção e estados desabilitados seguem o mesmo sistema.

A simplificação posterior concentra a navegação em Meus fluxos/Acessos/Execuções, com ferramentas secundárias recolhidas. Dashboard inclui favoritos; wizard orienta5 passos; preparação usa campos compatíveis comuns com personalização explícita por fluxo e resumo antes de iniciar. Campos que herdam valores comuns ficam bloqueados até marcar personalização, evitando edições acidentais.

Hover discreto e transições160ms; prefers-reduced-motion elimina animações. Bordas suaves e hierarquia tipográfica evitam ornamentação excessiva. Nenhuma métrica demonstrativa é adicionada à interface de produção.

## Prévia local

temp/preview_identity.py serve o build em127.0.0.1:4173 com dados sintéticos e indicação de prévia. Reescreve somente a resposta JS em memória para apontar ao servidor demonstrativo; não altera o build nem consulta a API de produção. GETs alimentam a navegação; POSTs retornam VISUAL_PREVIEW_ONLY e não criam execuções. Processo de prévia iniciado nesta sessão com janela oculta; não é serviço de produção.

temp/check_identity_visual.py verifica logo, busca, seleção e preparação de lote em Edge headless, capturando desktop1440px e celular390px. Verificação de overflow e erros de navegador; screenshots emtemp/identity-*.png. A página de entrada e demais páginas compartilham tokens do sistema.

temp/check_practical_visual.py verifica favoritos, datas/empresa comuns, resumo, wizard e grupos de acesso; screenshots temp/practical-*.png. O servidor da prévia foi reiniciado para carregar os novos endpoints demonstrativos; consulta de opções retorna dados sintéticos, e POSTs de mutação continuam bloqueados. Listas comuns exibem somente a interseção válida entre destinos e o resumo usa os nomes das opções.
