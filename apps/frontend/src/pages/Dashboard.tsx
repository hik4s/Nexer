import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import { HealthCard } from "../components/HealthCard";

export function Dashboard() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: api.getHealth,
    staleTime: 15_000,
    retry: false,
  });

  return (
    <main className="page-shell">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Operação local</p>
          <h1>Nexer Dashboard</h1>
          <p className="muted">
            Visão inicial do ambiente e das automações executáveis.
          </p>
        </div>
      </div>

      <div className="grid">
        <HealthCard
          isLoading={health.isLoading}
          isError={health.isError}
          isHealthy={health.data?.status === "ok"}
        />
        <section className="card placeholder-card">
          <p className="eyebrow">Próximo núcleo</p>
          <h2>Execuções</h2>
          <p className="muted">
            Acompanhar fila, andamento, etapas, resultados e evidências em tempo real.
          </p>
        </section>
      </div>
    </main>
  );
}
