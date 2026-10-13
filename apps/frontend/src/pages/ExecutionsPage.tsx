import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {useState} from "react";

import { api } from "../lib/api";

const labels: Record<string, string> = {
  QUEUED: "Na fila",
  RUNNING: "Executando",
  SUCCEEDED: "Concluída",
  PARTIAL: "Parcial",
  FAILED: "Falhou",
  CANCELLED: "Cancelada",
};

export function ExecutionsPage() {
  const [view, setView] = useState<"flows" | "batches">("flows");
  const batches = useQuery({queryKey: ["execution-batches"], queryFn: api.listBatches, enabled: view === "batches", retry: false, refetchInterval: view === "batches" ? 3000 : false});
  const executions = useQuery({
    queryKey: ["executions", { limit: 50 }],
    queryFn: () => api.listExecutions({ limit: 50, offset: 0 }),
    staleTime: 2_000,
    retry: false,
  });

  return (
    <main className="page-shell">
      <div className="page-heading">
        <p className="eyebrow">Histórico</p>
        <h1>Execuções</h1>
        <p className="muted">
          Acompanhe execuções, etapas e resultados registrados.
        </p>
      </div>

      <section className="card">
        <div className="button-row"><button className={view === "flows" ? "primary-button" : "secondary-button"} onClick={() => setView("flows")}>Execuções individuais</button><button className={view === "batches" ? "primary-button" : "secondary-button"} onClick={() => setView("batches")}>Lotes</button></div>
        {view === "batches" ? <div className="automation-list">{batches.isLoading ? <p>Carregando lotes…</p> : batches.isError ? <p role="alert">Não foi possível carregar os lotes.</p> : batches.data?.items.length ? batches.data.items.map(batch => <Link className="automation-row" to={`/batches/${batch.id}`} key={batch.id}><div><strong>{batch.name}</strong><p className="muted">{batch.executions.length} fluxos</p></div><span className="badge">{labels[batch.status] ?? batch.status}</span></Link>) : <p className="muted">Nenhum lote registrado.</p>}</div> : null}
        {view === "flows" ? <>
        {executions.isLoading ? (
          <p className="muted">Carregando execuções…</p>
        ) : executions.isError ? (
          <div>
            <h2>Não foi possível carregar o histórico</h2>
            <p className="muted">Confira se a API está disponível.</p>
          </div>
        ) : executions.data?.items.length === 0 ? (
          <div>
            <h2>Nenhuma execução registrada</h2>
            <p className="muted">As novas execuções aparecerão aqui.</p>
          </div>
        ) : (
          <div className="automation-list">
            {executions.data?.items.map((execution) => (
              <Link
                className="automation-row automation-row--link"
                to={"/executions/" + execution.id}
                key={execution.id}
              >
                <div>
                  <strong>{execution.name}</strong>
                  <p className="muted">Execução #{execution.id}</p>
                </div>
                <div className="automation-meta">
                  <span className="badge">
                    {labels[execution.status] ?? execution.status}
                  </span>
                  <span className="version">
                    {execution.items.length} automação(ões)
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
        </> : null}</section>
    </main>
  );
}
