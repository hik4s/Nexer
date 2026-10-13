# Atualização — fluxos HTTPS, novo token e exclusão — 2026-10-13

Esta atualização prevalece sobre os limites anteriores de gravação HTTP local. Workspace atual: `C:\Users\kis\Downloads\Nexer-codex-nexer-reusable-flows-2026-10-13`, cópia sem `.git`; sem commits/push nesta máquina. Usuário pediu explicitamente implementar os três recursos.

## Entregue

- URL HTTPS e rotas de aplicação `#/caminho` preservadas, incluindo `https://indicadoresenergisaess.scl.corp/sgind/#/relatatendtodasocorrencias`. Validação compartilhada no backend/runtime, perfil de login/sucesso e UI. Credenciais, query, fragmentos com dados e HTTP externo continuam recusados. Origem de perfil não contém rota/fragmento.
- Gravação HTTPS abre Edge limpo em PREPARING. Usuário entra no site manualmente, abre a rota configurada na página original e usa **Iniciar gravação**. Preparação não captura eventos, rótulos, timers, drag ou login; início recusa senha visível (inclusive frames), rota diferente ou abas extras da preparação. Fechar essas abas e iniciar recria índices de tabs para replay. Depois, **Parar gravação** conclui; UI só permite Concluir após confirmação privada de started.
- Política mantém somente origem inicial, bloqueia redirects/origens externas, workers/WebSockets e salvamento de downloads/sessão do navegador. Contexto/processo próprio encerra em cancelamento/EOF; nenhuma receita vazia ou de preparação é publicada. HTTP loopback mantém gravação imediata. Não prometer SSO em outras origens, redirects ou qualquer site.
- **Gerar novo token** na tela local: POST /auth/pairing-code gera no console, retorna só metadados/no-store, limita renovação a cada5s. Código anterior invalidado, novo5min/uso único, sessões existentes preservadas. Não há autenticação automática ou token retornado pelo HTTP.
- **Excluir perfil** em Acessos pede confirmação; DELETE /login-profiles/{id}/permanent remove perfil e versões não referenciadas em transação, preserva grupos/snapshots/histórico e legado Desativar. Seleção ativa ou versão salva de receita vinculada recusa exclusão com explicação. Guarda não serializa todas operações concorrentes entre abas (limite conhecido).

## Evidência

Backend130 OK/13skips; gravador22 Edge OK; runtime113 OK/10skips; frontend65/19arquivos OK com testTimeout30000; fixtures do wizard3/3 e build TypeScript/Vite OK após correção de tipos; protocolo privado1/1; preparação real SGIND HTTP200 e cancelamento sem receita/credenciais.

- Validação real da rota SGIND: HTTP200, toolbar Iniciar presente, captura pausada e senha visível; cancelou sem receita e sem credenciais. Login/autenticação real e downloads corporativos não foram executados. Gate de execução autenticada SGIND/IQOS continua separado e fechado.
- Revisões individuais de pareamento/URLs e exclusão sem Critical/Important. Revisão do gravador identificou abas de preparação gerando índices inválidos de replay; corrigido e testado. Deadlock de Playwright ao acessar navegador dentro de binding foi reproduzido e corrigido enfileirando o início para o loop principal.
- App local continua backend --api-only em8000 e frontend5173. Nenhum worker/fila real iniciou; banco existente preservado nesta rodada, sem nova migração.

## Uso e continuidade

Após reiniciar backend: atualizar interface; **Gerar novo token**, copiar console e parear. Criar fluxo com a URL completa, escolher acesso para execução, abrir gravação, fazer login manual e abrir a página indicada, fechar abas de preparação, iniciar e capturar ações, parar e revisar/publicar. Excluir somente por confirmação explícita na interface.

Próximo escopo: validação de autenticação/execução corporativa e catálogos dependentes de acesso; compatibilidade com outras origens/redirects apenas após desenho e evidência próprios. Não tratar gravação como prova de execução.

---

# Atualização local — seleção de campos SGIND — 2026-10-13

Esta atualização prevalece sobre o bloqueio de seleção registrado anteriormente. Workspace: `C:\Users\kis\Downloads\Nexer-codex-nexer-reusable-flows-2026-10-13`, cópia sem `.git`, sem commit/push nesta máquina.

