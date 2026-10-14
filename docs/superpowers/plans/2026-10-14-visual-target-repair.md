# Visual Target Repair Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline and one fresh whole-change review. Track RED/GREEN and decisions in `temp/visual-target-repair/progress.md`.

**Goal:** Selecionar o novo alvo no Edge e revisar o reparo antes de aplicar.

**Architecture:** Sessão privada/backend subprocesso, bundle de seleção estrutural existente, UI associada ao rascunho. Contrato de receita não muda.

**Tech Stack:** Python/unittest, FastAPI, Playwright/Edge, React/TypeScript/Vitest.

**Spec:** `docs/superpowers/specs/2026-10-14-visual-target-repair-design.md`.

## Etapas

- [ ] Contrato puro em `apps/recorder/nexer_recorder/target_contract.py`: `validate_configuration(dict)->dict`, `validate_target(dict)->dict`, allowlist de erros, gramática de `selectors.js`. Testar URL/tipo/extra/seletores seguros/privados; RED antes de implementar.
- [ ] Bundle `target_capture.js`, `target_picker.py`, CLI `scripts/pick_target.py`: `target_script()->str`, `validate_selection(source,event,page,kind)->dict`, `pick_target(configuration,stop_event,on_phase,headless=False)->dict`. Testar real Edge com init bundle, prevenção de efeitos usuais e metadados seguros; validar seleção fora do callback e limpar contexto em finally.
- [ ] Backend: hook `_validate_configuration` preservando default de `LoginRecordings`; `TargetPickings.start_target(owner,url,kind)`, get/cancel, protocolo e erros allowlisted; router `target_pickings.py`, lifespan sweep/close. Configuração e resultados passam pelo contrato puro. Testar owner/TTL/capacidade/término/cancelamento/dados inesperados e API com manager falso; nenhum DB real.
- [ ] Frontend: API tipada, componente de seleção com guard de geração e cancelamento, integração ao editor existente com URL opcional. Resultado somente muda rascunho; novas edições invalidam seleção anterior. Testes de UI em RED antes da implementação, regressões do assistente.
- [ ] Suítes recorder/backend/frontend e regressões runtime/worker conforme imports; TypeScript/build e QA UI 1280/390. Logs em temp ignorado.
- [ ] Revisão independente do diff completo; reproduzir/corrigir achados relevantes e repetir suites afetadas. Documentar, atualizar HANDOFF e commit local. Sem merge/PR/instalação real.

## Restrições e revisão

Sem valores digitados, credenciais ou HTML no protocolo; sem ampliar origens/gates. Main-frame apenas; ação de seleção não executa a receita. Revisar especialmente: evento antes do clique, mudança de documento, resultado tardio após edição/cancelamento/unmount, owner/cancelamento de subprocesso, parser de seletores arbitrários e primeira ação após retorno de preparação.

Standing authorization (“Concedo permissão para tudo”) e direção selecionada pelo usuário usadas para prosseguir sem novos checkpoints de aprovação; decisões permanecem explícitas nesta spec e no relatório. A skill não amplia o escopo para uso corporativo real ou publicação.
