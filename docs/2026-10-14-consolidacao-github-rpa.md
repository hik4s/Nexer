# Nexer — consolidação para publicação da branch (14/10/2026)

## Propósito
Salvar o trabalho validado da arquitetura React/FastAPI/Playwright e a evolução do objetivo do produto: **Nexer Desktop-first, RPA de propósito geral para usuários comuns e empresas**. Ver `HANDOFF_NEXER_RPA_2026-10-14.md`, `docs/2026-10-14-auditoria-microtarefas-primeiro-relatorio.md` e `docs/2026-10-14-piloto-todas-ocorrencias-design.md`. Este registro é uma fotografia de preparação, não uma declaração de homologação SGIND/IQOS ou de produto pronto para venda.

## Origem legítima e preservação
- Repositório: `https://github.com/hik4s/Nexer` (público no momento da auditoria).
- Base da branch: `codex/smart-recorder-handoff-2026-10-14`, commit `6631b6bff1bec6ea05bab430235caa9d4d01b70f`.
- Branch de entrega: `feat/nexer-portable-bootstrap-2026-10-14`. Preparada em checkout independente, sem modificar `master` nem sobrescrever checkouts antigos.
- A pasta exportada `Nexer-codex-smart-recorder-handoff-2026-10-14` não tinha `.git`. Os arquivos foram comparados com o clone legítimo. As diferenças meramente CRLF/LF foram descartadas e **sete arquivos de mudanças reais** foram integrados do snapshot, junto de testes.
- Removido do **índice Git somente** o banco versionado `data/nexer.db` e o gitlink `Nexer` de diretório vazio, que não possuía `.gitmodules`. Os caminhos existentes em disco foram preservados; nenhum conteúdo histórico foi reescrito.
- O handoff master de 357 linhas foi copiado fielmente do artefato gerado nesta conversa: SHA256 `6fa74cc0e2ee9f6cd94c7148b0b00ff2033f305c724e55ccc4913e6d6f318f81`, tamanho 48.443 bytes.
- Nenhum `.env` operacional, senha corporativa ou banco deve ser comitado na nova árvore.

## Alterações incluídas
- Bootstrap: `Instalar-Nexer.cmd`, `scripts/install_nexer.ps1`, `scripts/requirements-windows-py312.lock.txt`, `.gitignore`, `.env.example`, `data/.gitkeep`, `docs/INSTALACAO_DO_GITHUB.md` e testes `tests/test_portable_distribution.py`.
- Código recuperado da exportação: `apps/recorder/nexer_recorder/capture.js` (janela arrastável, cliques internos desconsiderados), `apps/recorder/tests/test_capture_edge.py`; `apps/frontend/src/pages/NewBatchPage.tsx` (mensagem útil ao falhar carga de opções), `apps/frontend/src/pages/NewBatchPage.test.tsx`; `apps/backend/app/api/automation_versions.py`, `apps/backend/app/services/profile_execution.py` (publicar fluxo com perfil corporativo sem permitir execução não autorizada), `apps/backend/tests/test_automation_versions_api.py`.
- Documentos de continuidade: `docs/HANDOFF_NEXER_RPA_2026-10-14.md`, auditoria com 26 microtarefas, desenho do piloto, verificação de bootstrap e esta nota; `README.md` aponta para o handoff e para a instalação.

## Verificações reais — não extrapolar alcance
- Bootstrap a partir de arquivo ZIP gerado por `git archive`, sem `.git`, `.venv`, `node_modules` e SQLite: Python 3.12 em novo venv, pip/pip check OK, npm ci (168 pacotes), migrações Alembic até `0007_practical_workspace`, saída 0. Segunda passagem com constraints fixadas, saída 0. Frontend `tsc -b`, Vite build (119 módulos), API TestClient loopback `/version` e `/health` HTTP 200.
- Depois da integração dos sete arquivos da exportação, testes dirigidos: backend automations API **7/7**, recorder real Edge sintético **8/8**, frontend NewBatchPage **10/10**, portabilidade **5/5**; TypeScript e Vite build (119 módulos), saídas 0. Não equivalem a todas as suítes do projeto.
- Verificação de `.gitignore`: artefatos/caches protegidos, lockfiles, migrations, assets e scripts preservados. Arquivo original do handoff preservado com duas quebras Markdown intencionais via espaço duplo ao fim de 3 linhas (portanto `git diff --check` pode indicá-las).
- Varredura estática limitada de 449 arquivos versionados: 0 padrões de chaves privadas e tokens conhecidos. Não é comprovação de ausência de todos os segredos nem verificação do histórico.
- Nenhum worker na fila do usuário foi iniciado; sem login real SGIND/IQOS; nenhum relatório corporativo foi extraído.

## Alerta para distribuição pública
A **história anterior do repositório público** já inclui um `data/nexer.db` com 15 tabelas e alguns registros de automações/perfis (metadados avaliados apenas como contagens, sem divulgar valores). Excluí-lo na nova árvore **não limpa o histórico Git público**. Antes de divulgação comercial, realizar auditoria dos dados e, caso haja conteúdo sensível, coordenar saneamento de histórico, revogação de credenciais e política de acesso sem force push improvisado. Arquivos de documentação também podem citar hostnames e detalhes de operação corporativos — revisar sua distribuição pública com os responsáveis.

## Limitações pendentes
- O bootstrap ainda exige Python, Node/npm e rede de pacotes; não é instalador autossuficiente.
- Login local interativo e abertura por duplo clique não homologados em segunda máquina com portas livres.
- Não foi realizada suíte completa de todos os testes pós-integração; foram executados os testes direcionados acima.
- SGIND/IQOS reais continuam com autorização e correlação de downloads pendentes; execução de lote requer worker isolado com fila inspecionada.
- Shell desktop Tauri, assinatura, atualizações e Cloud são **propostas futuras**, não código entregue.

## Continuação recomendada
1. Revisar GitHub e nome da branch; usar este documento e handoff master como fonte de planejamento.
2. Resolver a exposição histórica do banco e verificar política de divulgação corporativa.
3. Validar o bootstrap com usuário real de administração local em VM/segundo Windows, sem registrar a senha nos testes.
4. Continuar a trilha de 26 microtarefas do primeiro piloto e a trilha RPA do handoff, sem duplicar recursos existentes.
5. Antes do primeiro relatório corporativo, inventariar fila/DB, habilitar apenas um worker isolado, recolher evidências autorizadas de consultas e downloads e entregar CSV próprio, íntegro e disponível na UI.

**Nota temporal:** afirmações em handoffs anteriores de que a branch ainda não foi enviada descrevem o instante da criação; confirmar o remoto com `git ls-remote` ao retomar.
