# Nexer — estabilidade e arquivos no histórico (15/10/2026)

Base: `b414fbe97f06c3188ed28357dc8f8039ef808412`, branch remota `feat/nexer-portable-bootstrap-2026-10-14`. Desenvolvimento isolado em `C:/Users/hikas/.codex/worktrees/nexer-distribution-audit/Nexer`; o checkout principal e seus documentos pendentes foram preservados.

O usuário autorizou continuidade autônoma. Plano/spec: `docs/superpowers/plans/2026-10-15-execution-artifacts.md` e `docs/superpowers/specs/2026-10-15-execution-artifacts-design.md`.

## Entregas

- Instalador alinhado ao pareamento: não exige nem chama `setup_auth.py`. `SkipAuthSetup` é compatibilidade obsoleta para `NoLaunch`; banco existente continua protegido e launcher continua API-only. `.env.example` e instalação documentados corretamente.
- Fechamento de `details` desmonta somente os pickers. O editor permanece montado com o rascunho; sessões em abertura são canceladas quando chegam, e respostas antigas de polling não alteram o rascunho. Os dois cenários tiveram RED/GREEN observado.
- `validate_file` sempre registra SHA-256, inclusive sem `calculate_checksum`, vinculando a validação aos bytes observados. O hash é calculado em blocos, com checagem de cancelamento.
- Worker publica registros `VALIDATED_FILE` e sucesso do item na mesma transação. Downloads exigem validação posterior; baixar de novo no mesmo caminho invalida a validação anterior. Execuções falhas, canceladas e dry-run não publicam arquivos. Sem migration nova.
- API autenticada: `GET /executions/{id}/artifacts` e `GET /executions/{id}/artifacts/{artifact_id}/download`. Resposta sem caminhos de disco/rede; download deriva caminho dos IDs/nome, exige tamanho e SHA-256 e usa o mesmo handle conferido. Attachment, octet-stream, no-store e nosniff. Rejeita traversal, nomes Windows inseguros, junctions, symlinks e hardlinks.
- Histórico mostra arquivos e oferece download autenticado dos bytes; falhas têm orientação fixa. API e worker usam a mesma configuração de diretório, inclusive `.env`.

## Evidência de integração real

`apps/worker/tests/test_recorded_artifacts_e2e.py`, habilitado com `NEXER_RUN_ARTIFACT_E2E=1`:

1. Site HTTP sintético em porta efêmera; gravação real no Edge usando o bundle do gravador.
2. Receita sem o valor demonstrado; revisão adiciona `validate_file` explicitamente.
3. Duas execuções criadas na API HTTP real, com empresas sintéticas A e B.
4. Worker e runtime reais executam a receita no Edge. A API lista metadados persistidos e SHA-256 esperado.
5. Frontend React real via Vite em porta efêmera, com proxy temporário para a API. Edge abre o histórico e aciona o botão de download.
6. Os bytes salvos pela UI correspondem ao CSV de cada execução e diferem entre A e B. Nenhum dado corporativo, fila existente ou credencial real é utilizado.

O cadastro inicial da versão publicada e a sessão local são preparados pela fixture. O teste não cobre o onboarding interativo nem a publicação pelo wizard. Worker/runner rodam no processo de teste; não é teste de transporte em subprocesso do worker. O teste não comprova concorrência, restart ou homologação de CSV de negócio. A primeira execução falhou na limpeza do SQLite; descarte do engine foi movido para antes da remoção do diretório e a reexecução passou.

## Revisão e regressões

Revisão independente somente leitura encontrou duas falhas, ambas reproduzidas e corrigidas com testes: diretório de `.env` ignorado pelo worker e representações com `..` divergentes entre download/validação. Segunda revisão confirmou as correções. Dois casos adicionais de integridade tiveram RED/GREEN: substituição por conteúdo de mesmo tamanho e download posterior à validação.

A revisão final encontrou uma fixture duplicando o código de automação em dois subcenários. Os cenários foram separados em testes independentes; suíte worker completa reexecutada com sucesso. Não houve novo achado no código de integridade.

## Limites e continuação

- Arquivos gerados antes desta entrega não recebem registros retroativos. Uma lista vazia não significa que o diretório físico esteja vazio.
- **Mudança deliberada:** receitas que baixam arquivos sem `validate_file` agora falham com `ARTIFACT_NOT_VALIDATED`, e a UI orienta revisão no Studio. A gravação/wizard ainda não adiciona automaticamente essa etapa; a fixture E2E a adiciona na revisão. Prioridade seguinte: configuração guiada de validação, inclusive nome preservado do site, sem relaxar o contrato.
- `output: {type: file}` sem ação de download mantém comportamento anterior; não é prova de artefato obrigatório entregue. Contrato de obrigatoriedade de saída continua pendente.
- Tamanho/extensão/hash não validam conteúdo de negócio nem rejeitam todo HTML/SSO disfarçado. Validação estrutural de CSV e homologação real seguem pendentes.
- Downloads grandes são materializados como Blob no frontend; limites de memória/disco não foram medidos. Processos locais com escrita podem alterar arquivo durante transmissão; não se promete isolamento contra administrador local malicioso.
- Exposição histórica do banco, remoção do binário legado do pacote público, separação completa dos adaptadores corporativos, clean-install em outra máquina e shell autossuficiente continuam pendentes. Nada foi publicado ou homologado corporativamente nesta rodada.
- Testes usam o Python existente do checkout principal; o worktree recebeu dependências frontend por `npm ci`, sem alteração de lockfile. Houve avisos esbuild allowScripts e depreciação Starlette/httpx; builds e testes observados são registrados abaixo.

## Verificação final

Todas as execuções abaixo terminaram com exit 0. Não somar as reexecuções dirigidas às contagens finais.

| Suíte | Comando/base | Resultado final |
|---|---|---|
| Frontend | `npm test` em `apps/frontend` | 31 arquivos, 113 passaram |
| Build | `npm run build` em `apps/frontend` | TypeScript + Vite OK, 120 módulos |
| Backend | `python -m unittest discover -s apps/backend/tests -v` | 162 testes, 149 passaram, 13 skips |
| Runtime | `python -m unittest discover -s apps/runtime/tests -v`, `NEXER_RUN_RECORDER_E2E=1` | 161 testes, 151 passaram, 10 skips |
| Worker | `python -m unittest discover -s apps/worker/tests -v`, `NEXER_RUN_ARTIFACT_E2E=1` | 45 testes, 44 passaram, 1 skip |
| Gravador | `python -m unittest discover -s apps/recorder/tests -v`, `NEXER_RUN_RECORDER_E2E=1` | 64 testes, todos passaram |
| Raiz/instalador | `python -m unittest discover -s tests -v` | 16 testes, todos passaram |

Total sem duplicar rodadas: **537 passaram, 24 skips**. Skips permanecem gates fechados; incluem testes de processos/credenciais corporativas e opt-ins de navegador separados. Não representam homologação.

Interpretador: `C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe`. `PYTHONPATH` inclui `apps/backend`, `apps/backend/tests`, `apps/runtime`, `apps/runtime/tests`, `apps/worker` e `apps/recorder`. `git diff --check` e parser PowerShell do instalador sem erros. Logs temporários `temp-*-tests.log` estão ignorados e não são fonte de dados corporativos.

Branch local de preservação: `codex/nexer-stability-artifacts-2026-10-15`. Sem merge, push, PR ou release; manter o worktree para a próxima implementação. O checkout principal não deve ser usado para executar este código por engano.
