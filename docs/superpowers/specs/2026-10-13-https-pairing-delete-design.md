# HTTPS, pareamento e exclusão de acessos — desenho aprovado

Usuário pediu implementar gravação HTTPS incluindo `https://indicadoresenergisaess.scl.corp/sgind/#/relatatendtodasocorrencias`, botão para novo token na tela de pareamento e exclusão de perfis. Autorização existente para melhorias reversíveis; esta cópia sem `.git` não permite commits/worktrees.

URLs: aceitar HTTPS e HTTP loopback, preservando rotas de aplicação `#/caminho` sem query/credenciais; origens de perfil não incluem fragmentos. Mesma regra na UI, API, gravador e configuração da receita.

Gravação HTTPS: nova sessão limpa do Edge, preparação com captura pausada; usuário entra no site e abre a rota solicitada. Iniciar gravação exige URL esperada e ausência de senha visível. Nenhum evento de preparação/login entra na receita. Protocolo privado sinaliza início; finalizar antes disso é recusado. HTTP local conserva gravação imediata. Política de origem inicial, redirects bloqueados, sem workers/WebSockets/estado persistido/downloads salvos. Credenciais nunca em receita, SQLite, eventos ou cache. Gate de execução autenticada corporativa permanece separado e fechado.

Novo token: endpoint de renovação local com verificação de origem/host, limite de frequência, código uso único/5min somente no console do operador, resposta HTTP sem código. Não autentica automaticamente; substitui código anterior e preserva sessões existentes.

Excluir perfil: confirmação explícita, exclusão transacional de perfil+versões sem vínculos, recusa durante seleção ativa ou quando receitas salvas usam o perfil. Grupos/histórico/snapshots preservados. Desativação existente permanece compatível.

Verificação: regressões RED→GREEN; suites relevantes; Edge sintético para login/preparação/início/encerramento e restrições; navegação corporativa real sem login automatizado. Revisão independente antes de concluir. Atualizar handoff com evidência e limites; nenhum segredo em chat/artefatos.
