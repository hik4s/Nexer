import { useQuery, useQueries } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, Automation, BatchFlowInput, CreateBatchInput } from "../lib/api";
import { FieldCatalog, ParameterDeclaration, RecipeField, fieldLabel, fieldValueLabel } from "../components/RecipeField";
import { clearCredentials, CredentialFields, readCredentials, SiteCredentialsFields } from "../components/SiteCredentialsFields";
import {accessIdentity, commonParameters, initialSiteUrl, flowDestination, intersectCatalogs} from "../lib/practical";
import {DateShortcuts} from "../components/DateShortcuts";

function parseValues(parameters: [string, ParameterDeclaration][], values: Record<string, string>) {
  const result: Record<string, unknown> = {};
  for (const [name, declaration] of parameters) {
    const raw = values[name];
    if (declaration.secret) throw new Error("Use um perfil de login para credenciais.");
    if (raw === undefined || (raw === "" && !declaration.allow_empty)) {
      if (declaration.required !== false) throw new Error(`Preencha ${declaration.label ?? name}.`);
      continue;
    }
    if (["number", "integer"].includes(declaration.type ?? "")) {
      const number = Number(raw);
      if (!Number.isFinite(number) || (declaration.type === "integer" && !Number.isInteger(number))) throw new Error(`Revise ${name}.`);
      result[name] = number;
    } else if (declaration.type === "boolean") {
      if (!["true", "false"].includes(raw)) throw new Error(`Revise ${name}.`);
      result[name] = raw === "true";
    } else if (declaration.type === "array") {
      const array: unknown = JSON.parse(raw);
      if (!Array.isArray(array) || !array.every(value => typeof value === "string")) throw new Error(`Revise ${name}.`);
      result[name] = array;
    } else result[name] = raw;
  }
  return result;
}

