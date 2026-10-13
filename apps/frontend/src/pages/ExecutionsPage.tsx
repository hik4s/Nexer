import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useState } from "react";

import { api } from "../lib/api";

const labels: Record<string, string> = {
  QUEUED: "Na fila", RUNNING: "Executando", SUCCEEDED: "Concluída",
  PARTIAL: "Parcial", FAILED: "Falhou", CANCELLED: "Cancelada",
};
const terminal = new Set(["SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED"]);

export function ExecutionsPage() {
  const [view, setView] = useState<"flows" | "batches">("flows");
  const [deleting, setDeleting] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const batches = useQuery({queryKey: ["execution-batches"], queryFn: api.listBatches, enabled: view === "batches", retry: false, refetchInterval: view === "batches" ? 3000 : false});
  const executions = useQuery({
    queryKey: ["executions", { limit: 50 }],
    queryFn: () => api.listExecutions({ limit: 50, offset: 0 }),
    staleTime: 2_000, retry: false,
  });

  async function removeExecution(id: number, name: string) {
    if (!window.confirm(`Excluir o histórico da execução "${name}"? Os arquivos baixados serão preservados. Esta ação não pode ser desfeita.`)) return;
    setDeleting(`execution-${id}`); setFeedback("");
    try {
      await api.deleteExecution(id);
      await executions.refetch();
      setFeedback("Registro de execução excluído. Arquivos preservados.");
    } catch (error) {setFeedback(error instanceof Error ? error.message : "Não foi possível excluir a execução.");}
    finally {setDeleting(null);}
  }

  async function removeBatch(id: number, name: string) {
    if (!window.confirm(`Excluir o lote "${name}" e todos os seus registros de execução? Os arquivos baixados serão preservados. Esta ação não pode ser desfeita.`)) return;
    setDeleting(`batch-${id}`); setFeedback("");
    try {
      await api.deleteBatch(id);
      await Promise.all([batches.refetch(), executions.refetch()]);
      setFeedback("Lote e históricos excluídos. Arquivos preservados.");
    } catch (error) {setFeedback(error instanceof Error ? error.message : "Não foi possível excluir o lote.");}
    finally {setDeleting(null);}
  }

  return (
    <main className="page-shell">
      <div className="page-heading">
        <p className="eyebrow">Histórico</p>
        <h1>Execuções</h1>
        <p className="muted">Acompanhe execuções, etapas e resultados registrados.</p>
      </div>
      <section className="card">
        <div className="button-row">
          <button className={view === "flows" ? "primary-button" : "secondary-button"} onClick={() => setView("flows")}>Execuções individuais</button>
          <button className={view === "batches" ? "primary-button" : "secondary-button"} onClick={() => setView("batches")}>Lotes</button>
        </div>
        {feedback ? <p role="status">{feedback}</p> : null}
        {view === "batches" ? <div className="automation-list">
          {batches.isLoading ? <p>Carregando lotes…</p>
            : batches.isError ? <p role="alert">Não foi possível carregar os lotes.</p>
            : batches.data?.items.length ? batches.data.items.map(batch =>
                <article className="automation-row" key={batch.id}>
                  <div><Link className="text-button" to={`/batches/${batch.id}`}><strong>{batch.name}</strong></Link><p className="muted">{batch.executions.length} fluxos</p></div>
                  <div className="automation-meta">
                    <span className="badge">{labels[batch.status] ?? batch.status}</span>
                    {terminal.has(batch.status) ? <button type="button" className="text-button" disabled={deleting !== null} onClick={() => removeBatch(batch.id, batch.name)}>Excluir lote</button> : null}
                  </div>
                </article>) : <p className="muted">Nenhum lote registrado.</p>}
        </div> : null}
        {view === "flows" ? <>
          {executions.isLoading ? <p className="muted">Carregando execuções…</p>
            : executions.isError ? <p role="alert">Não foi possível carregar o histórico. Confira a API.</p>
            : executions.data?.items.length === 0 ? <p className="muted">Nenhuma execução registrada.</p>
            : <div className="automation-list">
              {executions.data?.items.map(execution =>
                <article className="automation-row" key={execution.id}>
                  <div><Link className="text-button" to={`/executions/${execution.id}`}><strong>{execution.name}</strong></Link><p className="muted">Execução #{execution.id}{execution.batch_id != null ? " · Pertence a um lote" : ""}</p></div>
                  <div className="automation-meta">
                    <span className="badge">{labels[execution.status] ?? execution.status}</span>
                    <span className="version">{execution.items.length} automação(ões)</span>
                    {terminal.has(execution.status) && execution.batch_id == null ? <button type="button" className="text-button" disabled={deleting !== null} onClick={() => removeExecution(execution.id, execution.name)}>Excluir execução</button> : null}
                  </div>
                </article>)}
            </div>}
        </> : null}
      </section>
    </main>
  );
}