- Usuário confirmou cadastro de acesso funcionando e encontrou bloqueio ao selecionar campos. Diagnóstico comprovou dois problemas: rejeição explícita do host corporativo no serviço/picker e URL do perfil apontando para `/`, que abre a página padrão Apache sem formulário. `/sgind/` abre o SGIND com usuário, senha e botão visíveis.
- Validação real: DNS corporativo resolveu; HTTP200 usando certificados confiáveis do Windows; Edge limpo abriu `/sgind/`; transporte existente `context.request` também validou HTTPS. O próprio `pick_login` capturou os3 controles no SGIND real, sem digitar credenciais. Não foi necessário alterar roteamento, TLS ou regras de redirects.
- Removida rejeição do host corporativo SOMENTE de `apps/backend/app/services/login_recordings.py` e `apps/recorder/nexer_recorder/login_picker.py`. Seleção mantém sessão limpa, requisições GET/HEAD da mesma origem, redirects bloqueados, serviço workers/WebSockets/downloads bloqueados e captura de seletores estruturais, sem valores. Gates de autenticação/execução corporativa no runtime permanecem fechados. Não afirmar validação de login, relatórios, IQOS real ou produção.
- `LoginProfilesPage.tsx` agora permite alterar a URL do perfil dentro do mesmo site e salvar nova versão. Alteração limpa alvos de usuário/senha/botão e regra de sucesso, exigindo reidentificação antes de publicar. Versões anteriores preservadas. Para trocar o site/origem, cadastrar outro acesso.
- O perfil real do usuário não foi alterado automaticamente. Próximo uso: novo pareamento após reinício do backend; selecionar acesso cadastrado; editar URL para `https://indicadoresenergisaess.scl.corp/sgind/`; Salvar perfil; Identificar campos no Edge; clicar usuário, senha e botão sem preencher credenciais.
- Evidência final: backend114 OK/13skips; gravador19/19 com Edge; runtime109 OK/10skips; processo privado de seleção1/1 Edge local; frontend55/18 arquivos com `--testTimeout=30000`, build TypeScript/Vite OK. Timeouts da rodada anterior de5s permanecem registrados; nenhuma mudança permanente no timeout da suíte. Regressões RED→GREEN observadas para bloqueio, edição de URL e reidentificação após edição.
- Revisão independente confirmou restrições de captura/runtime; observação de troca de origem esclarecida na interface. Invalidação de seletores antigos foi corrigida e testada após revisão.
- Backend local continua `scripts/run_local.py --api-only`, interface `http://127.0.0.1:5173`; nenhuma fila/worker real iniciado. Banco novo desta cópia migrado até0007. Nenhuma mudança do banco real de perfis nesta rodada.

---

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


## Retomada kis — cadastro e seleção de acesso (2026-10-13)

- Workspace atual: `C:\Users\kis\Downloads\Nexer-codex-nexer-reusable-flows-2026-10-13`, cópia sem `.git`. Frontend instalado com `npm ci`, em `http://127.0.0.1:5173`. Backend usa `scripts/run_local.py --api-only`; nenhum worker foi iniciado. Banco novo `data/nexer.db` migrado até0007.
- Corrigido frontend que descartava `error.message` da API, preservando fallback por status. API de criação de acesso explica `LOGIN_URL_INVALID` sem repetir dados enviados. Regras de URL preservadas. Usuário confirmou que conseguiu cadastrar o acesso após a correção.
- Na seleção de campos, erro reproduzido por perfil do host corporativo: `CORPORATE_AUTH_NOT_VALIDATED`. Serviço e picker têm bloqueio explícito anterior ao processo Edge; não é falta de Edge/Playwright. A API agora explica que a seleção SGIND/IQOS aguarda validação corporativa.
- DNS corporativo resolveu nesta máquina; isso não demonstra acesso à página, seleção de campos ou execução. Pergunta pendente: usuário está no computador corporativo e consegue abrir SGIND normalmente no Edge? Gates continuam fechados.
- Testes backend114 OK/13skips. Frontend53/18 arquivos passou com `--testTimeout=30000`; execução padrão apresentou dois timeouts de5s em `NewFlowPage.test.tsx`. Build TypeScript/Vite passou. Regressões de mensagem observadas RED→GREEN; entrada não é refletida na resposta.
- Alterações locais: `apps/backend/app/main.py`, `apps/backend/app/api/login_profiles.py`, `apps/backend/tests/test_login_profiles_api.py`, `apps/frontend/src/lib/api.ts`, novo `apps/frontend/src/lib/api.test.ts`. Sem commit/push nesta máquina. Reiniciar backend para ativar mensagens exige novo pareamento.
