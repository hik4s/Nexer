# Nexer — Decisões de Desenvolvimento

## ADR operacional

### 1. Isolamento do legado
A nova arquitetura é desenvolvida em branch(es) própria(s). `master` continua representando a versão funcional anterior até existir uma decisão explícita de migração.

### 2. Runtime local
A operação final permanece local em Windows. Cloud/Codex pode ser usada para desenvolvimento quando compatível, mas não muda o requisito operacional do produto.

### 3. Stack
- frontend: React + TypeScript + Vite
- API: FastAPI
- persistência: SQLite + SQLAlchemy + Alembic
- eventos: SSE
- automação: Playwright + Edge
- worker: processo separado

### 4. TDD
Código funcional novo deve ser precedido por teste que falha pela ausência da implementação esperada.

### 5. Concorrência do Worker
O claim inicial usa transação SQLite com `BEGIN IMMEDIATE` para impedir que dois workers coletem a mesma execução. Uma evolução futura pode adicionar lease/recuperação mais sofisticada sem quebrar o contrato atual.

### 6. Handoff
O estado do projeto deve existir no repositório. A conversa é interface de trabalho, não fonte única de verdade.

### 7. Segurança
Credenciais, cookies, tokens, caminhos corporativos e dados reais não entram no código, fixtures, logs ou documentação pública.


### 8. Direção do produto — 2026-10-12
O usuário solicitou Nexer focado em automações, cadastro de perfis de login e gravação de fluxos reutilizáveis, atendendo uso pessoal e profissional. Confirmou iniciar vários fluxos por lote com acompanhamento/cancelamento individual. Perfis armazenam configuração dos campos; credenciais são informadas na execução e permanecem efêmeras. A implementação deve preservar especializações e gates de SGIND/IQOS. Paralelismo por processos isolados é a proposta técnica; não declarar pronto o loop serial atual. Desenho e critérios estão em docs/superpowers/specs/2026-10-12-nexer-reusable-flows-design.md.
