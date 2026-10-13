import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, Execution } from "../lib/api";
import { useExecutionEvents } from "../hooks/useExecutionEvents";
const terminal = new Set(["SUCCEEDED", "FAILED", "PARTIAL", "CANCELLED"]);

function FlowProgress({execution, cancelling, cancel}: {execution: Execution; cancelling: boolean; cancel: () => void}) {
  const {events, connected} = useExecutionEvents(terminal.has(execution.status) ? null : execution.id);
  const latest = events.at(-1);
  return <section className="card"><h2>{execution.name}</h2><p>Status: {execution.status}</p>
    {execution.items.map(item => <p key={item.id}>Etapa: {item.stage || "Aguardando"} · {item.status}</p>)}
    {latest ? <p role="status">{latest.message}</p> : null}
    {!terminal.has(execution.status) ? <p className="muted">{connected ? "Eventos conectados" : "Atualizando acompanhamento…"}</p> : null}
    <Link to={`/executions/${execution.id}`}>Ver execução e eventos</Link><button className="secondary-button" disabled={cancelling || terminal.has(execution.status) || execution.cancel_requested} onClick={cancel}>Cancelar fluxo {execution.id}</button>
  </section>;
}

export function BatchDetailPage() {
  const {id} = useParams();
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState<number | "all" | null>(null);
  const batch = useQuery({queryKey: ["batch", id], queryFn: () => api.getBatch(Number(id)), refetchInterval: query => terminal.has(query.state.data?.status ?? "") ? false : 1000});
  async function cancel(executionId?: number) {
    setCancelling(executionId ?? "all"); setError("");
    try {if (executionId) await api.cancelExecution(executionId); else await api.cancelBatch(Number(id)); await batch.refetch();}
    catch {setError("Não foi possível solicitar o cancelamento.");}
    finally {setCancelling(null);}
  }
  return <main className="page-shell"><h1>{batch.data?.name ?? "Lote"}</h1>
    {batch.isError ? <p role="alert">Não foi possível carregar o lote.</p> : null}
    {batch.data ? <><p>Status do lote: {batch.data.status}</p><button className="secondary-button" disabled={cancelling !== null || terminal.has(batch.data.status)} onClick={() => cancel()}>Cancelar lote</button>
      <Link className="secondary-button" to={`/batches/new?repeat=${batch.data.id}`}>Executar novamente</Link>
      <div className="grid">{batch.data.executions.map(execution => <FlowProgress key={execution.id} execution={execution} cancelling={cancelling !== null} cancel={() => cancel(execution.id)} />)}</div></> : <p>Carregando lote…</p>}
    {error ? <p role="alert">{error}</p> : null}</main>;
}
