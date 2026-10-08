import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, type CreateDestinationInput } from "../lib/api";

export function DestinationsPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    code: "",
    name: "",
    path_reference: "",
  });

  const destinations = useQuery({
    queryKey: ["destinations", { limit: 50 }],
    queryFn: () => api.listDestinations({ limit: 50, offset: 0 }),
    retry: false,
  });

  const mutation = useMutation({
    mutationFn: (input: CreateDestinationInput) => api.createDestination(input),
    onSuccess: () => {
      setForm({ code: "", name: "", path_reference: "" });
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["destinations"] });
    },
    onError: (cause) => {
      setError(
        cause instanceof Error ? cause.message : "Não foi possível salvar o destino",
      );
    },
  });

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!form.code.trim() || !form.name.trim() || !form.path_reference.trim()) {
      setError("Preencha código, nome e referência do caminho.");
      return;
    }

    mutation.mutate({
      code: form.code.trim(),
      name: form.name.trim(),
      path_reference: form.path_reference.trim(),
      enabled: true,
    });
  }

  return (
    <main className="page-shell">
      <div className="page-heading">
        <p className="eyebrow">Configuração</p>
        <h1>Destinos</h1>
        <p className="muted">
          Referências de saída para cópias locais e destinos de rede.
        </p>
      </div>

      <div className="grid">
        <section className="card">
          <p className="eyebrow">Cadastro</p>
          <h2>Novo destino</h2>
          <form className="form-card" onSubmit={submit}>
            <label>
              Código
              <input
                value={form.code}
                onChange={(event) =>
                  setForm((current) => ({ ...current, code: event.target.value }))
                }
                placeholder="NETWORK_REPORTS"
              />
            </label>

            <label>
              Nome
              <input
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
                placeholder="Relatórios de rede"
              />
            </label>

            <label>
              Referência do caminho
              <input
                value={form.path_reference}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    path_reference: event.target.value,
                  }))
                }
                placeholder="\\server\reports"
              />
            </label>

            {error ? (
              <p className="form-error" role="alert">{error}</p>
            ) : null}

            <button className="primary-button" type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Salvando…" : "Salvar destino"}
            </button>
          </form>
        </section>

        <section className="card">
          <p className="eyebrow">Registrados</p>
          {destinations.isLoading ? (
            <p className="muted">Carregando destinos…</p>
          ) : destinations.isError ? (
            <p className="muted">Não foi possível carregar os destinos.</p>
          ) : destinations.data?.items.length === 0 ? (
            <div>
              <h2>Nenhum destino cadastrado</h2>
              <p className="muted">Os destinos cadastrados aparecerão aqui.</p>
            </div>
          ) : (
            <div className="automation-list">
              {destinations.data?.items.map((destination) => (
                <article className="automation-row" key={destination.id}>
                  <div>
                    <strong>{destination.code}</strong>
                    <p className="muted">{destination.name}</p>
                    <p className="muted">{destination.path_reference}</p>
                  </div>
                  <span className="badge">
                    {destination.enabled ? "Ativo" : "Desativado"}
                  </span>
                </article>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
