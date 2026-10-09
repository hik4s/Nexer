> ATUALIZAÇÃO 09/10/2026: leia primeiro [CONTINUAR_NEXER_2026-10-09.md](CONTINUAR_NEXER_2026-10-09.md). Ele consolida o estado atual, testes, pendências e a autorização expressa de commit/push deste checkpoint.

# Nexer — Plano Mestre

## Identidade do produto
- Nome oficial: **Nexer**.
- Repositório GitHub verificado em 09/10/2026: `https://github.com/hik4s/Nexer.git`; `git ls-remote origin HEAD` respondeu com sucesso.
- Não manter referências ativas à marca antiga em interfaces, código, pacotes, variáveis de ambiente, documentação ou artefatos distribuídos. Referências históricas só podem permanecer quando necessárias e identificadas como históricas.
- Requisito obrigatório: infraestrutura de custo zero. Priorizar execução local, SQLite e ferramentas gratuitas; não introduzir serviços pagos.

## Regras de desenvolvimento
- Trabalhar na branch `feat/etapa1-foundation`; não alterar `master`.
- Preservar o legado funcional enquanto a migração não for decidida explicitamente.
- Avançar em microtarefas: implementar → testar → verificar diff → atualizar documentação.
- Não declarar uma etapa concluída sem evidência real de teste.
- Nunca guardar senhas em receitas, logs ou parâmetros comuns; usar mecanismo seguro de credenciais/sessões.
- Recuperação de worker perdido deve falhar de forma segura, sem replay automático que possa duplicar efeitos colaterais.

## Arquitetura-alvo
Frontend React/Vite → API FastAPI → Worker → Runtime de automação → SQLite + eventos SSE.

- **Frontend:** Login, Dashboard, Automações, Execuções, Nova execução, Diagnóstico, Destinos e Studio.
- **Backend:** API local, persistência, contratos, política de segredos e eventos.
- **Worker:** reserva/processamento, heartbeat, watchdog e recuperação controlada.
- **Runtime:** receitas declarativas, autenticação/sessões, Edge/Playwright, downloads e validação.
- **Persistência:** SQLite local, sem necessidade de backend hospedado pago.

## Plano de entregas

### E1 — Fundação
- API, Worker, Runtime, SQLite, SSE e frontend integrados.
- Cancelamento, destinos, execução básica e contrato de saúde.
- Login visual já presente, mas a validação atual no frontend é apenas uma fundação; não deve ser tratada como segurança real até autenticar pelo backend.
- Gate formal E1 com testes integrados e evidências reproduzíveis.

### E2 — Studio e resiliência
- Criar, editar, versionar, testar e publicar receitas.
- Retry por etapa, checkpoints persistidos, heartbeat, watchdog e recuperação fail-closed.
- Definir idempotência e regras seguras antes de habilitar retomada automática.
- Separar receita (como executar) dos parâmetros de cada execução (com quais valores executar).

### E3 — Produto final
- Qualidade, acessibilidade, tratamento de erros, experiência visual, empacotamento e distribuição.
- Documentação de instalação, operação e diagnóstico.
- Validação final ponta a ponta.

## Fluxo de automação esperado
1. Usuário entra no Nexer.
2. Sessão/credenciais autorizadas são obtidas por mecanismo seguro.
3. Runtime abre SGIND e IQOS conforme a sessão configurada.
4. Receita navega até o relatório específico.
5. Dashboard fornece os valores variáveis da execução: empresa, período, datas, regional e filtros.
6. Receita define seletores e ações sem fixar valores de negócio que devem ser variáveis.
7. Arquivo é baixado, validado e gravado no destino escolhido.

## Receitas e parâmetros
- Receita define **como** executar: navegação, seletores, ações, validações, download e variáveis declaradas.
- Dashboard define **com quais valores**: empresa, datas, regional, tipo de relatório, período, destino e filtros.
- Usar placeholders como `{{company}}`, `{{period_start}}` e `{{period_end}}`.
- Cada execução deve guardar um snapshot dos parâmetros usados e uma referência à versão da receita.
- Senhas e tokens nunca são variáveis normais de receita.

