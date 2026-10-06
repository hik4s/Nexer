# Nova arquitetura do RelatPy

Esta árvore pertence à nova versão do RelatPy e é desenvolvida de forma isolada do aplicativo legado existente na raiz.

## Regra de isolamento
- O legado permanece preservado e operacional.
- A nova arquitetura evolui por branches e microtarefas.
- Nenhum arquivo legado é substituído como parte da fundação.
- A integração com o legado só ocorrerá mediante decisão explícita e validação.

## Direção
- frontend: React + TypeScript + Vite
- backend: FastAPI
- worker/runtime: Python
- persistência: SQLite
- eventos: SSE
- automação: Playwright + Edge no runtime Windows
