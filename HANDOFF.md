# Handoff — Nexer — 2026-10-13

## Retomar no próximo chat

Leia este arquivo primeiro e depois `CONTINUAR_NEXER_2026-10-13.md`, `docs/development/CURRENT_STATE.md` e os planos em `docs/superpowers/plans/`. Este handoff prevalece sobre referências históricas a alterações ainda não commitadas: o usuário solicitou salvar o checkpoint completo, dar commit e push em uma branch nova.

- Repositório: https://github.com/hik4s/Nexer
- Branch deste checkpoint: `codex/nexer-reusable-flows-2026-10-13`.
- Origem: HEAD `4f7e73c` da branch `feat/etapa1-foundation`, incluindo as alterações locais acumuladas das últimas sessões.
- Workspace: `C:\Users\hikas\Documents\ChatGPT\Nexer`; Windows/PowerShell, timezone America/Sao_Paulo.
- A branch original e o legado são preservados. Não houve merge para main, reset ou exclusão dos arquivos anteriores. A nova branch isola a publicação; não garante ausência de conflitos em um merge futuro.
- O usuário autorizou implementar melhorias reversíveis sem pedir novamente permissão e autorizou explicitamente este commit/push. Não confundir autorização de desenvolvimento com disponibilidade de credenciais ou rede corporativa.

## Objetivo do produto

Nexer deve ser um aplicativo simples e escalável de automações, útil também fora do ambiente empresarial. Pilares: cadastrar configurações de login por site, gravar fluxos reutilizáveis no Edge, personalizar os parâmetros em cada execução e selecionar vários fluxos para iniciar um lote com progresso/cancelamento individuais. Identidade minimalista com os ativos originais de `nexer-logo-kit`.

Requisitos confirmados:

- Gravar locais e ações; nunca persistir os valores digitados ou a seleção usada na gravação como defaults.
- Data inicial/final, empresa e demais campos aparecem com seus tipos e regras no dashboard. As opções de listas são carregadas do site ao preparar a execução, não copiadas da gravação.
- Nomes dos campos vêm dos rótulos da página e podem ser revisados depois de gravar.
- Compartilhar o preenchimento de credenciais entre destinos do mesmo grupo; cada destino mantém configuração e sessão próprias.
- Nomes de downloads mudam entre execuções: usuário escolheu padrão configurável. Procurar de cima para baixo na central do site e baixar a primeira correspondência, preservando o nome atual do arquivo recebido do site.
- Validação SGIND/IQOS será em outro computador com acesso à rede corporativa.

## Implementado neste checkpoint

Arquitetura: React/TypeScript/Vite → FastAPI/SQLite/Alembic/SSE → supervisor com processos de worker independentes → Playwright/Edge. Legado Streamlit preservado.

1. Perfis de login versionados, seleção de três alvos no Edge, sucesso por URL/marcador e credenciais efêmeras. Grupos de acessos para vários destinos; template reaproveita alvos, sem copiar regra de sucesso/origins. Credenciais fora de receitas, banco, eventos e cache de consultas.
2. Gravação parametrizada: cliques, preenchimentos, controles nativos e alguns personalizados, scroll/hover/drag, frames de mesma origem, shadow DOM aberto e abas do fluxo. Inputs viram placeholders, sem valores da gravação.
3. Cadastro guiado Site → Acesso → Gravação → Campos → Publicar, importação de JSON e edição de labels no Studio. Publicar não inicia execução.
4. Toolbar **Parar gravação** na página principal do Edge; conclusão por binding privado, toolbar excluída da receita. Interface segue automaticamente para Campos após DONE. Somente controles efetivamente editados geram parâmetros; nomes vêm de label/aria-labelledby/aria-label/legend. `base_url` é configuração separada de Site.
5. Downloads em tabelas/listas identificáveis registram `collection: {rows, name, button, pattern}`. Padrão glob solicitado na nova execução, ex.: `Relatorio_*.xlsx`. Nenhum nome/conteúdo de arquivo usado na gravação é copiado. Runtime escolhe primeira linha visível correspondente na ordem do DOM, aguarda até timeout, respeita cancelamento, falha sem correspondência e preserva `suggested_filename`. Impede sobrescrever arquivo já salvo na mesma execução.
6. Lotes atômicos/idempotentes, até 20 itens, processos independentes (supervisor padrão 2, configurável 1–4), isolamento de sessões/downloads, cancelamento individual e do lote. Worker perdido não reassocia credenciais.
7. Meus fluxos/Acessos/Execuções; identidade do kit; busca/seleção de fluxos, favoritos, repetição de execução/lote, parâmetros comuns compatíveis, datas rápidas e resumo antes da confirmação. Listas comuns usam interseção das opções atuais por valor e label; mudar período limpa escolhas dependentes.