## Resiliência — regras obrigatórias
- Retry é por etapa e limitado pela política configurada.
- Checkpoint registra o último progresso confirmado.
- Watchdog detecta perda real de heartbeat/processo.
- Recuperação classifica e preserva estado, sem replay cego.
- Worker realmente perdido pode ser marcado como `WORKER_LOST`/falha; não reencaminhar automaticamente quando houver risco de duplicar ações.
- Retomada só pode ser liberada após regras explícitas de repetibilidade/idempotência.

## Estado e próximos passos
1. Renomeação local concluída: marca, frontend/backend, pacote Worker, namespaces de credenciais, variáveis de ambiente, executável/launcher, CI, scripts e documentação foram atualizados. `git grep -in relatpy` não encontrou referências em arquivos rastreados na verificação de 09/10/2026; arquivos não rastreados ainda precisam ser incluídos numa auditoria mais ampla.
2. Remote verificado: `origin` aponta para `https://github.com/hik4s/Nexer.git`; `git ls-remote origin HEAD` respondeu com sucesso em 09/10/2026.
3. Testes segmentados em 09/10/2026: Backend 41 passaram; Worker 15 passaram e 1 E2E foi ignorado; Runtime 46 passaram e 1 E2E foi ignorado; frontend 17 passaram em 9 arquivos após adicionar teste de falha no logout; `npm run typecheck` não reportou erros; `npm run build` concluiu com código 0. A execução isolada do Vitest com `--pool=threads --maxWorkers=1` também passou.
4. `git diff --check` não indicou erros de whitespace; apenas avisos de conversão LF/CRLF. O estado ainda contém alterações pendentes que devem ser preservadas.
5. Verificação integrada `scripts/verify.ps1 -SkipAudit` concluída em 09/10/2026 com código de saída 0 após a correção do logout: pip check, 41 testes Backend, 15 testes Worker (1 E2E ignorado), 46 testes Runtime (1 E2E ignorado), 17 testes frontend, typecheck e build passaram. A auditoria de dependências foi excluída pelo parâmetro `-SkipAudit`. npm avisou que o script de instalação do `esbuild@0.28.2` ainda não foi aprovado; não foi aprovado automaticamente. Não há validação ponta a ponta do login SGIND/IQOS ou download real.
6. Próximo passo: revisar os diffs restantes, incluindo o pacote Worker renomeado, e testar a configuração de autenticação local do Nexer pelo fluxo UI → backend sem usar credenciais corporativas no chat.
7. Integrar autenticação/sessão segura com SGIND e IQOS após confirmar a configuração local, inspecionando seletores sem enviar credenciais automaticamente.
8. Executar os testes E2E com Edge e validar login/download real somente quando houver autorização e ambiente de teste apropriado.

## Ambiente local
- Branch esperada: `feat/etapa1-foundation`.
- Pasta local atual: `C:\Users\kis\Downloads\Nexer`.
- Não alterar `master`.

