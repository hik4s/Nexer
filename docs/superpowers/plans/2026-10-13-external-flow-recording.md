# Gravar fluxos HTTPS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement task-by-task.

**Goal:** Gravar fluxos HTTPS.
**Architecture:** URLs compartilhadas + preparo/captura via processo privado.
**Tech Stack:** Python/FastAPI/SQLite/Playwright/Edge; React/TypeScript/Vite.
**Spec:** ../specs/2026-10-13-https-pairing-delete-design.md

## Global Constraints

- Melhorias reversíveis autorizadas pelo usuário; sem commits/worktrees nesta cópia sem `.git`.
- Nunca persistir/ecoar credenciais ou token HTTP; preservar SQLite histórico e código anterior.
- API local em127.0.0.1, origens frontend5173, token5min/uso único.
- Runtime corporativo segue validação separada; gravação não comprova execução.

## Review Focus

URL hash preservada; preparação não emite; cancelamento/EOF e finish prematuro; origem/redirect; password visível bloqueia início

## Task: Gravar fluxos HTTPS

**Files:** apps/runtime/site_urls.py; apps/backend/app/schemas_login_profile.py; scripts/record_recipe.py; scripts/record_flow.py; apps/recorder/nexer_recorder/capture.js; apps/backend/app/services/flow_recordings.py; apps/backend/app/api/workspace.py; apps/frontend/src/lib/practical.ts; apps/frontend/src/pages/NewFlowPage.tsx
**Interfaces:** validate_site_url(value) -> str; site_origin(value) -> (scheme,hostname,port); FlowRecording.phase PREPARING/RECORDING; mensagem privada started antes de done

- [x] Escrever regressões do comportamento e observar falha antes de implementação.
- [x] Implementar somente a fronteira necessária, preservando contratos existentes.
- [x] Executar testes focados (unittest do backend/gravador, vitest página/helper); observar GREEN.
- [x] Revisar integração/segredos e executar suites/build pertinentes; atualizar estado/handoff.

Commit não disponível: pasta extraída sem `.git`; não inicializar repositório artificial.

## Registro final

Backend130 OK/13skips; gravador22 Edge OK; runtime113 OK/10skips; frontend65/19arquivos OK com testTimeout30000; fixtures do wizard3/3 e build TypeScript/Vite OK após correção de tipos; protocolo privado1/1; preparação real SGIND HTTP200 e cancelamento sem receita/credenciais.
Ruling: código de pareamento somente no console — preserva a autenticação local — exige copiar na tela.
Ruling: exclusão vinculada recusada — mantém receitas/histórico — usuário pode desativar.
Ruling: preparar HTTPS manualmente antes de capturar — não armazenar credenciais — autenticação automatizada permanece etapa separada.