Arquivos centrais:

- UI: `apps/frontend/src/pages/{Dashboard,NewFlowPage,NewBatchPage,LoginProfilesPage,StudioPage}.tsx`; `components/RecipeField.tsx`; `lib/practical.ts`.
- Gravação: `scripts/record_recipe.py`, `scripts/record_flow.py`, `apps/recorder/nexer_recorder/{capture.js,compiler.py}`; serviço `apps/backend/app/services/flow_recordings.py`.
- Downloads: `apps/runtime/actions.py` e `apps/runtime/recipe.py`.
- Perfis/lotes: APIs `apps/backend/app/api/{login_profiles,execution_batches,workspace}.py`; supervisor `scripts/run_local.py`.
- Migrações novas: `0004_login_profiles`, `0005_execution_login_profiles`, `0006_execution_batches`, `0007_practical_workspace`.
- Referências de produto e evidência: `apps/recorder/README.md`, `docs/development/VISUAL_IDENTITY.md`, arquivo de continuidade.

## Próximas melhorias aprovadas para planejamento

Estas seis propostas foram aceitas pelo usuário ao pedir salvar o contexto. **Ainda não foram implementadas**. Prioridade recomendada: 1 e 2.

1. **Gravar sites externos autorizados.** Expandir do HTTP local para HTTPS com política explícita de origens, navegação/redirects/popups e cancelamento seguros. Validar em sites reais fornecidos pelo usuário antes de prometer compatibilidade. Perfis HTTPS existentes não tornam o gravador compatível com qualquer site.
2. **Revisão simples após gravar.** Mostrar nomes e tipos legíveis (Data inicial — data; Empresa — lista), sequência compreensível de ações e deixar identificadores/seletores em Avançado. Hoje o editor ainda expõe `input_001` e os detalhes de seletores.
3. **Verificar padrão de download antes de baixar.** Botão “Verificar arquivo correspondente” mostra o item que seria escolhido na central, sem disparar download. Respeitar acesso efêmero e não persistir conteúdo/credenciais inadvertidamente. Hoje existe seleção por padrão somente durante execução.
4. **Obrigatoriedade e dependências mais claras.** Mensagens como “Escolha a empresa para carregar as regionais”, conservando tipos/regras do site. Hoje regras e invalidação de listas existem, mas explicação explícita de dependências pode melhorar.
5. **Erros com solução e regravação de etapa.** Identificar alvo alterado e permitir “Regravar esta etapa” sem refazer o fluxo inteiro. Hoje não existe reparo seletivo da gravação.
6. **Reexecutar apenas falhas de um lote.** Preparar somente itens que falharam, permitir correção de parâmetros e pedir credenciais novas. Hoje há repetição de execução/lote, mas não este atalho específico.

## Limites e usabilidade real

