import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";

type FormValues = {
  name: string;
  automationId: string;
  periodStart: string;
  periodEnd: string;
  sendToNetwork: boolean;
  keepLocalCopy: boolean;
  overwriteExisting: boolean;
  testMode: boolean;
  inputs: string;
};

export function NewExecutionPage() {
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);

  const automations = useQuery({
    queryKey: ["automations", "published"],
    queryFn: () =>
      api.listAutomations({
        status: "PUBLISHED",
        limit: 50,
        offset: 0,
      }),
    retry: false,
  });

  const form = useForm<FormValues>({
    defaultValues: {
      name: "",
      automationId: "",
      periodStart: "",
      periodEnd: "",
      sendToNetwork: false,
      keepLocalCopy: true,
      overwriteExisting: false,
      testMode: true,
      inputs: "{}",
    },
  });

  const mutation = useMutation({
    mutationFn: api.createExecution,
    onSuccess: (execution) => navigate("/executions/" + execution.id),
    onError: (error) =>
      setFormError(
        error instanceof Error ? error.message : "Falha ao criar execução",
      ),
  });

  const onSubmit = form.handleSubmit((values) => {
    setFormError(null);

    if (!values.name.trim()) {
      setFormError("Informe um nome para a execução.");
      return;
    }

    if (!values.automationId) {
      setFormError("Selecione uma automação publicada.");
      return;
    }

    if (
      values.periodStart &&
      values.periodEnd &&
      values.periodStart > values.periodEnd
    ) {
      setFormError("O período inicial deve ser anterior ao final.");
      return;
    }

    let inputs: Record<string, unknown>;
    try {
      inputs = JSON.parse(values.inputs || "{}") as Record<string, unknown>;
      if (
        inputs === null ||
        Array.isArray(inputs) ||
        typeof inputs !== "object"
      ) {
        throw new Error("object required");
      }
    } catch {
      setFormError("Entradas precisam ser um objeto JSON válido.");
      return;
    }

    mutation.mutate({
      name: values.name.trim(),
      automation_ids: [Number(values.automationId)],
      period_start: values.periodStart
        ? values.periodStart + "T00:00:00"
        : undefined,
      period_end: values.periodEnd
        ? values.periodEnd + "T23:59:59"
        : undefined,
      send_to_network: values.sendToNetwork,
      keep_local_copy: values.keepLocalCopy,
      overwrite_existing: values.overwriteExisting,
      test_mode: values.testMode,
      inputs,
    });
  });

  return (
    <main className="page-shell">
      <div className="page-heading">
        <p className="eyebrow">Operação</p>
        <h1>Nova execução</h1>
        <p className="muted">
          Crie uma execução nomeada a partir de uma automação publicada.
        </p>
      </div>

      <section className="card form-card">
        {automations.isLoading ? (
          <p className="muted">Carregando automações publicadas…</p>
        ) : automations.isError ? (
          <div>
            <h2>Não foi possível carregar automações</h2>
            <p className="muted">Confira se a API está disponível.</p>
          </div>
        ) : automations.data?.items.length === 0 ? (
          <div>
            <h2>Nenhuma automação publicada</h2>
            <p className="muted">
              Publique uma automação antes de criar uma execução.
            </p>
          </div>
        ) : (
          <form onSubmit={onSubmit}>
            <label>
              Nome da execução
              <input
                {...form.register("name")}
                placeholder="Relatório de outubro"
              />
            </label>

            <label>
              Automação
              <select {...form.register("automationId")}>
                <option value="">Selecione…</option>
                {automations.data.items.map((automation) => (
                  <option key={automation.id} value={automation.id}>
                    {automation.code} — {automation.name}
                  </option>
                ))}
              </select>
            </label>

            <div className="form-grid">
              <label>
                Período inicial
                <input type="date" {...form.register("periodStart")} />
              </label>
              <label>
                Período final
                <input type="date" {...form.register("periodEnd")} />
              </label>
            </div>

            <label>
              Entradas da receita (JSON)
              <textarea
                {...form.register("inputs")}
                rows={7}
                spellCheck={false}
              />
            </label>

            <div className="checkbox-grid">
              <label className="checkbox-label">
                <input type="checkbox" {...form.register("testMode")} />
                Modo de teste
              </label>
              <label className="checkbox-label">
                <input type="checkbox" {...form.register("keepLocalCopy")} />
                Manter cópia local
              </label>
              <label className="checkbox-label">
                <input type="checkbox" {...form.register("sendToNetwork")} />
                Enviar para rede
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  {...form.register("overwriteExisting")}
                />
                Permitir substituição
              </label>
            </div>

            {formError ? (
              <p className="form-error" role="alert">
                {formError}
              </p>
            ) : null}

            <button
              type="submit"
              className="primary-button"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? "Criando…" : "Criar execução"}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
