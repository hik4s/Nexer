import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";

function statusLabel(status: string) {
  switch (status) {
    case "PUBLISHED":
      return "Publicada";
    case "DRAFT":
      return "Rascunho";
    case "TESTING":
      return "Em teste";
    case "BROKEN":
      return "Com erro";
    case "DISABLED":
      return "Desativada";
    default:
      return status;
  }
}

export function AutomationsPage() {
  const automations = useQuery({
    queryKey: ["automations", { limit: 50 }],
    queryFn: () => api.listAutomations({ limit: 50, offset: 0 }),
    staleTime: 10_000,
    retry: false,
  });

  if (automations.isLoading) {
    return (
      <main className="page-shell">
        <p className="eyebrow">Catálogo</p>
        <h1>Automações</h1>
        <section className="card">
          <p className="muted">Carregando automações…</p>
        </section>
      </main>
    );
  }

  if (automations.isError) {
    return (
      <main className="page-shell">
        <p className="eyebrow">Catálogo</p>
        <h1>Automações</h1>
        <section className="card">
          <h2>Não foi possível carregar as automações</h2>
          <p className="muted">Confira se a API está disponível.</p>
        </section>
      </main>
    );
  }

  const items = automations.data?.items ?? [];

  return (
    <main className="page-shell">
      <div className="page-heading">
        <p className="eyebrow">Catálogo</p>
        <h1>Automações</h1>
        <p className="muted">
          Receitas versionadas prontas para teste e execução.
        </p>
      </div>

      <section className="card">
        {items.length === 0 ? (
          <div>
            <h2>Nenhuma automação cadastrada</h2>
            <p className="muted">
              Crie uma automação para começar a montar uma receita.
            </p>
          </div>
        ) : (
          <div className="automation-list">
            {items.map((automation) => (
              <article className="automation-row" key={automation.id}>
                <div>
                  <strong>{automation.code}</strong>
                  <p className="muted">{automation.name}</p>
                </div>
                <div className="automation-meta">
                  <span className="badge">{statusLabel(automation.status)}</span>
                  <span className="version">
                    {automation.current_version ? `v${automation.current_version}` : "Sem versão"}
                  </span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
