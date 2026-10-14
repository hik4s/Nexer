import {downloadErrorMessage} from "../lib/downloadGeneration";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";

import { useExecutionEvents } from "../hooks/useExecutionEvents";
import { api } from "../lib/api";

const labels: Record<string, string> = {
  QUEUED: "Na fila",
  RUNNING: "Executando",
  SUCCEEDED: "Concluída",
  PARTIAL: "Parcial",
  FAILED: "Falhou",
  CANCELLED: "Cancelada",
};

export function ExecutionDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const executionId = Number(params.id);

  const execution = useQuery({
    queryKey: ["execution", executionId],
    queryFn: () => api.getExecution(executionId),
    enabled: Number.isInteger(executionId),
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "QUEUED" || status === "RUNNING" ? 1000 : false;
    },
  });

  const stream = useExecutionEvents(
    Number.isInteger(executionId) ? executionId : null,
  );

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteExecution(id),
    onSuccess: () => navigate("/executions"),
  });
  const cancel = useMutation({
    mutationFn: (id: number) => api.cancelExecution(id),
    onSuccess: () => execution.refetch(),
  });

  if (execution.isLoading) {
    return (
      <main className="page-shell">
        <p className="eyebrow">Acompanhamento</p>
        <h1>Execução</h1>
        <section className="card">
          <p className="muted">Carregando execução…</p>
        </section>
      </main>
    );
  }

  if (execution.isError || !execution.data) {
    return (
      <main className="page-shell">
        <p className="eyebrow">Acompanhamento</p>
        <h1>Execução</h1>
        <section className="card">
          <h2>Execução não encontrada</h2>
          <p className="muted">Não foi possível consultar a execução.</p>
        </section>
      </main>
    );
  }

  const current = execution.data;

  return (
    <main className="page-shell">
      <div className="page-heading">
        <p className="eyebrow">Acompanhamento</p>
        <h1>{current.name}</h1>
        <Link className="secondary-button" to={`/batches/new?repeatExecution=${current.id}`}>Executar novamente</Link>
        <p className="muted">
          Execução #{current.id} · {labels[current.status] ?? current.status}
        </p>
        {current.status === "QUEUED" || current.status === "RUNNING" ? (
          <button
            className="secondary-button"
            type="button"
            onClick={() => cancel.mutate(current.id)}
            disabled={cancel.isPending}
          >
            {cancel.isPending ? "Cancelando…" : "Cancelar execução"}
          </button>
        ) : null}
        {["SUCCEEDED", "FAILED", "PARTIAL", "CANCELLED"].includes(current.status) && current.batch_id == null ? (
          <button type="button" className="secondary-button" disabled={remove.isPending}
            onClick={() => {if (window.confirm(`Excluir o histórico da execução "${current.name}"? Os arquivos baixados serão preservados. Esta ação não pode ser desfeita.`)) remove.mutate(current.id);}}>
            {remove.isPending ? "Excluindo…" : "Excluir execução"}
          </button>
        ) : null}
        {remove.isError ? <p role="alert">{remove.error instanceof Error ? remove.error.message : "Não foi possível excluir a execução."}</p> : null}
      </div>

      <div className="grid">
        <section className="card">
          <p className="eyebrow">Automações</p>
          <div className="execution-items">
            {current.items.map((item) => (
              <div className="execution-item" key={item.id}>
                <div>
                  <strong>Automação #{item.automation_id}</strong>
                  <p className="muted">
                    versão {item.automation_version} · {item.stage}
                  </p>
                  {item.status === "FAILED" ? <p role="status">{downloadErrorMessage(item.error_detail)}</p> : null}
                </div>
                <span className="badge">
                  {labels[item.status] ?? item.status}
                </span>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="event-heading">
            <div>
              <p className="eyebrow">Eventos</p>
              <h2>Tempo real</h2>
            </div>
            <span className="connection">
              {stream.connected ? "Conectado" : "Reconectando"}
            </span>
          </div>

          <div className="event-list" aria-live="polite">
            {stream.events.length === 0 ? (
              <p className="muted">Aguardando eventos…</p>
            ) : (
              stream.events.map((event) => (
                <div className="event-row" key={event.id + "-" + event.type}>
                  <span className="event-id">#{event.id}</span>
                  <div>
                    <strong>{event.type}</strong>
                    <p className="muted">{event.message}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