- Núcleo funcional em testes locais; não declarar pronto para produção ou compatível com todos os sites.
- Gravador direto ainda aceita somente HTTP loopback, sem query/fragment/credenciais na URL. Sites externos exigem expansão controlada/adaptação; receita preparada pode ser importada.
- Gates SGIND/IQOS continuam fechados. Não há validação corporativa nesta máquina.
- O banco real não foi migrado e nenhuma fila real foi iniciada na última rodada. Aplicar migrações na instalação real antes de uso; validar configuração existente e preservar dados.
- Prévia `http://127.0.0.1:4173` é somente visual, com dados de exemplo. POSTs de mutação bloqueados; consulta de opções devolve catálogo sintético. Não é backend/workers reais. Servidor ignorado `temp/preview_identity.py`, último PID observado 5448; confirmar se ainda existe antes de operar e nunca encerrar processos genéricos do Edge.
- Centrais devem ordenar os mais recentes primeiro: runtime segue ordem do DOM, sem ordenar por timestamp. Estruturas particulares ou nome fora da primeira coluna exigem revisar seletores. Não instrumenta a interface de downloads do próprio Edge.
- Downloads espontâneos/sem controle identificado, uploads, canvas, shadow fechado, frames de outra origem, MFA/CAPTCHA e componentes particulares não têm cobertura universal. Controles Baixar/Download, links `download` ou seletores declarados são reconhecidos.
- Validação de receita no Studio é estrutural; não comprova execução real no site.
- Distribuição final/Nexer.exe não foi atualizada nem validada nesta rodada.

## Evidência mais recente

- Frontend: **50 testes em 17 arquivos**, build TypeScript/Vite passou.
- Recorder: **19 testes com Edge opt-in**, todos passaram; rótulos, canários ausentes, toolbar, downloads em tabela/lista e replay com valores novos.
- Runtime: **109 testes**, OK, 10 skips de cenários opt-in.
- Backend: **112 testes**, OK, 13 skips; migrações verificadas em bancos temporários.
- Protocolo privado de gravação: **2 testes**, incluindo Edge real finalizando pela toolbar, passaram.
- Evidência anterior ainda válida: worker32/1skip; contenção Windows4; dois workers reais com downloads simultâneos, cancelamento individual e sessões isoladas.
- QA desktop/mobile: campos e configuração de central sem overflow/erros. Artefatos ignorados em `temp/recording-fields-*.png` e `temp/practical-*.png`.
- Revisões independentes corrigidas com regressões RED→GREEN: compatibilidade antes de todas receitas carregarem; resumo obsoleto por controles programáticos; texto Baixar contaminando nome em listas. Não repetir revisão apenas para confirmar correções já testadas.
- `git diff --check` passou. Patch cumulativo local `temp/NEXER_PATCH_2026-10-13.patch` regenerado e validado por reverse check; não vai ao Git por ser artefato ignorado.

Comandos úteis na raiz (sem instalar dependências novamente se já presentes):

```powershell
$env:PYTHONPATH='apps/runtime;apps/recorder'
$env:NEXER_RUN_RECORDER_E2E='1'
.venv/Scripts/python.exe -m unittest discover -s apps/recorder/tests
.venv/Scripts/python.exe -m unittest discover -s apps/runtime/tests

$env:PYTHONPATH='apps/backend;apps/runtime;apps/worker'
$env:NEXER_ENVIRONMENT='test'
Remove-Item Env:NEXER_RUN_RECORDER_E2E -ErrorAction SilentlyContinue
.venv/Scripts/python.exe -m unittest discover -s apps/backend/tests

Push-Location apps/frontend
npm test
npm run build
Pop-Location
```

## Como continuar

Inspecionar a branch/estado antes de editar; preservar o checkpoint e o legado. Começar pelo suporte a gravação de sites externos e simplificação da revisão, seguindo os requisitos acima. Pedir apenas URLs/informações realmente ausentes; não repetir perguntas já respondidas sobre opções, tipos, lotes ou padrões de nomes. Atualizar este handoff com decisões, novas evidências e limites; não marcar o projeto inteiro ou etapa corporativa concluídos por haver apenas testes locais verdes.
