import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";

export function DiagnosticsPage() {
  const diagnostics = useQuery({
    queryKey: ["diagnostics"],
    queryFn: api.getDiagnostics,
    retry: false,
    staleTime: 5_000,
  });

  return (
    <main className="page-shell">
      <div className="page-heading">
        <p className="eyebrow">Ambiente</p>
        <h1>Diagnóstico</h1>
        <p className="muted">Saúde básica da API, banco e workers.</p>
      </div>

      {diagnostics.isLoading ? (
        <section className="card">
          <p className="muted">Verificando ambiente…</p>
        </section>
      ) : diagnostics.isError ? (
        <section className="card">
          <h2>Diagnóstico indisponível</h2>
          <p className="muted">Não foi possível consultar a API.</p>
        </section>
      ) : (
        <div className="grid">
          <section className="card">
            <p className="eyebrow">Aplicação</p>
            <h2>
              {diagnostics.data?.status === "ok" ? "Saudável" : "Degradada"}
            </h2>
            <p className="muted">
              Banco: {diagnostics.data?.database.status}
            </p>
          </section>
          <section className="card">
            <p className="eyebrow">Workers</p>
            <h2>{diagnostics.data?.workers.online} online</h2>
            <p className="muted">
              Total registrado: {diagnostics.data?.workers.total}
            </p>
          </section>
        </div>
      )}
    </main>
  );
}
