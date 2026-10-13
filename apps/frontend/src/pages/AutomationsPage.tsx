import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

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
    case "ARCHIVED":
      return "Arquivada";
    default:
      return status;
  }
}

export function AutomationsPage() {
  const [deleting, setDeleting] = useState<number | null>(null);
  const [feedback, setFeedback] = useState("");
  async function remove(id: number, name: string) {
    if (!window.confirm(`Excluir o fluxo "${name}"? Caso tenha histórico ou rotina associada, ele será arquivado.`)) return;
    setDeleting(id); setFeedback("");
    try {
      const result = await api.deleteAutomation(id);
      await automations.refetch();
      setFeedback(result.archived ? "Fluxo arquivado, mantendo seu histórico." : "Fluxo excluído.");
    } catch (error) {setFeedback(error instanceof Error ? error.message : "Não foi possível excluir o fluxo.");}
    finally {setDeleting(null);}
  }
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
        {feedback ? <p role="status">{feedback}</p> : null}
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
                  {automation.status !== "ARCHIVED" ? <button type="button" className="text-button" disabled={deleting !== null} onClick={() => remove(automation.id, automation.name)}>Excluir fluxo</button> : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
