# Launcher desktop Nexer — 13/10/2026

O executável antigo `Nexer.exe` iniciava a interface Streamlit legada (porta 8501). Ele foi removido e substituído por um executável PyInstaller gerado a partir de `scripts/nexer_desktop.py`.

O novo `Nexer.exe` abre uma janela de controle com:
- **Abrir dashboard**: inicializa apenas a API local (`scripts/run_local.py --api-only`) e o frontend Vite (porta 5173), se não estiverem em execução, e abre o dashboard atual no navegador.
- **Reiniciar API**: solicita confirmação, interrompe somente a API local do Nexer (identificação pelo caminho absoluto do `run_local.py`, opção `--api-only` e porta 8000), aguarda liberação e inicia novamente; frontend permanece em execução.
- **Finalizar API**: solicita confirmação e encerra a API verificada, sem tocar em processos não pertencentes ao projeto.
- A janela é independente do dashboard; não expõe endpoint remoto de encerramento de processo.
- `Nexer.bat` agora apenas abre o novo executável, sem instalar dependências ou iniciar Streamlit.

Pré-requisitos: Python 3.12 com dependências backend instaladas, Node.js e `apps/frontend/node_modules` existentes; o executável empacota só a janela de controle, não o backend inteiro. Não inicia worker de relatórios e não armazena credenciais.

Validações: `python -m py_compile scripts/nexer_desktop.py` passou; `manage_nexer.ps1 -Action status` retornou API_RUNNING; `-Action start` passou com API/frontend já ativos; PyInstaller concluiu build; executável novo foi aberto e confirmado como processo ativo, e encerrado em seguida; substituição do binário antigo confirmada com hashes distintos. Não foi executado teste destrutivo real de restart/stop da API em sessão do usuário, para evitar interromper gravações ativas.

**Nota:** esta pasta não contém .git; nenhum commit/push realizado.
