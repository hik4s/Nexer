import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api, type Automation } from "../lib/api";

const DEFAULT_RECIPE = {
  schema_version: 1,
  name: "Nova receita",
  variables: {
    base_url: "https://example.invalid",
  },
  steps: [
    {
      id: "open",
      action: "navigate",
      url: "{{base_url}}",
    },
  ],
  output: {
    type: "file",
    filename: "resultado",
    expected_extension: ".csv",
  },
};

export function StudioPage() {
  const [selected, setSelected] = useState<Automation | null>(null);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [recipeText, setRecipeText] = useState(
    JSON.stringify(DEFAULT_RECIPE, null, 2),
  );
  const [version, setVersion] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const automations = useQuery({
    queryKey: ["automations", "studio"],
    queryFn: () => api.listAutomations({ limit: 50, offset: 0 }),
    retry: false,
  });

  const createAutomation = useMutation({
    mutationFn: (input: Parameters<typeof api.createAutomation>[0]) =>
      api.createAutomation(input),
    onSuccess: (automation) => {
      setSelected(automation);
      setVersion(null);
      setStatus("Automação criada.");
      setFormError(null);
      void automations.refetch();
    },
    onError: (error) =>
      setFormError(error instanceof Error ? error.message : "Falha ao criar automação."),
  });

  const saveVersion = useMutation({
    mutationFn: ({ automationId, recipe }: { automationId: number; recipe: Record<string, unknown> }) =>
      api.createAutomationVersion(automationId, recipe),
    onSuccess: (created) => {
      setVersion(created.version);
      setStatus(`Versão v${created.version} salva.`);
      setFormError(null);
    },
    onError: (error) =>
      setFormError(error instanceof Error ? error.message : "Falha ao salvar versão."),
  });

  const testVersion = useMutation({
    mutationFn: ({ automationId, version: currentVersion }: { automationId: number; version: number }) =>
      api.testAutomationVersion(automationId, currentVersion),
    onSuccess: (result) => {
      setStatus(`Versão v${result.version} testada: ${result.test_status}.`);
      setFormError(null);
    },
    onError: (error) =>
      setFormError(error instanceof Error ? error.message : "Falha ao testar versão."),
  });

  const publishVersion = useMutation({
    mutationFn: ({ automationId, version: currentVersion }: { automationId: number; version: number }) =>
      api.publishAutomationVersion(automationId, currentVersion),
    onSuccess: () => {
      setStatus("Versão publicada.");
      setFormError(null);
      void automations.refetch();
    },
    onError: (error) =>
      setFormError(error instanceof Error ? error.message : "Falha ao publicar versão."),
  });

  function selectAutomation(automation: Automation) {
    setSelected(automation);
    setVersion(automation.current_version);
    setStatus(null);
    setFormError(null);
  }

  function create() {
    setFormError(null);
    if (!code.trim() || !name.trim()) {
      setFormError("Informe código e nome da automação.");
      return;
    }

    createAutomation.mutate({
      code: code.trim(),
      name: name.trim(),
      description: undefined,
      system: undefined,
    });
  }

  function save() {
    if (!selected) {
      setFormError("Selecione ou crie uma automação primeiro.");
      return;
    }

    try {
      const recipe = JSON.parse(recipeText) as Record<string, unknown>;
      if (
        recipe === null ||
        Array.isArray(recipe) ||
        typeof recipe !== "object"
      ) {
        throw new Error("object required");
      }
      saveVersion.mutate({ automationId: selected.id, recipe });
    } catch {
      setFormError("A receita precisa ser um objeto JSON válido.");
    }
  }

  const busy =
    createAutomation.isPending ||
    saveVersion.isPending ||
    testVersion.isPending ||
    publishVersion.isPending;

  return (
    <main className="page-shell">
      <div className="page-heading">
        <p className="eyebrow">Construção</p>
        <h1>Studio</h1>
        <p className="muted">
          Crie e versione receitas declarativas sem colocar credenciais no arquivo.
        </p>
      </div>

      <section className="card">
        <h2>Nova automação</h2>
        <div className="form-grid">
          <label>
            Código
            <input
              aria-label="Código"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="RELATORIO"
            />
          </label>
          <label>
            Nome
            <input
              aria-label="Nome"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="Relatório mensal"
            />
          </label>
        </div>
        <button
          type="button"
          className="primary-button"
          disabled={busy}
          onClick={create}
        >
          Criar automação
        </button>
      </section>

      <section className="card">
        <h2>Automação</h2>
        {automations.isLoading ? (
          <p className="muted">Carregando automações…</p>
        ) : automations.isError ? (
          <p className="form-error">Não foi possível carregar as automações.</p>
        ) : (
          <div className="automation-list">
            {(automations.data?.items ?? []).map((automation) => (
              <button
                type="button"
                className="automation-row"
                key={automation.id}
                onClick={() => selectAutomation(automation)}
              >
                <span>
                  <strong>{automation.code}</strong>
                  <small className="muted">{automation.name}</small>
                </span>
                <span className="badge">{automation.status}</span>
              </button>
            ))}
          </div>
        )}
        {selected ? (
          <p className="muted">
            Editando <strong>{selected.code}</strong>
            {version ? ` · v${version}` : " · sem versão publicada"}
          </p>
        ) : (
          <p className="muted">Selecione uma automação para editar a receita.</p>
        )}
      </section>

      <section className="card form-card">
        <h2>Receita declarativa</h2>
        <p className="muted">
          Use apenas referências como <code>credential_ref</code>; segredos reais não pertencem à receita.
        </p>
        <label>
          JSON da receita
          <textarea
            aria-label="JSON da receita"
            value={recipeText}
            onChange={(event) => setRecipeText(event.target.value)}
            rows={22}
            spellCheck={false}
          />
        </label>

        {formError ? <p className="form-error" role="alert">{formError}</p> : null}
        {status ? <p role="status">{status}</p> : null}

        <div className="button-row">
          <button type="button" className="primary-button" disabled={busy || !selected} onClick={save}>
            {saveVersion.isPending ? "Salvando…" : "Salvar versão"}
          </button>
          <button
            type="button"
            disabled={busy || !selected || version == null}
            onClick={() => testVersion.mutate({ automationId: selected!.id, version: version! })}
          >
            {testVersion.isPending ? "Testando…" : "Testar versão"}
          </button>
          <button
            type="button"
            disabled={busy || !selected || version == null}
            onClick={() => publishVersion.mutate({ automationId: selected!.id, version: version! })}
          >
            {publishVersion.isPending ? "Publicando…" : "Publicar versão"}
          </button>
        </div>
      </section>
    </main>
  );
}