## Atualização Work — 09/10/2026: desenho aprovado e primeiro módulo
A decisão de credenciais temporárias da opção B prevalece sobre passos antigos de .env/setup_auth/keyring.
Documentos: docs/superpowers/plans/2026-10-09-temporary-credentials-spec.md e 2026-10-09-temporary-credentials.md.
Criados apps/backend/app/ephemeral_credentials.py e apps/backend/tests/test_ephemeral_credentials.py. Cofre isolado, em memória, por execução/proprietário/sistema, com TTL e revogação; ainda NÃO conectado à API, worker ou frontend.
Evidência real: cinco testes novos falharam inicialmente por módulo ausente e depois passaram; suite backend 46 testes OK, exit 0, com PYTHONPATH apps/backend;apps/worker;apps/runtime e NEXER_ENVIRONMENT=test.
Primeiro comando da suite tinha PYTHONPATH incompleto e falhou em test_etapa1_gate (import nexer_worker); comando corrigido sem alterar código.
Aviso StarletteDeprecationWarning sobre httpx/httpx2 observado. Não executar migração de dependências automaticamente.
Diff dos dois novos arquivos revisado. Nenhum commit/push; alterações preexistentes preservadas.
Pendente: pareamento local, canal entre processos, integração do cofre/ciclo de limpeza, substituição keyring no fluxo ativo, formulário corporativo e testes ponta a ponta. Cofre atual expira acesso em get/put, mas remoção periódica sem consultas e limite de capacidade serão responsabilidade da integração.
Nenhuma nova UI entregue nesta rodada; frontend/worker/runtime não retestados porque não foram alterados.
Login SGIND real permanece bloqueado por indicador de sucesso desconhecido; IQOS por URL/seletores desconhecidos. Não solicitar segredos no chat.


## Continuação Work — 09/10/2026: pareamento confirmado e vínculo por execução
Usuário confirmou acesso real à dashboard com código local. Esta confirmação substitui a nota anterior API_NOT_LISTENING; não reiniciar a API ou invalidar sua sessão automaticamente.
Implementado execution_credentials.py, put_session_credentials em security.py e criação de execução ligada ao cofre/canal antes do commit da fila. Campos corporativos continuam fora dos modelos SQLAlchemy/respostas/inputs; dicionário transitório é limpo após a cópia para o cofre, sem promessa de zeroização física de strings Python.
Política confiável require_validated_corporate_auth permanece bloqueando QUALQUER envio corporativo na produção. Somente dependency override dentro dos testes autoriza credenciais sintéticas. Não há flag no request/.env para contornar o bloqueio.
Vínculo exige sistema correspondente à automação e worker ONLINE da encarnação atual, heartbeat até 30s, sem stopped_at. Owner vem exclusivamente do cookie; não é persistido. TTL limitado à sessão e a 3600s. Logout é serializado com put; bind ocorre depois de liberar session lock para evitar inversão channel -> session. Mudança de encarnação antes do bind falha e revoga.
Rollback de IntegrityError e de qualquer exceção antes/durante commit revoga cofre e vínculo. Cancelamento, logout, timeout e release já existentes foram exercitados com credenciais presentes, não por ausência inicial.
Novo test_execution_credentials.py: 12 testes com SQLite temporário e canários fictícios; criação/claim/release idempotente, dump SQL/resposta sem canários/owner, rollback, cancelamento, logout, TTL, worker stale/canal ausente, sistema incorreto, mudança de encarnação e logout concorrente com submissão. Observado RED com módulo gate ausente; depois gate sozinho permitiu reproduzir falta de armazenamento/validação; implementação passou. Quatro casos adicionais verificaram comportamento já implementado.
Verificação final desta rodada: backend Ran 74 tests, OK, exit0; worker Ran 19 tests, OK (skipped=1, E2E Edge não executado); git diff --check exit0, avisos LF/CRLF. Aviso Starlette/httpx legado mantido. Frontend/runtime sem alterações nesta rodada, não rerodados. Revisão desta fatia pelo próprio autor; revisão independente da branch completa ainda pendente.
Ruling: preservar branch e alterações aprovadas, sem nova worktree/commit/push; política corporativa permanece bloqueada pois URL/seletores IQOS e sucesso SGIND não estão validados. Custo: esta fatia não libera execução corporativa real nem valida launcher API-worker completo.
Pendências: validar adaptadores reais (sem pedir senhas no chat), restringir contexto autenticado/origens e scripts antes de habilitar login; finalizar formulário efêmero fora do cache React Query; cancelamento do contexto durante navegação e expiração durante ações; E2E do launcher; limpar mapas de owners expirados/terminais periodicamente para não reter tokens além do necessário; revisão independente final. Não afirmar plano inteiro concluído.
API atual não foi reiniciada: alterações backend entram em vigor no próximo reinício manual. Nunca coletar o código de pareamento real.

