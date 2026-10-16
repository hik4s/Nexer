# Nexer — Calendários semânticos e Eye Developer (16/10/2026)

## Objetivo e escopo

Atender à necessidade de RPA generalista: ao clicar no calendário PrimeNG compatível, preservar a **identidade, nome e máscara de data/hora** do campo; no lote e na execução permitir escolher data/hora visualmente e enviar ao portal o mesmo formato do input original. Integrar ao Nexer uma primeira versão realmente funcional do **Eye Developer**, mantendo privacidade, operação local e custo zero.

Não extrapolar para suporte universal de qualquer datepicker, SSO ou site corporativo sem homologação. Não enviar segredo, valor digitado, HTML, screenshot, token, cookies ou dados corporativos a nenhum serviço externo.

## 1. Datas

- `apps/recorder/nexer_recorder/capture.js`: para campos com calendário estrutural, inspeção de `label`, `aria-label`, associação `for` e rótulo contextual `.field-label`. Retira indicadores `*` e `:`. Captura máscaras de **atributos estáticos** (por exemplo `placeholder="dd/mm/yyyy hh:mm:ss"` ou `data-date-format`). Quando há rótulo explícito de data/hora, pode inferir um datetime e sugerir `dd/MM/yyyy HH:mm:ss`. **Nunca lê `input.value` para descobrir máscara**. Se o site não fornece informações suficientes, o usuário revisa formato no editor.
- `apps/runtime/field_schema.py`: acrescenta `site_format` somente para `date`/`datetime-local`, com formatos permitidos e combinação coerente, recusando textos arbitrários; mantém schema v1 compatível.
- `apps/frontend/src/lib/siteDates.ts`: conversão determinística sem `Date.parse` e sem timezone do navegador; valida dia/mês/ano/hora/minuto/segundo e suporta `dd/MM/yyyy`, `dd/MM/yyyy HH:mm`, `dd/MM/yyyy HH:mm:ss`, `yyyy-MM-dd`, `yyyy-MM-dd HH:mm:ss`.
- `apps/frontend/src/components/RecipeField.tsx`: quando a receita contém `field.site_format` suportado, renderiza calendário nativo `type=date` ou `datetime-local` com segundos quando aplicável. Converte **no evento onChange** para o texto aceito pelo site; o backend e o Playwright recebem esse texto como variável string, não o valor ISO do widget. Mostra formato e marca valores anteriores inválidos em vez de arredondar silenciosamente.
- `apps/frontend/src/components/DateFormatEditor.tsx`: configuração guiada do padrão no Studio e na etapa Campos do cadastro; o usuário pode corrigir rótulo e máscara sem alterar JSON.
- `NewBatchPage.tsx`: limpa aviso obsoleto `Preencha input_001` quando o usuário muda um parâmetro, sem pular a revalidação no submit.
- **Fluxos publicados anteriormente** não recebem migração silenciosa. Regravar/passar pelo Studio e publicar **nova versão** é obrigatório para o calendário ficar disponível; o Nexer não deve substituir a receita publicada sem confirmação.

## 2. Eye Developer — primeira versão

- Rota protegida `/developer-eye` em `App.tsx`, na navegação **Ferramentas e ajustes**. Só acessível após autenticação local existente.
- Diagnóstico da API, banco, trabalhadores e últimas execuções com auto-refresh opcional 5s, atualização manual e links para cada execução. Reutiliza APIs do Nexer.
- **Headless**: `POST /developer-eye/probe` em `apps/backend/app/api/developer_eye.py`, com implementação `services/developer_eye.py`. Cria Edge temporário isolado, sem storage/cookies, inspeciona um seletor com prazo limitado, retorna apenas presença/ambiguidade, visibilidade, habilitação e duração. Não devolve texto/URL/conteúdo do DOM; recusa endereços inseguros e destinos com credenciais/query. Protegido pelo middleware de sessão local e origem do Nexer. Sem persistência.
- **Visual (headed)**: reutiliza `/target-pickings`; abre Edge visível em processo isolado, recebe somente o seletor escolhido, permite cancelamento e copia o seletor. Não interfere no worker.
- **Sem promessa enganosa:** modo headless é **sem janela**. A visualização por enquanto inspeciona uma sessão **separada**, não o navegador da execução ativa. Implementar observação de jobs reais requer o próximo bloco: supervisor do worker, controle de novo run visível/headless, consentimento, isolamento dos dados de página, snapshots sob demanda e cancelamento, sem logs de credenciais. Não ativar por padrão em estações empresariais.
- Não há função de executar código arbitrário, shell remoto, exfiltração de DOM nem instalação de plugins desconhecidos a partir dessa aba. Isso mantém o RPA adequado à distribuição a usuários e empresas.

## 3. Critérios de aceite e testes

- TDD gravador Edge: exemplo de início e fim com rótulo HTML/adjacente e `placeholder` estrutural: `apps/recorder/tests/test_capture_edge.py`, com nenhuma data digitada/segredo na receita.
- React: `RecipeField.test.tsx`, `DateFormatEditor.test.tsx`, `DeveloperEyePage.test.tsx` cobrem conversão de formato, calendário e chamadas de APIs reais via mocks.
- Backend: `test_developer_eye.py` cobre sessão, validação estrita de payload, headers `no-store`, autorização e inspeção real de fixture local no Edge (incluindo seletor ambíguo).
- Runtime: `test_calendar_metadata.py` aceita máscaras suportadas e recusa combinações inválidas.
- Gate final antes do deploy: Node/TypeScript, frontend completo, backend completo, gravador com Edge, runtime com Edge e validação do checkout/export; backup com SHA-256; não tocar nas credenciais, SQLite, master ou processos de execução ativos.

## 4. Próxima homologação real

1. Em um novo fluxo ou nova versão, gravar os dois calendários do SGIND (início e fim).
2. Conferir `field.control=datetime-local`, `site_format` e rótulos em Campos/Studio.
3. Publicar nova versão; abrir lote e verificar calendários reais, inserir outro intervalo e revisar o valor que será enviado ao site.
4. Executar *somente após autorização* e verificar no portal que as datas/hora ficaram corretas, que pesquisa terminou e que relatório foi validado.
5. No Eye Developer, conferir estado API/worker e inspecionar um seletor de página *sem credenciais no serviço headless*. Se precisar de login, usar a inspeção visual e autenticar manualmente.

**Status:** implementação em checkout `feat/nexer-guided-artifact-validation-2026-10-16` com modificações preexistentes a preservar. Resultados dos testes e sincronização operacional devem ser acrescentados após verificação; sem commit/push automático.
