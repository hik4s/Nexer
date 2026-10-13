import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import { api, type CreateExecutionInput } from "../lib/api";
import { SiteCredentialsFields, clearCredentials, readCredentials, type CredentialFields } from "../components/SiteCredentialsFields";
import { CorporateCredentialsFields } from "../components/CorporateCredentialsFields";

import { RecipeField, type ParameterDeclaration, type FieldCatalog } from "../components/RecipeField";
import {DateShortcuts} from "../components/DateShortcuts";

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

export function NewExecutionPage({initialAutomationId = "", embedded = false}: {initialAutomationId?: string; embedded?: boolean} = {}) {
  const Container = embedded ? "div" : "main";
  const [catalogs, setCatalogs] = useState<Record<string, FieldCatalog>>({});
  const generation = useRef(0);
  const credentialFields = useRef<CredentialFields>({username: null, password: null});
  const submission = useRef<CreateExecutionInput | null>(null);
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const [parameterValues, setParameterValues] = useState<Record<string, string>>({});
  const [review, setReview] = useState<{name: string; inputs: Record<string, unknown>; start: string; end: string; test: boolean} | null>(null);

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
      automationId: initialAutomationId,
      periodStart: "",
      periodEnd: "",
      sendToNetwork: false,
      keepLocalCopy: true,
      overwriteExisting: false,
      testMode: true,
      inputs: "{}",
    },
  });

  const automationId = form.watch("automationId");
  const testMode = form.watch("testMode");
  const selectedAutomation = automations.data?.items.find(item => String(item.id) === automationId);
  const version = useQuery({
    queryKey: ["automation-version", automationId, selectedAutomation?.current_version],
    queryFn: () => api.getAutomationVersion(Number(automationId), selectedAutomation!.current_version!),
    enabled: Boolean(selectedAutomation?.current_version),
    retry: false,
  });
  useEffect(() => { setParameterValues({}); setCatalogs({}); setReview(null); generation.current++; }, [automationId]);
  const declarations = version.data?.recipe.variables;
  const profileReference = version.data?.recipe.login_profile as {id: number; version: number} | undefined;
  const loginProfile = useQuery({queryKey: ["login-profile-version", profileReference?.id, profileReference?.version],
    queryFn: () => api.getLoginProfileVersion(profileReference!.id, profileReference!.version), enabled: Boolean(profileReference?.id), retry: false});
  useEffect(() => {clearCredentials(credentialFields.current);}, [automationId, profileReference?.id, profileReference?.version]);
  const parameters = declarations && typeof declarations === "object" && !Array.isArray(declarations)
    ? Object.entries(declarations).filter((entry): entry is [string, ParameterDeclaration] =>
        entry[1] !== null && typeof entry[1] === "object" && !Array.isArray(entry[1]))
    : [];

  const choiceParameters = parameters.filter(([, declaration]) => ["select", "multiselect", "radio"].includes(declaration.field?.control ?? ""));
  const choicesReady = choiceParameters.every(([name]) => catalogs[name] && !catalogs[name].error);
  const optionsMutation = useMutation({
    mutationFn: async () => {
      const requestGeneration = generation.current;
      const inputs: Record<string, unknown> = {...parameterValues};
      for (const [name, declaration] of parameters) {
        if (declaration.type === "boolean" && typeof inputs[name] === "string") inputs[name] = inputs[name] === "true";
        if (declaration.type === "array" && typeof inputs[name] === "string") {
          try {inputs[name] = JSON.parse(inputs[name] as string);} catch {delete inputs[name];}
        }
      }
      if (form.getValues("periodStart")) inputs.period_start = form.getValues("periodStart");
      if (form.getValues("periodEnd")) inputs.period_end = form.getValues("periodEnd");
      let credentials: Record<string, {username: string; password: string}> | undefined;
      if (profileReference) credentials = {[`profile-${profileReference.id}-v${profileReference.version}`]: readCredentials(credentialFields.current)};
      let result;
      try {
        result = credentials ? await api.getReportOptions(Number(automationId), selectedAutomation!.current_version!, inputs, credentials) : await api.getReportOptions(Number(automationId), selectedAutomation!.current_version!, inputs);
      } finally {
        if (credentials) for (const value of Object.values(credentials)) {value.username = ""; value.password = "";}
      }
      return {result, requestGeneration};
    },
    onSuccess: ({result, requestGeneration}) => {
      if (generation.current !== requestGeneration) return;
      setReview(null);
      setCatalogs(result.fields);
      setParameterValues(current => {
        const next = {...current};
        for (const [name, declaration] of choiceParameters) {
          const available = result.fields[name]?.options.filter(option => !option.disabled).map(option => option.value) ?? [];
          if (declaration.field?.control === "multiselect") {
            if (current[name] !== undefined) {
              try {
                const selected: string[] = JSON.parse(current[name]);
                if (selected.some(value => !available.includes(value))) delete next[name];
              } catch {delete next[name];}
            }
          } else if (!available.includes(current[name])) delete next[name];
        }
        return next;
      });
    },
    onError: error => setFormError(error instanceof Error ? error.message : "Não foi possível carregar as opções do site."),
  });
  const changeParameter = (name: string, value: string) => {
    setReview(null);
    generation.current++;
    setParameterValues(current => ({...current, [name]: value}));
    // An upstream filter can change downstream catalogs. Require a fresh read.
    const choiceIndex = choiceParameters.findIndex(([parameter]) => parameter === name);
    if (choiceIndex < 0) setCatalogs({});
    else {
      const downstream = choiceParameters.slice(choiceIndex + 1).map(([parameter]) => parameter);
      setCatalogs(current => Object.fromEntries(Object.entries(current).filter(([parameter]) => !downstream.includes(parameter))));
      setParameterValues(current => Object.fromEntries(Object.entries(current).filter(([parameter]) => !downstream.includes(parameter))));
    }
  };

  const mutation = useMutation({
    mutationFn: async () => {
      const input = submission.current;
      submission.current = null;
      if (!input) throw new Error("Prepare a execução antes de enviar.");
      try {return await api.createExecution(input);}
      finally {
        if (input.profile_credentials) {
          for (const values of Object.values(input.profile_credentials)) {values.username = ""; values.password = "";}
          delete input.profile_credentials;
        }
      }
    },
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

    if (version.isFetching || version.isError) {
      setFormError("Aguarde o carregamento dos parâmetros da receita.");
      return;
    }
    if (!choicesReady) {setFormError("Carregue as opções do site antes de criar a execução."); return;}
    for (const [name, declaration] of parameters) {
      if (declaration.secret) {
        setFormError("Esta receita exige uma credencial gerenciada. A execução corporativa permanece indisponível.");
        return;
      }
      if (name === "period_start" || name === "period_end") continue;
      const raw = parameterValues[name] ?? "";
      if ((parameterValues[name] === undefined || (!raw && !declaration.allow_empty)) && declaration.required !== false) {
        setFormError(`Informe o parâmetro ${name}.`);
        return;
      }
      if (!raw && !declaration.allow_empty) continue;
      if (declaration.type === "boolean") inputs[name] = raw === "true";
      else if (declaration.type === "integer" || declaration.type === "number") {
        const number = Number(raw);
        if (!Number.isFinite(number) || (declaration.type === "integer" && !Number.isInteger(number))) {
          setFormError(`Informe um número válido para ${name}.`); return;
        }
        inputs[name] = number;
      } else if (declaration.type === "array") {
        try {
          const array: unknown = JSON.parse(raw);
          if (!Array.isArray(array) || !array.every(item => typeof item === "string")) throw new Error();
          inputs[name] = array;
        } catch { setFormError(`Informe uma lista JSON de textos para ${name}.`); return; }
      } else inputs[name] = raw;
    }

    if (!review) {setReview({name: values.name, inputs, start: values.periodStart, end: values.periodEnd, test: values.testMode}); return;}
    let credentials: CreateExecutionInput["profile_credentials"];
    if (profileReference) {
      if (loginProfile.isFetching || loginProfile.isError || !loginProfile.data?.published || loginProfile.data.status === "DISABLED") {
        setFormError("O perfil de login precisa estar publicado e disponível."); return;
      }
      if (!values.testMode) {
        try {credentials = {[`profile-${profileReference.id}-v${profileReference.version}`]: readCredentials(credentialFields.current)};}
        catch (error) {setFormError(error instanceof Error ? error.message : "Informe as credenciais."); return;}
      }
    }
    submission.current = {
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
      ...(credentials ? {profile_credentials: credentials} : {}),
    };
    clearCredentials(credentialFields.current);
    mutation.mutate();
  });

  const publishedAutomations = automations.data?.items ?? [];

  return (
    <Container className={embedded ? "registered-report-form" : "page-shell"}>
      {!embedded ? <div className="page-heading">
        <p className="eyebrow">Operação</p>
        <h1>Nova execução</h1>
        <p className="muted">
          Crie uma execução nomeada a partir de uma automação publicada.
        </p>
      </div>

      : null}
      {!embedded && ["SGIND", "IQOS"].includes(selectedAutomation?.system ?? "") ? <CorporateCredentialsFields /> : null}
      <section className="card form-card">
        {automations.isLoading ? (
          <p className="muted">Carregando automações publicadas…</p>
        ) : automations.isError ? (
          <div>
            <h2>Não foi possível carregar automações</h2>
            <p className="muted">Confira se a API está disponível.</p>
          </div>
        ) : publishedAutomations.length === 0 ? (
          <div>
            <h2>Nenhuma automação publicada</h2>
            <p className="muted">
              Publique uma automação antes de criar uma execução.
            </p>
          </div>
        ) : (
            <form onSubmit={onSubmit} onChange={() => setReview(null)}>
            <label>
              Nome da execução
              <input
                {...form.register("name")}
                placeholder="Relatório de outubro"
              />
            </label>

            {!embedded ? <label>
              Automação
              <select {...form.register("automationId")}>
                <option value="">Selecione…</option>
                {publishedAutomations.map((automation) => (
                  <option key={automation.id} value={automation.id}>
                    {automation.code} — {automation.name}
                  </option>
                ))}
              </select>
            </label> : <h3>{selectedAutomation?.name}</h3>}

            <DateShortcuts onChoose={period => {form.setValue("periodStart", period.period_start, {shouldValidate: true}); form.setValue("periodEnd", period.period_end, {shouldValidate: true}); generation.current++; setCatalogs({}); setReview(null);}} />
            <div className="form-grid">
              <label>
                {parameters.find(([name]) => name === "period_start")?.[1].label?.trim() || "Período inicial"}
                <input type="date" min={parameters.find(([name]) => name === "period_start")?.[1].field?.min} max={parameters.find(([name]) => name === "period_start")?.[1].field?.max} step={parameters.find(([name]) => name === "period_start")?.[1].field?.step} required={parameters.some(([name, declaration]) => name === "period_start" && declaration.required !== false)} {...form.register("periodStart", {onChange: () => {generation.current++; setCatalogs({});}})} />
              </label>
              <label>
                {parameters.find(([name]) => name === "period_end")?.[1].label?.trim() || "Período final"}
                <input type="date" min={parameters.find(([name]) => name === "period_end")?.[1].field?.min} max={parameters.find(([name]) => name === "period_end")?.[1].field?.max} step={parameters.find(([name]) => name === "period_end")?.[1].field?.step} required={parameters.some(([name, declaration]) => name === "period_end" && declaration.required !== false)} {...form.register("periodEnd", {onChange: () => {generation.current++; setCatalogs({});}})} />
              </label>
            </div>

            {version.isFetching ? <p className="muted">Carregando parâmetros da receita…</p> : null}
            {version.isError ? <p role="alert">Não foi possível carregar os parâmetros da receita.</p> : null}
            {profileReference && loginProfile.isFetching ? <p>Carregando perfil de login…</p> : null}
            {profileReference && loginProfile.isError ? <p role="alert">Não foi possível carregar o perfil de login.</p> : null}
            {profileReference && loginProfile.data ? <SiteCredentialsFields key={`${profileReference.id}:${profileReference.version}`} name={loginProfile.data.name} fields={credentialFields.current} disabled={testMode || mutation.isPending} onChange={() => {generation.current++; setCatalogs({});}} /> : null}
            {choiceParameters.length ? <div>
              <p className="muted">Informe o endereço inicial e carregue as escolhas atuais do site. Após mudar um filtro de lista, atualize as opções dependentes.</p>
              <button type="button" className="secondary-button" disabled={optionsMutation.isPending || version.isFetching}
                onClick={() => {setFormError(null); optionsMutation.mutate();}}>
                {optionsMutation.isPending ? "Consultando site…" : "Carregar opções do site"}
              </button>
              {Object.values(catalogs).some(catalog => catalog.error) ? <p role="alert">Alguns campos não estão disponíveis nesta página. Confira o endereço inicial e os filtros.</p> : null}
            </div> : null}
            {parameters.filter(([name, declaration]) => !["period_start", "period_end"].includes(name) && !declaration.secret).map(([name, declaration]) => (
              <RecipeField key={`${automationId}:${name}`} name={name} declaration={declaration} value={parameterValues[name]}
                catalog={catalogs[name]} onChange={value => changeParameter(name, value)} />
            ))}

            <details>
            <summary>Entradas avançadas</summary>
            <label>
              Entradas adicionais da receita (JSON)
              <textarea
                {...form.register("inputs")}
                rows={7}
                spellCheck={false}
              />
            </label>
            </details>

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

            {review ? <section className="execution-review"><h2>Resumo antes de iniciar</h2><p>{review.name} · {review.test ? "Simulação" : "Execução real"}</p><p className="muted">{selectedAutomation?.name} · {loginProfile.data?.configuration.login_url ?? String(review.inputs.base_url ?? "Destino da receita")} · {loginProfile.data?.group_name ?? loginProfile.data?.name ?? "Sem perfil de login"}</p><p>{review.start} — {review.end}</p><dl>{Object.entries(review.inputs).filter(([name]) => !parameters.find(([key]) => key === name)?.[1].secret).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{Array.isArray(value) ? value.join(", ") : String(value)}</dd></div>)}</dl><button type="button" className="secondary-button" onClick={() => setReview(null)}>Voltar aos campos</button></section> : null}
            <button
              type="submit"
              className="primary-button"
              disabled={mutation.isPending || version.isFetching || version.isError || optionsMutation.isPending || !choicesReady || (Boolean(profileReference) && (loginProfile.isFetching || loginProfile.isError))}
            >
              {mutation.isPending ? "Criando…" : review ? "Confirmar e criar execução" : "Criar execução"}
            </button>
          </form>
        )}
      </section>
    </Container>
  );
}