### URLs e formulário corporativo informados — 09/10/2026
Usuário forneceu URLs IQOS https://indicadoresenergisaess.scl.corp/iqos/#/login e SGIND https://indicadoresenergisaess.scl.corp/sgind/#/login, junto de HTML de ambos os formulários. Evidência registrada em docs/development/corporate-login-evidence.md. Usuário/senha têm name cre_username/cre_password; botão real é button[type="submit"]; SGIND form#idFormLogin, IQOS form[name="form"]. Não usar classes de validação Angular ou atributos pc/_ngcontent como seletores.
Esta evidência substitui "URL/seletores IQOS desconhecidos" nos registros anteriores, mas NÃO valida sucesso de autenticação. Precisamos URL e elemento exclusivo pós-login de cada sistema. Políticas da API/runtime ainda bloqueiam corp login; nenhum segredo solicitado, enviado ou armazenado.
Interface IQOS atualizada para aguardando validação, explicando que URL/formulário foram informados e falta indicador de sucesso; campos continuam desabilitados. Nenhuma navegação/login real executado nesta rodada. Branch feat/etapa1-foundation confirmada; sem commit/push.

### Evidência home e probe anônimo — 09/10/2026
Usuário forneceu URLs pós-login /sgind/#/home e /iqos/#/home e HTML com app-home-page em ambos. Sucesso candidato composto: URL home exata do sistema + componente visível + formulário login ausente.
Probe REAL na máquina do usuário via Playwright/Edge headless, contextos novos sem cookies/storage state e sem preencher credenciais: home SGIND -> /sgind/#/login, login_visible=true, home_visible=false; home IQOS -> /iqos/#/login, mesmos estados. TLS padrão, exit0. Esta evidência valida redirecionamento anônimo; NÃO é um login automático/E2E autenticado.
corporate_auth.py agora define CorporateLoginDefinition congelada para SGIND/IQOS, URLs/selectores confiáveis independentes da receita e matches_authenticated_home (predicado puro). validate_corporate_url reconhece IQOS e restringe cada sistema ao seu caminho, bloqueando troca SGIND/IQOS, aliases, traversal, caminhos percent-encoded, userinfo, host semelhante, porta externa e HTTP.
Cinco novos testes observados RED (política IQOS ausente, caminhos não restritos, definições/matcher ausentes), depois GREEN. Runtime Ran53 tests OK skipped=1, exit0. Worker Ran19 tests OK skipped=1, exit0. Esses skips são E2E Edge opt-in, não executados. O probe Edge anônimo é separado desses testes.
Interface SGIND/IQOS agora diz "Telas de login e início identificadas. Integração automática em preparação." Campos seguem desabilitados. Teste de texto observado RED antes da alteração.
Ruling: evidência manual+probe permite fixar URL/home/seletores; manter gates API/require_validated_adapter enquanto login seguro do worker não está conectado. Custo: usuário ainda não pode enviar credenciais corporativas por esta UI. Não pedir novamente URL/HTML home já recebidos.
Pendências de implementação, não de dados home: interceptar destinos e restringir scripts no contexto; preencher e validar usando client efêmero; revalidar credenciais/cancelamento durante ações; formulário fora de React Query/storage; teste launcher/E2E autenticado com senha digitada pelo usuário apenas na UI. Mensagem de erro de senha desconhecida pode ser tratada por timeout/código constante. Não habilitar guard de renovação de receita arbitrária.
Branch feat/etapa1-foundation confirmada; mudanças preservadas, sem commit/push. Próxima etapa é ligar definição confiável ao worker, não solicitar nova aprovação para continuar desenvolvimento autorizado.
