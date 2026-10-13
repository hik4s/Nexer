# Nexer — roadmap alinhado em 2026-10-13

Direção solicitada pelo usuário: aplicativo local para automações pessoais e profissionais, com perfis de login, gravação reutilizável e execução por lote. SGIND/IQOS são especializações mantidas. O Master Plan anterior continua como histórico; esta mudança não declara etapas anteriores encerradas.

| Entrega | Estado real | Critério de conclusão |
|---|---|---|
| Núcleo React/FastAPI/SQLite/SSE/worker/runtime | Implementado, em validação | Jornada integrada e gates formais |
| Gravador parametrizado e campos no dashboard | Implementado localmente | Fixtures Edge; adaptação dos sites reais pendente |
| Studio: importação e nomes de campos | Implementado, testes/revisão OK | Integração em build local |
| Cadastrar login: perfis e seleção de campos no Edge | Implementado e validado em fixtures | Configuração sem credenciais, processo privado e cancelamento |
| Login genérico efêmero por perfil | Implementado e validado localmente | LoginPOST/cookie/regra explícita; sites reais pendentes |
| Selecionar fluxos e iniciar lote | Implementado; API/UI e testes | Parâmetros separados, transação/idempotência e status individual |
| Paralelismo real por processos | Comprovado em dois processos/Edge locais | Downloads sobrepostos; contas/arquivos separados; cancelarA permiteB concluir |
| Identidade visual Percurso | Aplicada; desktop/mobile inspecionados | Logo do kit, navegação, busca e seleção interativas |
| Workspace prático | Implementado e testado localmente | Grupos de acesso, wizard, campos comuns/override, favoritos, repetição, datas rápidas e resumo |
| Adaptação SGIND/IQOS real | Aguardando computador autorizado | Não abrir gates antes do teste real |
| Distribuição Windows e escala remota | Posterior | Jornada local estabilizada antes da distribuição |

Cada processo continua serial. O supervisor inicia2 processos isolados por padrão (--workers1..4), com capabilities privadas distintas; a evidência de paralelismo vem de downloads simultâneos reais. Ampliar testes de perda/restart/filas longas e adaptar sites reais continuam como próximos trabalhos.

Desenho: [fluxos reutilizáveis](../superpowers/specs/2026-10-12-nexer-reusable-flows-design.md). Credenciais entram somente na execução, sem persistência. Não registrar resultados de fixtures como validação de sites corporativos.

Plano da simplificação: [workspace prático](../superpowers/plans/2026-10-13-practical-workspace.md). Migração0007 necessária na instalação real; prévia de design usa dados sintéticos e não inicia automações.
