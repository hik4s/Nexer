# RelatPy — Handoff

Este arquivo existe para permitir que um novo chat retome o desenvolvimento sem depender do histórico da conversa.

## Bootstrap obrigatório

Ao iniciar um novo chat, usar:

> Continue o desenvolvimento do RelatPy a partir do estado atual do repositório `hik4s/RelatPy`. Leia `docs/development/CURRENT_STATE.md`, `HANDOFF.md`, `MASTER_PLAN.md` e consulte o GitHub/Linear/CI. Trabalhe somente na branch de desenvolvimento isolada; não altere o legado em `master`. Siga TDD para código funcional, execute os testes e só registre avanço após verificação real. Retome pelo próximo microtask descrito em CURRENT_STATE e continue até encontrar um bloqueio real.

## Ordem de leitura

1. `MASTER_PLAN.md`
2. `docs/development/CURRENT_STATE.md`
3. `HANDOFF.md`
4. `docs/development/ROADMAP.md`
5. `docs/development/DECISIONS.md`

## Ciclo de cada microtask

```text
entender requisito
    ↓
escrever teste RED
    ↓
implementar mínimo GREEN
    ↓
rodar suíte relevante
    ↓
rodar suíte completa
    ↓
registrar evidência
    ↓
atualizar estado
    ↓
commit/PR
    ↓
próximo microtask
```

## Fonte de verdade

- código: GitHub
- planejamento: Master Plan + Linear
- documentação: `docs/`
- evidência de integração: GitHub Actions + testes reais
- validação Windows/Edge: máquina Windows quando necessária

## Estado atual

O desenvolvimento está na Etapa 1. O backend base, persistência, API de automações/execuções, SSE e o núcleo inicial do Worker já existem. O próximo foco é tornar o Worker executável e construir o Runtime declarativo v1.

## Não fazer

- não substituir o app legado;
- não mover a execução operacional para nuvem;
- não introduzir Kubernetes/Redis/Celery;
- não usar timeout curto arbitrário como solução de resiliência;
- não registrar credenciais/tokens/cookies em logs ou receitas.

## Quando a conversa expirar

Não é necessário reconstruir o histórico. O novo chat deve consultar este arquivo, verificar a branch/CI e continuar pelo próximo item.
