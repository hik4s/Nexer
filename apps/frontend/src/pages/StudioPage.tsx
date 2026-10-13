import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api, type Automation } from "../lib/api";
import { parameterLabel, type ParameterDeclaration } from "../components/RecipeField";

const DEFAULT_RECIPE = {
  schema_version: 1,
  name: "Nova receita",
  variables: {
    base_url: { type: "string", required: true },
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
  const editorRevision = useRef(0);
  const [loadingRecipe, setLoadingRecipe] = useState(false);
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
  const loginProfiles = useQuery({queryKey: ["login-profiles"], queryFn: api.listLoginProfiles, retry: false});

  const createAutomation = useMutation({
    mutationFn: (input: Parameters<typeof api.createAutomation>[0]) =>
      api.createAutomation(input),
    onSuccess: (automation) => {
      editorRevision.current++;
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
    mutationFn: ({ automationId, recipe }: { automationId: number; recipe: Record<string, unknown>; revision: number }) =>
      api.createAutomationVersion(automationId, recipe),
    onSuccess: (created, variables) => {
      if (variables.revision !== editorRevision.current) return;
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

  function editRecipe(text: string) {
    editorRevision.current++;
    setRecipeText(text);
    setVersion(null);
    setStatus(null);
    setFormError(null);
  }

  async function selectAutomation(automation: Automation) {
    const revision = ++editorRevision.current;
    setSelected(automation);
    setVersion(null);
    setStatus(null);
    setFormError(null);
    setRecipeText(JSON.stringify(DEFAULT_RECIPE, null, 2));
    if (automation.current_version == null) {setLoadingRecipe(false); return;}
    setLoadingRecipe(true);
    setRecipeText("");
    try {
      const saved = await api.getAutomationVersion(automation.id, automation.current_version);
      if (revision !== editorRevision.current) return;
      setRecipeText(JSON.stringify(saved.recipe, null, 2));
      setVersion(saved.version);
    } catch {
      if (revision === editorRevision.current) setFormError("Não foi possível carregar a receita selecionada. Tente selecionar o relatório novamente.");
    } finally {
      if (revision === editorRevision.current) setLoadingRecipe(false);
    }
  }

  async function importRecording(file: File | undefined) {
    if (!file) return;
    setStatus(null);
    setFormError(null);
    const revision = ++editorRevision.current;
    try {
      if (file.size > 1024 * 1024) throw new Error();
      const text = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(new Error());
        reader.readAsText(file);
      });
      const recipe: unknown = JSON.parse(text);
      if (!recipe || typeof recipe !== "object" || Array.isArray(recipe)) throw new Error();
      const candidate = recipe as Record<string, unknown>;
      if (candidate.schema_version !== 1 || !Array.isArray(candidate.steps) || !candidate.steps.length || !candidate.variables || typeof candidate.variables !== "object" || Array.isArray(candidate.variables)) throw new Error();
      if (revision !== editorRevision.current) return;
      editRecipe(JSON.stringify(recipe, null, 2));
      setStatus("Gravação importada. Revise os campos e salve uma nova versão.");
    } catch {
      if (revision === editorRevision.current) setFormError("Não foi possível importar. Use uma receita JSON v1 válida de até 1 MB.");
    }
  }

  let parameters: [string, ParameterDeclaration][] = [];
  let selectedProfile = "";
  try {
    const parsed = JSON.parse(recipeText);
    if (parsed?.login_profile?.id && parsed?.login_profile?.version) selectedProfile = `${parsed.login_profile.id}:${parsed.login_profile.version}`;
    if (parsed?.variables && typeof parsed.variables === "object" && !Array.isArray(parsed.variables)) {
      parameters = Object.entries(parsed.variables).filter((entry): entry is [string, ParameterDeclaration] => Boolean(entry[1]) && typeof entry[1] === "object" && !Array.isArray(entry[1]));
    }
  } catch { /* Advanced JSON may be incomplete while editing. */ }
  function fieldType(declaration: ParameterDeclaration) {
    return [declaration.field?.control, declaration.format, declaration.type].find(value => typeof value === "string") ?? "texto";
  }
  function renameField(parameter: string, label: string) {
    const recipe = JSON.parse(recipeText);
    if (label) recipe.variables[parameter].label = label;
    else delete recipe.variables[parameter].label;
    editRecipe(JSON.stringify(recipe, null, 2));
  }
  function chooseLoginProfile(value: string) {
    try {
      const recipe = JSON.parse(recipeText);
      if (value) {const [id, version] = value.split(":").map(Number); recipe.login_profile = {id, version};}
      else delete recipe.login_profile;
      editRecipe(JSON.stringify(recipe, null, 2));
    } catch {setFormError("Corrija o JSON antes de vincular um perfil de login.");}
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
      saveVersion.mutate({ automationId: selected.id, recipe, revision: editorRevision.current });
    } catch {
      setFormError("A receita precisa ser um objeto JSON válido.");
    }
  }

  const busy =
    loadingRecipe || createAutomation.isPending ||
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

      <section className="card form-card">
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
                aria-pressed={selected?.id === automation.id}
                key={automation.id}
                disabled={createAutomation.isPending || saveVersion.isPending || testVersion.isPending || publishVersion.isPending}
                onClick={() => void selectAutomation(automation)}
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
            {version ? ` · v${version}` : " · rascunho não salvo"}
          </p>
        ) : (
          <p className="muted">Selecione uma automação para editar a receita.</p>
        )}
      </section>

      <section className="card form-card">
        <h2>Gravação e campos do relatório</h2>
        <label>Perfil de login
          <select value={selectedProfile} disabled={busy || loginProfiles.isFetching} onChange={event => chooseLoginProfile(event.target.value)}>
            <option value="">Sem login</option>
            {selectedProfile && !loginProfiles.data?.items.some(profile => `${profile.id}:${profile.current_version}` === selectedProfile && profile.published && profile.status !== "DISABLED") ? <option value={selectedProfile}>Perfil vinculado — {selectedProfile}</option> : null}
            {loginProfiles.data?.items.filter(profile => profile.published && profile.status !== "DISABLED").map(profile => <option key={profile.id} value={`${profile.id}:${profile.current_version}`}>{profile.name} · v{profile.current_version}</option>)}
          </select>
        </label>
        <p className="muted">Cadastre e publique o acesso em Logins de sites. A receita conserva somente a referência ao perfil.</p>
        <label>
          Importar gravação JSON
          <input type="file" accept=".json,application/json" disabled={busy}
            onChange={event => {void importRecording(event.target.files?.[0]); event.target.value = "";}} />
        </label>
        {loadingRecipe ? <p role="status">Carregando receita…</p> : null}
        {parameters.length ? <div className="recipe-field-editor">
          <h3>Campos no dashboard</h3>
          <p className="muted">Defina como cada campo aparece ao preparar a execução. Os tipos e as regras da gravação são preservados.</p>
          {parameters.filter(([, declaration]) => !declaration.secret).map(([parameter, declaration]) => <label key={parameter}>
            Nome no formulário: {parameter}
            <input aria-label={`Nome no formulário: ${parameter}`} value={typeof declaration.label === "string" ? declaration.label : ""} placeholder={parameterLabel(parameter)} maxLength={100}
              disabled={busy} onChange={event => renameField(parameter, event.target.value)} />
            <small className="muted">{fieldType(declaration)}{declaration.field?.required ? " · obrigatório no site" : ""}</small>
          </label>)}
        </div> : null}
        <details>
        <summary>Editor avançado da receita</summary>
        <p className="muted">
          Use apenas referências como <code>credential_ref</code>; segredos reais não pertencem à receita.
        </p>
        <label>
          JSON da receita
          <textarea
            aria-label="JSON da receita"
            value={recipeText}
            disabled={busy}
            onChange={(event) => editRecipe(event.target.value)}
            rows={22}
            spellCheck={false}
          />
        </label>

        </details>
        {formError ? <p className="form-error" role="alert">{formError}</p> : null}
        {status ? <p role="status">{status}</p> : null}

        <div className="button-row">
          <button type="button" className="primary-button" disabled={busy || !selected || !recipeText.trim()} onClick={save}>
            {saveVersion.isPending ? "Salvando…" : "Salvar versão"}
          </button>
          <button
            type="button"
            disabled={busy || !selected || version == null}
            onClick={() => testVersion.mutate({ automationId: selected!.id, version: version! })}
          >
            {testVersion.isPending ? "Validando…" : "Validar receita"}
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
