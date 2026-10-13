# Nexer — estado atual em 2026-10-13

Fonte de retomada do novo núcleo; o legado permanece preservado. Branch `feat/etapa1-foundation`, sem merge ou encerramento formal da Etapa 1.

## Direção confirmada pelo usuário

Aplicativo local Windows para automações pessoais e profissionais. Pilares: biblioteca de automações, cadastro de perfis de login e gravação parametrizada de fluxos. Vários fluxos serão iniciados por lote, com acompanhamento/cancelamento separados. Perfis devem armazenar configuração dos campos e receber credenciais somente ao executar. SGIND/IQOS permanecem como especializações.

Desenho e critérios: [fluxos reutilizáveis](../superpowers/specs/2026-10-12-nexer-reusable-flows-design.md). Planos: [perfis de login](../superpowers/plans/2026-10-12-login-profiles.md) e [lotes/paralelismo](../superpowers/plans/2026-10-12-batches-parallelism.md).

## Implementado

- React/TypeScript/Vite → FastAPI → SQLite/Alembic + SSE → Worker → runtime Playwright/Edge.
- Automações e versões com validação/publicação; execuções, inputs, status, cancelamento e eventos.
- Cofre/canal efêmero de credenciais, vinculado à sessão/execução/worker, com revogação e gates corporativos fechados.
- Contexto de navegador monitorado, restrições corporativas, shutdown do worker por EOF e cleanup de árvore própria Windows.
- Gravador em HTTP loopback: ações DOM, campos parametrizados sem valores da gravação, frames/abas e downloads identificados.
- Dashboard Relatórios registrados com formulário de tipos/regras HTML, consulta efêmera de opções locais e invalidação de dependências.
- Studio nesta rodada: importar gravação JSON, configurar nomes amigáveis, manter placeholders/tipos/regras, carregar receita publicada selecionada e impedir validar/publicar edição não salva.
- Logins de sites: perfil versionado, seleção separada de usuário/senha/botão no Edge, regra explícita de sucesso e desativação. Cadastro não recebe credenciais.
- Execução por perfil: snapshot imutável, credenciais efêmeras por sessão/execução/worker, contexto monitorado e consulta de opções autenticada sem persistir sessão.
- Lotes: transação e idempotência, parâmetros separados por fluxo, preparação no dashboard, acompanhamento SSE e cancelamento individual ou do lote.
- Supervisor: dois processos de worker por padrão, opção --workers entre1 e4; capabilities distintas por stdin, revogação individual. Loop serial dentro de cada processo.
- Identidade Percurso aplicada do nexer-logo-kit: logo original, favicon, navegação lateral responsiva, grafite/branco/fundo suave, busca e cartões selecionáveis, foco visível e suporte a movimento reduzido.
- Workspace prático: grupos de acesso (ex.Energisa), destinos com seletores reutilizáveis, rotinas favoritas no SQLite, campos comuns compatíveis/override, datas rápidas, resumo explícito e repetição de execução/lote com credenciais novas.
- Cadastro guiado em5 passos: site, acesso, gravação/importação, nomes de campos e publicar. Recorder privado acessível pela UI para páginas HTTP locais, com concluir/cancelar e resultado parametrizado; não guarda valores digitados.
- Navegação cotidiana Meus fluxos/Acessos/Execuções; Studio, catálogo técnico, destinos e diagnóstico em ferramentas secundárias. Histórico oferece execuções individuais e lotes.

## Limites reais

- Cada worker continua serial; paralelismo acontece entre processos. Teste real de dois processos/Edge comprovou sobreposição, contas e arquivos separados e cancelamento individual.
- Perfis genéricos não equivalem a suporte automático a qualquer site. MFA/CAPTCHA, login em etapas, popups autenticados e controles customizados exigem adaptação.
- Seleção de campos de login é modo separado do gravador normal; proteção password do gravador existente permanece.
- Credenciais nunca devem entrar em execution.inputs, receita, cache React Query ou arquivos.
- Gravador comum permanece restrito a loopback; perfis aceitam HTTPS e HTTP loopback com origens explícitas. Sites reais e catálogos corporativos precisam de validação autorizada.
- Componentes especiais, navegação para listas em outra página/aba, máscaras só em JS e carregamentos permanentes exigem adaptação.

## Evidência

Gravação agora abre revisão somente após finalizar, aproveita nomes estruturais dos campos e tem botão Parar gravação na página. Central de downloads aceita padrão na execução, seleciona primeira correspondência na ordem da lista e preserva nome atual do site, sem gravar nomes/valores da sessão de captura. Seletores podem exigir revisão. Validação mais recente: frontend50, recorder19 Edge, runtime109, backend112; detalhes no arquivo de continuidade.

Consultar CONTINUAR_NEXER_2026-10-13.md para evidência atual, limites e retomada. Migrações0004–0006 verificadas em bancos temporários. Não afirmar validação corporativa, distribuição final ou compatibilidade universal.

## Próximas entregas

1. Acompanhar a interface com o usuário e incorporar ajustes visuais sobre a identidade do kit.
2. Validar fluxos de sites reais fornecidos pelo usuário, adaptando controles/login específicos.
3. Ampliar o gravador comum para sites autorizados HTTPS com política de origens; integração gráfica local já implementada.
4. Expandir cenários de perda/reinício de processo e filas longas no supervisor multiworker.
5. Validar SGIND/IQOS no outro computador; conservar gates até evidência.