type PreparedFlow = {item: BatchFlowInput; name: string; labels: Record<string, string>; displayValues: Record<string, string>; destination: string; access: string; credentials?: [string, {username: string; password: string}]};
type Accesses = Map<string, {owner: number; fields: CredentialFields}>;
function FlowFields({flow, testMode, prepare, changed, pending, accesses, accessEpoch, accessChanged, commonValues, initialValues, hasShared, sharedPeriod, onCatalogs, loaders}: {flow: Automation; testMode: boolean; prepare: Map<number, (includeCredentials?: boolean) => PreparedFlow>; changed: () => void; pending: boolean; accesses: Accesses; accessEpoch: number; accessChanged: () => void; commonValues: Record<string, string>; initialValues?: Record<string, unknown>; hasShared: boolean; sharedPeriod: boolean; onCatalogs: (id: number, fields: Record<string, FieldCatalog>) => void; loaders: Map<number, () => Promise<void>>}) {
  const version = useQuery({queryKey: ["batch-version", flow.id, flow.current_version], queryFn: () => api.getAutomationVersion(flow.id, flow.current_version!)});
  const reference = version.data?.recipe.login_profile as {id: number; version: number} | undefined;
  const profile = useQuery({queryKey: ["login-profile-version", reference?.id, reference?.version], queryFn: () => api.getLoginProfileVersion(reference!.id, reference!.version), enabled: Boolean(reference)});
  const [values, setValues] = useState<Record<string, string>>({});
  const [catalogs, setCatalogs] = useState<Record<string, FieldCatalog>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [individual, setIndividual] = useState(false);
  const generation = useRef(0);
  const parameters = Object.entries(version.data?.recipe.variables ?? {}) as [string, ParameterDeclaration][];
  const choices = parameters.filter(([, declaration]) => ["select", "multiselect", "radio"].includes(declaration.field?.control ?? ""));
  const ready = choices.every(([name]) => catalogs[name] && !catalogs[name].error);
  const current = useRef({values, catalogs}); current.current = {values, catalogs};
  function updateValues(next: Record<string, string>, invalid: string[]) {
    const metadata = {...current.current.catalogs}; invalid.forEach(name => {delete next[name]; delete metadata[name];});
    setValues(next); setCatalogs(metadata); onCatalogs(flow.id, metadata);
  }
  function changeValue(name: string, value: string) {
    generation.current++; changed();
    const index = choices.findIndex(([key]) => key === name);
    const invalid = (index < 0 ? choices : choices.slice(index + 1)).map(([key]) => key);
    updateValues({...current.current.values, [name]: value}, invalid);
  }
  const identity = reference ? `profile-${reference.id}-v${reference.version}` : undefined;
  const accessKey = profile.data ? accessIdentity({...profile.data, current_version: reference!.version}) : undefined;
  if (accessKey && !accesses.has(accessKey)) accesses.set(accessKey, {owner: flow.id, fields: {username: null, password: null}});
  const accessFields = accessKey ? accesses.get(accessKey)! : undefined;
  useEffect(() => {
    if (initialValues || !version.data) return;
    const site = initialSiteUrl(version.data.recipe);
    if (site && parameters.some(([name]) => name === "base_url")) setValues(current => ({...current, base_url: current.base_url ?? site}));
  }, [version.data, initialValues]);
  useEffect(() => {
    if (!initialValues) return;
    const declarations = version.data?.recipe.variables as Record<string, ParameterDeclaration> | undefined;
    if (!declarations) return;
    setValues(Object.fromEntries(Object.entries(initialValues).filter(([name]) => declarations[name] && !declarations[name].secret).map(([name, value]) => [name, Array.isArray(value) ? JSON.stringify(value) : String(value)])));
    generation.current++; setCatalogs({});
  }, [initialValues, version.data]);
  useEffect(() => {
    if (individual || !Object.keys(commonValues).length) return;
    const changedNames = Object.keys(commonValues).filter(name => current.current.values[name] !== commonValues[name]);
    if (!changedNames.length) return;
    const indexes = changedNames.map(name => choices.findIndex(([key]) => key === name));
    const invalid = (indexes.some(index => index < 0) ? choices : choices.slice(Math.min(...indexes) + 1)).map(([key]) => key);
    updateValues({...current.current.values, ...commonValues}, invalid); generation.current++;
  }, [commonValues, individual]);
  useEffect(() => {generation.current++; setCatalogs({}); onCatalogs(flow.id, {});}, [accessEpoch, flow.id, onCatalogs]);
  function credentials() {
    if (!identity) return undefined;
    if (!profile.data?.published || profile.data.status === "DISABLED") throw new Error("Perfil de login indisponível.");
    return [identity, readCredentials(accessFields!.fields)] as [string, {username: string; password: string}];
  }
  prepare.set(flow.id, (includeCredentials = true) => {
    if (!version.data || !ready) throw new Error(`Prepare os campos de ${flow.name}.`);
    if (reference && (profile.isFetching || profile.isError || !profile.data?.published || profile.data.status === "DISABLED")) throw new Error(`Aguarde ou revise o acesso de ${flow.name}.`);
    for (const [name, declaration] of choices) {
      const selected = declaration.type === "array" ? JSON.parse(values[name] ?? "[]") : [values[name]];
      if (!Array.isArray(selected) || selected.some(value => value !== undefined && !(value === "" && declaration.allow_empty) && !catalogs[name].options.some(option => !option.disabled && option.value === value))) throw new Error(`Atualize as opções de ${flow.name}.`);
    }
    const access = testMode || !includeCredentials ? undefined : credentials();
    const inputs = parseValues(parameters, values);
    return {item: {automation_id: flow.id, version: flow.current_version!, inputs, test_mode: testMode}, name: flow.name, labels: Object.fromEntries(parameters.map(([name, declaration]) => [name, fieldLabel(name, declaration)])), displayValues: Object.fromEntries(Object.entries(inputs).map(([name, value]) => [name, fieldValueLabel(value, parameters.find(([key]) => key === name)?.[1], catalogs[name])])), credentials: access, destination: flowDestination(version.data.recipe, inputs, profile.data?.configuration.login_url), access: profile.data?.group_name ?? profile.data?.name ?? "Sem login"};
  });
  async function loadOptions() {
    const token = ++generation.current;
    setLoading(true); setError("");
    let access: ReturnType<typeof credentials>;
    try {
      access = credentials();
      const inputs = parseValues(parameters.map(([name, declaration]) => [name, {...declaration, required: false}]), values);
      const result = access ? await api.getReportOptions(flow.id, flow.current_version!, inputs, {[access[0]]: access[1]}) : await api.getReportOptions(flow.id, flow.current_version!, inputs);
      if (token === generation.current) {setCatalogs(result.fields); onCatalogs(flow.id, result.fields);}
    } catch (failure) {
      if (token === generation.current) {
        const message = failure instanceof Error ? failure.message : "";
        setError(message && !message.startsWith("API_REQUEST_FAILED:") ? message : "Não foi possível preparar as opções do site.");
      }
    }
    finally {if (access) {access[1].username = ""; access[1].password = "";} setLoading(false);}
  }
  loaders.set(flow.id, loadOptions);
  return <fieldset className="card" disabled={pending}><legend>{flow.name}</legend>
    {version.isError ? <p role="alert">Não foi possível carregar a receita.</p> : null}
    {reference && profile.data ? <><p className="muted">{profile.data.configuration.login_url} · perfil v{reference.version}</p>{accessFields?.owner === flow.id ? <SiteCredentialsFields name={profile.data.group_name ?? profile.data.name} fields={accessFields.fields} disabled={testMode} onChange={accessChanged} /> : <p className="muted">Usa o acesso informado para {profile.data.group_name ?? profile.data.name} neste lote.</p>}</> : null}
    {hasShared ? <label className="checkbox-label"><input type="checkbox" checked={individual} onChange={event => {setIndividual(event.target.checked); changed();}} />Personalizar somente {flow.name}</label> : null}
    {parameters.some(([name, declaration]) => name === "period_start" && [undefined, "date"].includes(declaration.field?.control)) && (!sharedPeriod || individual) ? <DateShortcuts onChoose={period => {setIndividual(true); updateValues({...current.current.values, ...period}, choices.map(([key]) => key)); generation.current++; changed();}} /> : null}
    <div className="form-grid">{parameters.map(([name, declaration]) => <fieldset className="parameter-lock" disabled={!individual && name in commonValues} key={name}><RecipeField idPrefix={`${flow.id}-`} name={name} declaration={declaration} value={values[name]} catalog={catalogs[name]} onChange={value => changeValue(name, value)} /></fieldset>)}</div>
    {choices.length ? <button type="button" className="secondary-button" onClick={loadOptions} disabled={loading}>{loading ? "Carregando opções…" : "Carregar opções do site"}</button> : null}
    {error ? <p role="alert">{error}</p> : null}
  </fieldset>;
}

