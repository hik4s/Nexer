# Execution artifacts implementation plan

> Execução inline com superpowers:executing-plans; sem subagentes. Usuário autorizou continuidade autônoma.

**Goal:** entregar arquivos validados da execução na interface com vínculo e integridade verificáveis.
**Architecture:** persistência no worker, serviço de leitura confinada na API e componente de histórico; reusar modelo existente.
**Tech Stack:** Python, SQLAlchemy, FastAPI, React, unittest, Vitest e Edge sintético.
**Spec:** `docs/superpowers/specs/2026-10-15-execution-artifacts-design.md`.

## Restrições e revisão

Sem dependências/migrations novas, sem serviços corporativos ou fila real, sem caminhos locais na resposta. Revisar arquivo de outro item, resposta sem autenticação, traversal/link/junction, alteração após validação e resultado cancelado/falho. Testar esses casos nos componentes responsáveis.

## Tarefas

- [x] Escrever testes RED do registro de arquivos e API: sucesso com bytes/checksum, arquivo de outro job, sem sessão, caminho inválido, ausência e alteração. Implementar serviço de artefatos, registro no worker e rotas; executar regressões.
- [x] Escrever teste RED da lista/download na UI. Implementar componente e contrato API; testar frontend e build.
- [x] Exercitar runtime/worker com Edge sintético em diretórios temporários e confirmar registro/download de bytes; documentar limites e testes completos. Revisar diff e preservar alterações em branch própria.

Ledger: ver `docs/2026-10-15-stability-artifacts.md`. Execução inline conforme autorização do usuário; revisão independente por subagente conforme skill requesting-code-review, sem delegação de implementação. Ruling: preservar receitas sem download e dry-run; downloads sem validação falham com orientação explícita, sem inferir validação por mera existência. Custo: o wizard ainda requer revisão manual da validação no Studio.
