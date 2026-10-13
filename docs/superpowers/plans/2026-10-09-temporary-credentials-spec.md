# Nexer — especificação de credenciais temporárias
Data: 09/10/2026. Desenho conceitual aprovado pelo usuário no chat.
Autoridade: decisão opção B em NEXER_WORK_HANDOFF_2026-10-09.md.

## Produto e limites
Aplicação local Windows com custo de infraestrutura R$0.
Credenciais SGIND e IQOS são distintas. A interface solicita as necessárias para cada execução. Não representam identidade Nexer nem dão acesso à API por si mesmas.
Nenhuma senha corporativa em .env, SQLite, receita, snapshot de parâmetros, eventos, logs, arquivos, storage do navegador ou keyring.
Reinício invalida acesso temporário e credenciais. Execuções existentes não recuperam segredos automaticamente.
Python não garante sobrescrita física de strings nem proteção contra administrador, dump ou swap do sistema; a garantia é ausência de persistência implementada pela aplicação e revogação de acesso.

## Acesso local
API somente 127.0.0.1; validar Host/Origin e rejeitar mutações sem origem local permitida.
Launcher gera código aleatório de pareamento de uso único, validade 5 minutos, mostrado apenas no console local. Nunca incluir em URL, logs de diagnóstico ou resposta pública.
POST /auth/login recebe somente {pairing_code}; tentativa inválida retorna erro constante; aplicar limite de tentativas.
Sessão aleatória com TTL máximo 8 horas; cookie HttpOnly/SameSite Strict, sem exposição do token ao JavaScript.
GET /auth/session informa somente estado de acesso local.
POST /auth/logout revoga sessão e todas as execuções corporativas associadas.
Não permitir bypass via NEXER_ENVIRONMENT=test no servidor de produção; testes usam dependências explicitamente substituídas.
Repareamento exige ação no console local; não criar rota pública que gere códigos.

## Cofre por execução
EphemeralCredentialVault vive somente no processo API, protegido por RLock e relógio monotônico.
Registro: execution_id → owner_session, expires_at, sistemas.
Sistemas permitidos: SGIND/IQOS; cada sistema contém username/password.
TTL máximo 3600 segundos; campo vazio ou excessivo falha com erro constante.
put(execution_id, owner, systems, ttl_seconds) não sobrescreve vínculo existente.
get(execution_id, owner, system) devolve cópia, somente enquanto vigente.
revoke(execution_id) e revoke_owner(owner) eliminam referências.
Limpeza periódica deve remover registros expirados mesmo sem consultas.
Limite de capacidade e tamanho de requisição impede crescimento ilimitado.
TTL não pode ultrapassar a validade restante da sessão proprietária.

## Criação e ciclo da execução
POST /executions recebe parâmetros normais e corporate_credentials em campo separado.
Pydantic SecretStr e repr=False para valores sensíveis; erro de validação não reproduz body.
A API valida receitas, sistema requerido e disponibilidade do worker antes de aceitar credenciais.
Credenciais são copiadas para cofre antes de tornar a execução disponível ao worker; rollback revoga o registro.
Execution.inputs contém somente parâmetros não sensíveis e referências declarativas.
Nunca colocar segredos em requested_by, nome, metadata, URL ou mensagens.
Cancelamento, término, expiração e logout revogam o cofre. Worker interrompe novas ações, fecha contexto e descarta referências.
Falha da API/canal deve bloquear ações posteriores e encerrar execução com código estável.

## Canal entre processos
Launcher coordena API e worker. Capability aleatória por encarnação é entregue por pipe/handle herdado, nunca por argumento de linha de comando, .env, arquivo ou banco.
Canal somente loopback ou pipe Windows restrito ao usuário local; não usar pickle ou desserialização executável.
API valida capability por comparação constante e verifica no SQLite a reserva ativa da execução pelo worker da mesma encarnação.
Worker solicita credencial de um único sistema e execução; nenhum endpoint lista o cofre.
Não incluir body do canal em logs; respostas sem cache.
Antes de cada ação sensível, worker confirma validade e cancelamento; não manter credencial reutilizável fora do escopo necessário.
Backend/worker reiniciado perde capability; execuções sem vínculo atual falham, sem replay automático.

## Runtime e destino
Fluxo temporário não chama KeyringCredentialProvider nem SessionStateStore.
Contexto novo por item, não persistente, sem storage_state, trace, HAR ou screenshot durante autenticação; close em finally.
Credenciais corporativas só entram no adaptador de autenticação do sistema. Não disponibilizar senhas ao resolver genérico de inputs.
Lista de destinos vem de configuração validada do adaptador, não de receita arbitrária.
SGIND origem: https://indicadoresenergisaess.scl.corp (porta 443; sem userinfo).
Validar login_url, URL final depois de navegação e destino do formulário antes de preencher/clicar.
Bloquear requests e redirecionamentos para destinos fora da política no contexto autenticado; novas origens corporativas exigem revisão.
Não executar JavaScript arbitrário de receita no contexto autenticado.
SGIND login observado: input[name="cre_username"], input[name="cre_password"], botão Logar.
Seletor confiável de sucesso SGIND não confirmado: autenticação real permanece bloqueada.
IQOS URL/seletores não confirmados: integração permanece bloqueada.
Não contornar MFA/SSO/controles corporativos.

## Interface visual
Tela de entrada: código de pareamento local, instrução de obtê-lo no console.
Nova execução: parâmetros separados de cartões SGIND/IQOS; indicar sistemas bloqueados e motivo.
Senhas em type=password; sem localStorage/sessionStorage ou cache do React Query.
Envio direto com fetch; mutations contendo segredos não podem permanecer em cache.
Limpar username/password após tentativa de envio, ao sair e ao desmontar formulário.
Servidor responde somente identificador/estado da execução; não ecoa credenciais.
A interface só apresenta autenticação corporativa como validada após evidência real.

## Evidência exigida
Testes de isolamento, expiração exata, revogação, rollback, acesso cruzado, logout/cancelamento, reinício de processo, capability inválida e reserva de worker.
Canário sintético não pode aparecer no SQLite, respostas, eventos ou logs capturados.
Runtime: userinfo/porta/host parecido/redirect externo, receita maliciosa e exceções de browser não vazam segredo.
Frontend: campos separados, limpeza na falha/sucesso/logout e ausência de cache/storage.
Rodar suites segmentadas, typecheck, build e diff --check. E2E corporativo somente no ambiente autorizado e com credenciais digitadas localmente.

## Estado real nesta rodada
Foi criado um cofre isolado e cinco testes; ainda não conectado à API/worker/UI.
Login antigo e keyring continuam ativos no caminho existente.
Nenhum login corporativo foi executado; nenhum commit/push foi feito.