export function NewBatchPage() {
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const routineId = Number(search.get("routine"));
  const repeatId = Number(search.get("repeat"));
  const repeatExecutionId = Number(search.get("repeatExecution"));
  const source = useQuery({queryKey: ["preparation-source", routineId, repeatId, repeatExecutionId], enabled: Boolean(routineId || repeatId || repeatExecutionId), retry: false, queryFn: async () => {
    if (routineId) return api.getRoutine(routineId);
    const batch = repeatId ? await api.getBatch(repeatId) : {name: "", executions: [await api.getExecution(repeatExecutionId)]};
    const items = await Promise.all(batch.executions.flatMap(execution => execution.items.map(async item => {
      const recipe = await api.getAutomationVersion(item.automation_id, item.automation_version);
      const declarations = recipe.recipe.variables as Record<string, ParameterDeclaration> ?? {};
      const inputs = Object.fromEntries(Object.entries(execution.inputs).filter(([name]) => declarations[name] && !declarations[name].secret && !["password", "senha", "username", "token", "credentials", "profile_credentials", "corporate_credentials"].includes(name.toLowerCase())));
      return {automation_id: item.automation_id, version: item.automation_version, inputs};
    })));
    return {name: batch.name || batch.executions[0].name, items};
  }});
  const ids = source.data?.items.map(item => item.automation_id) ?? (search.get("flows") ?? "").split(",").map(Number).filter(id => id > 0).slice(0, 20);
  const catalog = useQuery({queryKey: ["automations", "published"], queryFn: () => api.listAutomations({status: "PUBLISHED", limit: 100})});
  const flows = catalog.data?.items.filter(flow => ids.includes(flow.id)) ?? [];
  const [name, setName] = useState("");
  const [testMode, setTestMode] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [review, setReview] = useState<PreparedFlow[] | null>(null);
  const [commonValues, setCommonValues] = useState<Record<string, string>>({});
  const [siteCatalogs, setSiteCatalogs] = useState<Record<number, Record<string, FieldCatalog>>>({});
  const [preparingOptions, setPreparingOptions] = useState(false);
  const loaders = useRef(new Map<number, () => Promise<void>>());
  const onCatalogs = useCallback((id: number, fields: Record<string, FieldCatalog>) => setSiteCatalogs(current => ({...current, [id]: fields})), []);
  const versions = useQueries({queries: flows.map(flow => ({queryKey: ["batch-version", flow.id, flow.current_version], queryFn: () => api.getAutomationVersion(flow.id, flow.current_version!)}))});
  const candidates = versions.length === flows.length && versions.every(version => version.data && !version.isFetching && !version.isError) ? commonParameters(versions.map(version => version.data!.recipe)) : [];
  const commonCatalogs = Object.fromEntries(candidates.filter(([, declaration]) => ["select", "multiselect", "radio"].includes(declaration.field?.control ?? "")).map(([name]) => [name, intersectCatalogs(flows.map(flow => siteCatalogs[flow.id]?.[name]))]));
  const common = candidates.filter(([name, declaration]) => !["select", "multiselect", "radio"].includes(declaration.field?.control ?? "") || Boolean(commonCatalogs[name] && (commonCatalogs[name]!.options.length || declaration.allow_empty)));
  const commonSignature = JSON.stringify(common);
  const effectiveSharedValues = useMemo(() => {
    const names = new Set((JSON.parse(commonSignature) as [string, ParameterDeclaration][]).map(([name]) => name));
    return Object.fromEntries(Object.entries(commonValues).filter(([name]) => names.has(name)));
  }, [commonValues, commonSignature]);
  useEffect(() => {if (source.data) setName(source.data.name);}, [source.data]);
  const key = useRef(crypto.randomUUID());
  const accesses = useRef(new Map<string, {owner: number; fields: CredentialFields}>());
  const [accessEpoch, setAccessEpoch] = useState(0);
  const prepare = useRef(new Map<number, (includeCredentials?: boolean) => PreparedFlow>());
  const changed = () => {key.current = crypto.randomUUID(); setReview(null); setError("");};
  function updateCommon(patch: Record<string, string>) {
    const choiceNames = candidates.filter(([, declaration]) => ["select", "multiselect", "radio"].includes(declaration.field?.control ?? "")).map(([name]) => name);
    const indexes = Object.keys(patch).map(name => choiceNames.indexOf(name));
    const invalid = indexes.some(index => index < 0) ? choiceNames : choiceNames.slice(Math.min(...indexes) + 1);
    setCommonValues(current => {const next = {...current, ...patch}; invalid.forEach(name => {if (!(name in patch)) delete next[name];}); return next;});
    changed();
  }
  async function prepareOptions() {
    setPreparingOptions(true); setReview(null);
    try {for (const flow of flows) await loaders.current.get(flow.id)?.();}
    finally {setPreparingOptions(false);}
  }
  async function favorite() {
    try {
      if (!name.trim()) throw new Error("Nomeie a rotina antes de salvar.");
      await api.saveRoutine({name, items: flows.map(flow => ({automation_id: flow.id, version: flow.current_version!, inputs: {}}))});
      setNotice("Rotina favorita salva. Os campos e credenciais serão definidos a cada execução.");
    } catch (failure) {setError(failure instanceof Error ? failure.message : "Não foi possível salvar a rotina.");}
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError("");
    const payload: CreateBatchInput = {name, idempotency_key: key.current, items: [], profile_credentials: {}};
    try {
      if (!flows.length || flows.length !== new Set(ids).size) throw new Error("Selecione fluxos publicados no dashboard.");
      if (!review) {
        setReview(flows.map(flow => {const prepareFlow = prepare.current.get(flow.id); if (!prepareFlow) throw new Error("Aguarde as receitas."); return prepareFlow(false);}));
        return;
      }
      for (const flow of flows) {
        const prepared = prepare.current.get(flow.id)?.();
        if (!prepared) throw new Error("Aguarde o carregamento das receitas.");
        payload.items.push(prepared.item);
        if (prepared.credentials) {
          const [identity, access] = prepared.credentials;
          const previous = payload.profile_credentials![identity];
          if (previous && (previous.username !== access.username || previous.password !== access.password)) throw new Error("Use as mesmas credenciais para os fluxos com o mesmo perfil de login.");
          payload.profile_credentials![identity] = access;
        }
      }
      setPending(true);
      accesses.current.forEach(access => clearCredentials(access.fields));
      const batch = await api.createBatch(payload);
      navigate(`/batches/${batch.id}`);
    } catch (failure) {setError(failure instanceof Error ? failure.message : "Não foi possível iniciar o lote.");}
    finally {Object.values(payload.profile_credentials ?? {}).forEach(access => {access.username = ""; access.password = "";}); delete payload.profile_credentials; setPending(false);}
  }
  return <main className="page-shell"><h1>Preparar lote</h1><p className="muted">Cada fluxo mantém seus parâmetros, progresso e cancelamento. O modo de teste simula as ações.</p>
    {source.data ? <p className="muted">Parâmetros recuperados para revisão com as receitas atuais. Informe novas credenciais e carregue novamente as listas do site.</p> : null}
    {source.isError ? <p role="alert">Não foi possível recuperar a rotina ou execução anterior.</p> : null}
    <form onSubmit={submit}><label>Nome do lote<input required value={name} disabled={pending} onChange={event => {setName(event.target.value); changed();}} /></label>
      <label className="checkbox-label"><input type="checkbox" checked={testMode} disabled={pending} onChange={event => {setTestMode(event.target.checked); changed();}} />Modo de teste</label>
      {versions.some(version => Object.values(version.data?.recipe.variables ?? {}).some(declaration => ["select", "multiselect", "radio"].includes((declaration as ParameterDeclaration).field?.control ?? ""))) ? <button type="button" className="secondary-button" disabled={pending || preparingOptions} onClick={prepareOptions}>{preparingOptions ? "Preparando opções…" : "Carregar opções de todos os sites"}</button> : null}
      {common.length ? <fieldset className="card"><legend>Parâmetros compartilhados</legend><p className="muted">Preencha uma vez para os campos compatíveis. As listas mostram somente escolhas válidas em todos os destinos.</p>{common.some(([name, declaration]) => name === "period_start" && [undefined, "date"].includes(declaration.field?.control)) ? <DateShortcuts onChoose={updateCommon} /> : null}<div className="form-grid">{common.map(([name, declaration]) => <RecipeField key={name} idPrefix="common-" name={name} declaration={{...declaration, required: false}} value={commonValues[name]} catalog={commonCatalogs[name]} onChange={value => updateCommon({[name]: value})} />)}</div></fieldset> : null}
      {flows.map(flow => <FlowFields key={flow.id} flow={flow} testMode={testMode} prepare={prepare.current} changed={changed} pending={pending} accesses={accesses.current} accessEpoch={accessEpoch} accessChanged={() => {setAccessEpoch(epoch => epoch + 1); setReview(null);}} commonValues={effectiveSharedValues} initialValues={source.data?.items.find(item => item.automation_id === flow.id)?.inputs} hasShared={common.length > 0} sharedPeriod={common.some(([name]) => name === "period_start")} onCatalogs={onCatalogs} loaders={loaders.current} />)}
      {review ? <section className="card execution-review"><h2>Resumo antes de iniciar</h2><p>{name} · {testMode ? "Simulação" : "Execução real"} · {review.length} fluxos</p>{review.map(prepared => <div key={prepared.item.automation_id}><h3>{prepared.name}</h3><p className="muted">{prepared.destination} · Acesso: {prepared.access}</p><dl>{Object.keys(prepared.item.inputs).map(name => <div key={name}><dt>{prepared.labels[name] ?? name}</dt><dd>{prepared.displayValues[name]}</dd></div>)}</dl></div>)}<button type="button" className="secondary-button" onClick={() => setReview(null)}>Voltar aos campos</button></section> : null}
      {error ? <p role="alert">{error}</p> : null}{notice ? <p role="status">{notice}</p> : null}<div className="button-row"><button className="primary-button" disabled={pending || !flows.length}>{pending ? "Iniciando…" : review ? "Confirmar e iniciar" : "Iniciar lote"}</button><button type="button" className="secondary-button" disabled={pending || !flows.length} onClick={favorite}>Salvar como rotina favorita</button></div>
    </form></main>;
}
