# Arquitetura da nova versão

## Princípio de isolamento
A nova versão não substitui o sistema atual. O código novo fica em `apps/` e evolui por branches próprias.

## Fluxo alvo
React → FastAPI → Worker → Runtime → SQLite, com eventos de execução via SSE.

## Ambiente
O desenvolvimento e os testes compatíveis podem ocorrer em ambiente cloud, mas o runtime de produção permanece local no Windows.
