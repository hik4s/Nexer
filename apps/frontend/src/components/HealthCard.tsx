type HealthCardProps = {
  isLoading: boolean;
  isError: boolean;
  isHealthy: boolean;
};

export function HealthCard({
  isLoading,
  isError,
  isHealthy,
}: HealthCardProps) {
  let title = "Ambiente saudável";
  let detail = "API operacional";
  let statusClass = "status status--success";

  if (isLoading) {
    title = "Verificando ambiente…";
    detail = "Consultando a Nexer API";
    statusClass = "status status--pending";
  } else if (isError) {
    title = "Não foi possível verificar a API";
    detail = "Confira se o backend FastAPI está em execução.";
    statusClass = "status status--error";
  } else if (!isHealthy) {
    title = "Ambiente indisponível";
    detail = "A API respondeu com um estado inesperado.";
    statusClass = "status status--error";
  }

  return (
    <section className="card health-card" aria-labelledby="health-title">
      <div className={statusClass} aria-hidden="true" />
      <div>
        <p className="eyebrow">Status do ambiente</p>
        <h2 id="health-title">{title}</h2>
        <p className="muted">{detail}</p>
      </div>
    </section>
  );
}
