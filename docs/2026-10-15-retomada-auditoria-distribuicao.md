# Retomada e auditoria de distribuição — 15/10/2026

Base examinada: `b414fbe97f06c3188ed28357dc8f8039ef808412`, da branch remota `feat/nexer-portable-bootstrap-2026-10-14`.
Checkout isolado: `C:/Users/hikas/.codex/worktrees/nexer-distribution-audit/Nexer` (HEAD destacado, gerenciado pelo Codex).
O checkout principal e seus documentos pendentes foram preservados. Nenhum serviço, worker, instalador ou acesso corporativo foi iniciado.

## Achados e evidências

| Prioridade | Achado | Evidência | Próximo aceite |
|---|---|---|---|
| P0 | Banco removido da árvore atual, ainda recuperável do histórico | `git ls-files` não lista banco; `git log --all -- data/nexer.db` inclui a adição histórica e a remoção | Revisão privada dos dados históricos e decisão de saneamento com o responsável; não reescrever histórico automaticamente |
| P1 | Onboarding do instalador diverge da autenticação ativa | `scripts/install_nexer.ps1` exige `setup_auth.py` e chama configuração de usuário/hash; `apps/backend/app/api/auth.py` aceita apenas `pairing_code`; `scripts/run_local.py` emite pareamento | Instalação nova não solicita senha legada; abertura continua com pareamento, loopback e API-only |
| P1 | Pacote da árvore mistura binário legado e arquitetura nova | `git ls-files '*.exe'` lista `Nexer-Atualizado.exe`; o bootstrap usa Python/React | Definir manifesto da distribuição nova e excluir legado desse pacote, preservando fontes/histórico |
| P1 | Login genérico depende de módulos corporativos | `apps/runtime/login_profiles.py` herda de `CorporateBrowserPolicy`; essa classe importa definições corporativas; serviço de perfis contém bloqueio por host específico | Extrair política genérica e manter bloqueios corporativos em camada opcional, sem ampliar permissões |
| P1 | Editor recolhido não comunica fechamento ao picker | `StepReviewEditor.tsx` mantém `TargetEditor` montado dentro de `details`, sem `onToggle` | Reproduzir com resposta pendente; fechar cancela sessão, rejeita retorno tardio e preserva edição manual |

O último item é evidência estática compatível com o bug histórico, não reprodução nesta sessão. O executável legado não foi executado ou auditado internamente. Os dados do banco histórico não foram extraídos nem exibidos. A busca de referências corporativas foi limitada aos caminhos de código, scripts e receitas; não equivale a varredura completa de segredos ou autorização de publicação.

## Verificação executada

No checkout isolado:

```powershell
& 'C:/Users/hikas/Documents/ChatGPT/Nexer/.venv/Scripts/python.exe' tests/test_portable_distribution.py
```

Resultado observado: **5 testes, OK, exit 0, nenhum skip**. Foi utilizado o interpretador existente, sem instalar dependências. Esses testes verificam fontes, exclusões Git e invariantes textuais; não exercitam o instalador interativo nem provam a coerência do onboarding.

`git ls-tree -r HEAD` não apresenta entradas de modo `160000`; não há gitlink na árvore examinada. Nenhum `.env` operacional, banco, PEM ou PFX foi listado pelos filtros de arquivos rastreados usados nesta auditoria. Isso não prova ausência de outros dados sensíveis.

## Primeiro incremento proposto

Mudança delimitada: alinhar o bootstrap ao pareamento já usado pela API. Remover a exigência e a chamada de configuração legada de usuário/senha do instalador, revisar a opção `SkipAuthSetup` e suas referências para manter compatibilidade explícita, e atualizar a documentação de instalação. Preservar guardas de banco existente, migrações, dependências e inicialização API-only. Não remover os utilitários legados de autenticação incidentalmente.

Verificação necessária: teste regressivo comportamental do instalador em sandbox com comandos externos controlados, demonstrando instalação sem prompt de senha, modo sem lançamento e recusa de banco existente sem autorização; regressões do pareamento e os cinco testes de portabilidade. Validação interativa em outra máquina continua pendente.

Depois: reproduzir e corrigir fechamento do picker; definir pacote público e fronteira corporativa; montar E2E sintético UI → API → worker → arquivo → UI. Cada incremento exige evidência própria. Não houve commit, push ou PR nesta retomada.

## Incremento implementado após aprovação

O usuário autorizou o desenho acima com “Continue”. O instalador deixou de exigir e chamar `setup_auth.py`; agora orienta o acesso por pareamento ao abrir. `SkipAuthSetup` permanece aceito, com aviso de obsolescência, equivalendo a `NoLaunch`. Nenhum `.env` existente é alterado por esse ajuste. Documentação de instalação manual e assistida atualizada; utilitários legados preservados.

RED observado: os testes novos falharam em quatro cenários por exigir o script legado, tentar configurar senha e recusar a opção antiga sem lançamento; a proteção do banco existente passou. GREEN observado depois da correção: os cinco cenários passaram. Os testes executam o controle de fluxo PowerShell em árvores temporárias, substituindo a fronteira `Invoke-Checked`, a descoberta de ferramentas, a versão Node, a consulta de portas e o launcher. Não instalam pacotes nem iniciam serviços; o fluxo de criação de venv não foi exercitado.

Regressão encontrada na suíte da pasta `tests`: `test_missing_services_launch_hidden_with_window_pairing` dependia do Vite instalado no checkout. A fixture foi isolada em pasta temporária com launcher copiado e arquivo Vite marcador; nenhum código do launcher mudou. Reexecução: **16 testes, OK, exit 0**, sem skips.

Backend: `unittest discover -s apps/backend/tests -p 'test_*pair*.py' -v`: **20 testes, OK, exit 0**; `unittest discover -s apps/backend/tests -p test_auth_api.py -v`: **3 testes, OK, exit 0**. Houve aviso de depreciação Starlette/httpx. Tentativa inicial de usar pytest não executou testes porque esse módulo não está instalado; foi usado unittest, já adotado pelas suítes. Não se trata da suíte completa de todos os módulos do projeto.

O teste interativo de instalação/pareamento em outra máquina permanece pendente. Os achados de exposição histórica, pacote legado, política corporativa e picker continuam abertos. Sem commit/push/PR ou mudanças em serviços do usuário.
