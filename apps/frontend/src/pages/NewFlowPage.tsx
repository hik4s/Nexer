import {StepReviewEditor} from "../components/StepReviewEditor";
import {canRepairStep, hasValidStepIds} from "../lib/stepReview";
import {QueryOutcomeEditor} from "../components/QueryOutcomeEditor";
import {canConfigureQuery, type Recipe} from "../lib/queryOutcome";
import {DownloadGenerationEditor} from "../components/DownloadGenerationEditor";
import {useEffect, useRef, useState} from "react";
import {useQuery} from "@tanstack/react-query";
import {Link, useNavigate} from "react-router-dom";
import {api, FlowRecording} from "../lib/api";
import {parameterLabel, ParameterDeclaration} from "../components/RecipeField";
import {initialSiteUrl} from "../lib/practical";
const steps = ["Site", "Acesso", "Gravação", "Campos", "Publicar"];

export function recordingFailureMessage(code: string | null): string {
  const guidance: Record<string, string> = {
    RECORDER_EMPTY: "Nenhuma ação utilizável foi capturada. Inicie a gravação após o login e execute pelo menos uma ação.",
    RECORDER_CONTEXT_UNSUPPORTED: "Foi detectada uma ação ou contexto não suportado (como determinados frames). Revise o componente usado.",
    RECORDER_DOWNLOAD_UNSUPPORTED: "O download não pôde ser associado a uma ação gravada. Revise o botão de download.",
    RECORDER_BROWSER_FAILED: "O Edge ou a comunicação com a página falhou. Verifique se a janela permaneceu aberta e tente novamente.",
    RECORDER_CANCELLED: "A gravação foi cancelada.",
    FLOW_RECORDING_FAILED: "O gravador foi encerrado sem produzir uma receita válida. Tente novamente.",
  };
  return guidance[code ?? ""] ?? "Não foi possível concluir a gravação. Verifique a janela do Edge.";
}
export function NewFlowPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [profile, setProfile] = useState("");
  const [recipe, setRecipe] = useState<Record<string, unknown> | null>(null);
  const [recording, setRecording] = useState<FlowRecording | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [reviewDirty, setReviewDirty] = useState<Record<string,boolean>>({});
  const originalClicks = useRef<Record<string,Record<string,unknown>>>({});
  const owned = useRef<string | null>(null);
  const mounted = useRef(true);
  const saved = useRef<{id: number; version?: number} | null>(null);
  const profiles = useQuery({queryKey: ["login-profiles"], queryFn: api.listLoginProfiles, retry: false});
  const progress = useQuery({queryKey: ["flow-recording", recording?.id], queryFn: () => api.getFlowRecording(recording!.id), enabled: recording?.status === "RECORDING", refetchInterval: recording?.status === "RECORDING" ? 800 : false, retry: false});
  useEffect(() => {mounted.current = true; return () => {mounted.current = false; if (owned.current) void api.cancelFlowRecording(owned.current).catch(() => {});};}, []);
  useEffect(() => {
    if (!progress.data) return;
    if (progress.data.status === "RECORDING") setRecording(progress.data);
    if (progress.data.status === "DONE" && progress.data.recipe) {setRecipe(progress.data.recipe); originalClicks.current={}; setReviewDirty({}); setRecording(progress.data); owned.current = null; saved.current = null; setStep(3);}
    if (progress.data.status === "FAILED" || progress.data.status === "CANCELLED") {setRecording(progress.data); owned.current = null; setError(recordingFailureMessage(progress.data.error));}
  }, [progress.data]);
  async function record() {
    setPending(true); setError("");
    try {const result = await api.startFlowRecording(url); if (!mounted.current) {await api.cancelFlowRecording(result.id); return;} setRecipe(null); originalClicks.current={}; setReviewDirty({}); saved.current = null; owned.current = result.id; setRecording(result);}
    catch (failure) {setError(failure instanceof Error ? failure.message : "Não foi possível abrir o Edge.");}
    finally {setPending(false);}
  }
  async function importFile(file?: File) {
    if (!file) return;
    try {
      if (file.size > 1048576) throw new Error("A receita deve ter no máximo1MB.");
      const data = JSON.parse(await file.text());
      if (!data || typeof data !== "object" || !hasValidStepIds(data.steps) || !data.variables || typeof data.variables !== "object") throw new Error("Arquivo de receita inválido.");
      if (Object.values(data.variables).some(value => !value || typeof value !== "object" || (value as ParameterDeclaration).secret)) throw new Error("Use um perfil de acesso para credenciais.");
      setRecipe(data); originalClicks.current={}; setReviewDirty({}); setError(""); saved.current = null;
    } catch (failure) {setError(failure instanceof Error ? failure.message : "Não foi possível importar.");}
  }
  async function publish() {
    if (!recipe) return;
    setPending(true); setError("");
    try {
      const rawSteps = (recipe.steps as Record<string, unknown>[]).map(step => ({...step}));
      if (rawSteps[0]?.action === "navigate") rawSteps[0].url = "{{base_url}}";
      else rawSteps.unshift({id: `guided_open_${crypto.randomUUID().slice(0, 8)}`, action: "navigate", url: "{{base_url}}"});
      const configured = {...recipe, name, site_url: initialSiteUrl({site_url: url}), steps: rawSteps, variables: {...recipe.variables as object, base_url: {type: "string", required: true, label: "Endereço inicial", ...((recipe.variables as Record<string, ParameterDeclaration>).base_url ?? {})}}};
      delete (configured as Record<string, unknown>).login_profile;
      if (profile) {const [id, version] = profile.split(":").map(Number); (configured as Record<string, unknown>).login_profile = {id, version};}
      if (!saved.current) {const automation = await api.createAutomation({name, code: `FLOW_${crypto.randomUUID().replaceAll("-", "").slice(0, 16).toUpperCase()}`}); saved.current = {id: automation.id};}
      if (!saved.current.version) {const version = await api.createAutomationVersion(saved.current.id, configured, "guided"); saved.current.version = version.version;}
      await api.testAutomationVersion(saved.current.id, saved.current.version);
      await api.publishAutomationVersion(saved.current.id, saved.current.version);
      navigate(`/batches/new?flows=${saved.current.id}`);
    } catch (failure) {setError(failure instanceof Error ? failure.message : "A receita precisa de revisão. O rascunho foi preservado no Studio.");}
    finally {setPending(false);}
  }
  const active = recording?.status === "RECORDING";
  const parameters = Object.entries(recipe?.variables ?? {}).filter(([key]) => key !== "base_url") as [string, ParameterDeclaration][];
  const recordedSteps = (recipe?.steps ?? []) as Record<string, unknown>[];
  const downloads = recordedSteps.filter(item => item.action === "download");
  const querySteps = recordedSteps.filter(item => canConfigureQuery(recipe as Recipe, String(item.id)));
  useEffect(() => {
    for(const item of recordedSteps) if(item.action==='click' && !originalClicks.current[String(item.id)])
      originalClicks.current[String(item.id)]=structuredClone(item);
    setReviewDirty(current => {
      const entries=Object.entries(current).filter(([key])=>{
        const separator=key.indexOf(':');const type=key.slice(0,separator),id=key.slice(separator+1);
        return type==='query' ? querySteps.some(s=>s.id===id) : type==='step' ? recordedSteps.some(s=>s.id===id && canRepairStep(s)) : downloads.some(s=>s.id===id);
      });
      return entries.length===Object.keys(current).length ? current : Object.fromEntries(entries);
    });
  }, [recipe]);
  const smartWaits = recordedSteps.filter(item => item.action === "wait_for");
  function removeAutomaticWait(id: unknown) {
    setRecipe(current => current ? {...current, steps: (current.steps as Record<string, unknown>[]).filter(item => item.id !== id)} : current);
    saved.current = null;
  }
  function updateDownload(id: unknown, key: string, value: string) {
    setRecipe(current => {
      const items = current!.steps as Record<string,unknown>[];
      const download = items.find(item => item.id === id);
      const request = items.find(item => item.id === download?.generation);
      return {...current, steps: items.map(item => item.id === id || item.id === request?.baseline ? {...item, collection: {...(item.collection as object), [key]:value}} : item)};
    });
    saved.current = null;
  }
  return <main className="page-shell"><div className="page-heading"><p className="eyebrow">Cadastro guiado</p><h1>Criar fluxo</h1><p className="muted">Do site à primeira execução, um passo de cada vez.</p></div><ol className="wizard-steps">{steps.map((label, index) => <li key={label} aria-current={step === index ? "step" : undefined}><span>{index + 1}</span>{label}</li>)}</ol>
    <section className="card form-card"><h2>{steps[step]}</h2>
      {step === 0 ? <form onSubmit={event => {event.preventDefault(); if (!initialSiteUrl({site_url: url})) {setError("Informe HTTPS ou HTTP local, sem credenciais ou parâmetros; use somente uma rota segura após #."); return;} setError(""); setStep(1);}}><label>Nome do fluxo<input required maxLength={100} value={name} onChange={event => {setName(event.target.value); saved.current = null;}} /></label><label>Endereço do site<input type="url" required value={url} onChange={event => {setUrl(event.target.value); saved.current = null;}} placeholder="https://…" /></label><p className="muted">Página onde as ações começam, depois do login quando necessário. Você poderá ajustar o endereço ao executar.</p><button className="primary-button">Continuar</button></form> : null}
      {step === 1 ? <><label>Acesso para este fluxo<select value={profile} onChange={event => {setProfile(event.target.value); saved.current = null;}}><option value="">Sem login</option>{profiles.data?.items.filter(item => item.published && item.status !== "DISABLED").map(item => <option value={`${item.id}:${item.current_version}`} key={item.id}>{item.group_name ? item.group_name + " / " : ""}{item.name}</option>)}</select></label><p className="muted">Usuário e senha serão solicitados somente ao executar.</p><Link to="/site-logins" target="_blank">Cadastrar ou configurar acesso</Link></> : null}
      {step === 2 ? <><p className="muted">Grave os locais das ações no Edge, sem guardar valores digitados. Em sites HTTPS, faça login manual no Edge, abra a página e a rota configuradas e clique em Iniciar gravação. O login não entra na receita.</p><button className="primary-button" disabled={pending || active} onClick={record}>Gravar ações no Edge</button>{active && recording.phase === "PREPARING" ? <p role="status">Aguardando: faça login no Edge, abra a rota configurada e clique em Iniciar gravação.</p> : null}{active ? <div className="button-row"><button className="secondary-button" disabled={recording.phase === "PREPARING"} onClick={async () => {try {await api.finishFlowRecording(recording.id); await progress.refetch();} catch (failure) {setError(failure instanceof Error ? failure.message : "Não foi possível solicitar a conclusão.");}}}>Concluir gravação</button><button className="secondary-button" onClick={async () => {try {setRecording(await api.cancelFlowRecording(recording.id)); owned.current = null;} catch {setError("Não foi possível cancelar.");}}}>Cancelar gravação</button></div> : null}<label>Importar receita JSON<input type="file" accept=".json,application/json" disabled={active || pending} onChange={event => {void importFile(event.target.files?.[0]); event.target.value = "";}} /></label>{recipe ? <p role="status">Receita pronta para nomear campos: {Array.isArray(recipe.steps) ? recipe.steps.length : 0} ações.</p> : null}</> : null}
      {step === 3 ? <><StepReviewEditor recipe={recipe as Recipe} siteUrl={url} onChange={updated=>{setRecipe(updated);saved.current=null;}} onDirty={(id,dirty)=>setReviewDirty(current=>({...current,["step:"+id]:dirty}))}/><p className="muted">Campos descobertos após a gravação. Revise os nomes obtidos da página; os valores serão preenchidos em cada execução. Tipos e regras são preservados.</p><div className="recipe-field-editor">{parameters.map(([key, declaration]) => <label key={key}>Nome do campo: {key}<input value={declaration.label ?? ""} placeholder={parameterLabel(key)} maxLength={100} onChange={event => {setRecipe(current => ({...current, variables: {...current!.variables as object, [key]: {...declaration, label: event.target.value}}})); saved.current = null;}} /></label>)}</div><details><summary>Gravação inteligente · {smartWaits.length} condições de espera</summary><p className="muted">Esperas automáticas são sugestões revisáveis. Esperas manuais foram marcadas por você no Edge. Não são gravados valores de campos.</p><ol>{smartWaits.map(item => <li key={String(item.id)}><strong>{String(item.state === "enabled" ? "Aguardar habilitar" : item.state === "hidden" ? "Aguardar desaparecer" : item.state === "disabled" ? "Aguardar desabilitar" : "Aguardar aparecer")}</strong> · {String((item.learning as Record<string, unknown> | undefined)?.source === "manual" ? "Marcada manualmente" : "Sugerida automaticamente")} {String((item.learning as Record<string, unknown> | undefined)?.confidence ?? "")}<button type="button" className="secondary-button" disabled={(item.learning as Record<string, unknown> | undefined)?.source === "manual"} onClick={() => removeAutomaticWait(item.id)}>Remover sugestão</button></li>)}</ol></details>{querySteps.map(item => <details key={"query:"+String(item.id)}><summary>Consulta · {String(item.id)}</summary><QueryOutcomeEditor recipe={recipe as Recipe} stepId={String(item.id)} originalStep={originalClicks.current[String(item.id)]} onChange={updated=>{setRecipe(updated);saved.current=null;}} onDirty={dirty=>setReviewDirty(current=>({...current,["query:"+String(item.id)]:dirty}))}/></details>)}{downloads.map(item => item.collection ? <details key={String(item.id)}><summary>Central de download · {String(item.id)}</summary><p className="muted">{item.generation ? "O download usa a identificação confirmada pela solicitação e o padrão informado na execução. O arquivo mantém o nome fornecido pelo site." : "Sem vínculo à solicitação, a execução escolhe o primeiro nome correspondente ao padrão, seguindo a ordem da central. Esse modo não identifica o seu relatório em uma central compartilhada."}</p>{([['rows', 'Linhas da central'], ['name', 'Nome dentro da linha'], ['button', 'Botão dentro da linha']] as const).map(([key, label]) => <label key={key}>{label}<input value={String((item.collection as Record<string, unknown>)[key] ?? '')} onChange={event => updateDownload(item.id, key, event.target.value)} /></label>)}<DownloadGenerationEditor key={String(item.id)+String(item.generation ?? "")} recipe={recipe as Record<string, unknown> & {steps: Record<string, unknown>[]}} downloadId={String(item.id)} onChange={updated => {setRecipe(updated); saved.current = null;}} onDirty={dirty => setReviewDirty(current => ({...current, ["download:"+String(item.id)]:dirty}))} /></details> : <p className="muted" key={String(item.id)}>Download {String(item.id)}: botão individual. Para uma central com vários arquivos, configure collection no Studio.</p>)}</> : null}
      {step === 4 ? <><h3>{name}</h3><p className="muted">Site: {url}</p><p>{parameters.length} campos personalizados · {profile ? "Com perfil de acesso" : "Sem login"}</p><p className="muted">A validação verifica o contrato da receita. Publicar não executa ações no site; você revisará os parâmetros antes de iniciar.</p><button className="primary-button" disabled={pending} onClick={publish}>{pending ? "Validando…" : "Validar e publicar fluxo"}</button>{saved.current ? <Link to="/studio">Revisar rascunho no Studio</Link> : null}</> : null}
      {progress.isError && active ? <p role="alert" className="form-error">Não foi possível acompanhar a gravação. Verifique a conexão com a API antes de tentar novamente.</p> : null}
      {Object.values(reviewDirty).some(Boolean) ? <p role="status">Aplique ou descarte as alterações pendentes nas etapas, consultas e downloads antes de continuar.</p> : null}{error ? <p role="alert" className="form-error">{error}</p> : null}<div className="button-row">{step > 0 ? <button className="secondary-button" disabled={pending || active || Object.values(reviewDirty).some(Boolean)} onClick={() => setStep(value => value - 1)}>Voltar</button> : null}{step > 0 && step < 4 ? <button className="primary-button" disabled={pending || active || (step >= 2 && !recipe) || Object.values(reviewDirty).some(Boolean)} onClick={() => setStep(value => value + 1)}>Continuar</button> : null}</div>
    </section></main>;
}
