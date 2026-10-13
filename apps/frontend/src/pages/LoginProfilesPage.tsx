import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type LoginConfiguration, type LoginRecording, type SiteLoginProfile } from "../lib/api";

const targetNames = {username_target: "Campo de usuário", password_target: "Campo de senha", submit_target: "Botão de entrada"} as const;

export function LoginProfilesPage() {
  const [name, setName] = useState(""); const [url, setUrl] = useState("");
  const [groupName, setGroupName] = useState("");
  const [groupId, setGroupId] = useState("");
  const [templateId, setTemplateId] = useState("");
  const groups = useQuery({queryKey: ["access-groups"], queryFn: api.listAccessGroups, retry: false});
  const [selected, setSelected] = useState<SiteLoginProfile | null>(null);
  const [draft, setDraft] = useState<LoginConfiguration | null>(null);
  const [recording, setRecording] = useState<LoginRecording | null>(null);
  const [dirty, setDirty] = useState(false); const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);
  const mounted = useRef(true);
  const ownedRecording = useRef<LoginRecording | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      generation.current++;
      const active = ownedRecording.current;
      ownedRecording.current = null;
      if (active?.status === "RECORDING") void Promise.resolve(api.cancelLoginRecording(active.profile_id, active.id)).catch(() => {});
    };
  }, []);
  const profiles = useQuery({queryKey: ["login-profiles"], queryFn: api.listLoginProfiles, retry: false});
  const select = (profile: SiteLoginProfile) => {generation.current++; setSelected(profile); setDraft(structuredClone(profile.configuration)); setRecording(null); setDirty(false); setError(null);};
  const fail = (error: unknown) => setError(error instanceof Error ? error.message : "Não foi possível atualizar o perfil.");
  const create = useMutation({mutationFn: (input: {name: string; login_url: string; group_id?: number; template_profile_id?: number}) => api.createLoginProfile(input), onSuccess: profile => {select(profile); void profiles.refetch();}, onError: fail});
  const createGroup = useMutation({mutationFn: () => api.createAccessGroup(groupName), onSuccess: group => {setGroupId(String(group.id)); setGroupName(""); void groups.refetch();}, onError: fail});
  const removeGroup = useMutation({mutationFn: (id: number) => api.deleteAccessGroup(id), onSuccess: () => {setGroupId(""); void groups.refetch();}, onError: fail});
  const linkGroup = useMutation({mutationFn: (id: number | null) => api.setAccessGroup(selected!.id, id), onSuccess: profile => {select(profile); void profiles.refetch();}, onError: fail});
  const save = useMutation({mutationFn: () => api.createLoginProfileVersion(selected!.id, draft!), onSuccess: profile => {select(profile); void profiles.refetch();}, onError: fail});
  const publish = useMutation({mutationFn: () => api.publishLoginProfile(selected!.id, selected!.current_version), onSuccess: profile => {select(profile); void profiles.refetch();}, onError: fail});
  const disable = useMutation({mutationFn: () => api.disableLoginProfile(selected!.id), onSuccess: profile => {select(profile); void profiles.refetch();}, onError: fail});
  const remove = useMutation({mutationFn: (id: number) => api.deleteLoginProfile(id), onSuccess: () => {generation.current++; ownedRecording.current = null; setSelected(null); setDraft(null); setRecording(null); setDirty(false); setError(null); setTemplateId(""); void profiles.refetch();}, onError: fail});
  const start = useMutation({mutationFn: async () => {const current = generation.current; const result = await api.startLoginRecording(selected!.id); if (!mounted.current || current !== generation.current) {await api.cancelLoginRecording(result.profile_id, result.id); return {result, current};} ownedRecording.current = result; return {result, current};}, onSuccess: ({result, current}) => {if (mounted.current && current === generation.current) setRecording(result);}, onError: fail});
  const cancel = useMutation({mutationFn: () => api.cancelLoginRecording(selected!.id, recording!.id), onSuccess: setRecording, onError: fail});
  const progress = useQuery({queryKey: ["login-recording", recording?.id], queryFn: () => api.getLoginRecording(selected!.id, recording!.id), enabled: recording?.status === "RECORDING", refetchInterval: recording?.status === "RECORDING" ? 800 : false, retry: false});
  useEffect(() => {
    ownedRecording.current = recording;
  }, [recording]);
  useEffect(() => {
    const result = progress.data;
    if (!result || result.id !== recording?.id || result.profile_id !== selected?.id) return;
    if (result.status === "DONE") {
      setDraft(current => current ? {...current, ...result.targets} : current); setDirty(true);
    }
    if (result.status !== "RECORDING") setRecording(result);
  }, [progress.data, recording?.id, selected?.id]);
  const busy = create.isPending || save.isPending || publish.isPending || disable.isPending || remove.isPending || start.isPending || cancel.isPending || createGroup.isPending || linkGroup.isPending || removeGroup.isPending;
  const active = recording?.status === "RECORDING";
  const complete = draft && Object.keys(targetNames).every(key => draft[key as keyof typeof targetNames]) && draft.success_rule;
  function change(next: LoginConfiguration) {setDraft(next); setDirty(true); setError(null);}
  return <main className="page-shell">
    <div className="page-heading"><p className="eyebrow">Acessos reutilizáveis</p><h1>Acessos</h1><p className="muted">Um acesso, vários destinos. Agrupe sites que usam as mesmas credenciais e configure os campos de cada URL.</p></div>
    <section className="card form-card"><h2>Grupos de acesso</h2><p className="muted">Exemplo: Energisa com destinos SGIND e IQOS. O grupo compartilha o preenchimento; cada destino mantém sua sessão e validação.</p><form onSubmit={event => {event.preventDefault(); createGroup.mutate();}}><label>Nome do grupo<input required maxLength={100} value={groupName} placeholder="Energisa, Google, meus portais…" disabled={busy || active} onChange={event => setGroupName(event.target.value)} /></label><button className="secondary-button" disabled={busy || active}>Criar grupo</button></form><div className="report-picker">{groups.data?.items.map(group => <span className="badge" key={group.id}>{group.name} · {profiles.data?.items.filter(profile => profile.group_id === group.id).length ?? 0} destinos <button type="button" className="text-button" disabled={busy || active} aria-label={`Excluir grupo ${group.name}`} onClick={() => {if (window.confirm(`Excluir o grupo "${group.name}"? Desvincule os perfis associados antes de excluir.`)) {setError(null); removeGroup.mutate(group.id);}}}>Excluir</button></span>)}</div></section>
    <section className="card form-card"><h2>Cadastrar login</h2>
      <form onSubmit={event => {event.preventDefault(); setError(null); create.mutate({name: name.trim(), login_url: url.trim(), ...(groupId ? {group_id: Number(groupId)} : {}), ...(templateId ? {template_profile_id: Number(templateId)} : {})});}}>
        <div className="form-grid"><label>Nome do site<input value={name} required maxLength={100} disabled={busy || active} onChange={event => setName(event.target.value)} /></label>
          <label>URL de login<input type="url" value={url} required disabled={busy || active} placeholder="https://site.exemplo/login" onChange={event => setUrl(event.target.value)} /></label></div>
        <div className="form-grid"><label>Grupo de acesso<select disabled={busy || active} value={groupId} onChange={event => setGroupId(event.target.value)}><option value="">Acesso independente</option>{groups.data?.items.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label><label>Reutilizar campos de<select disabled={busy || active} value={templateId} onChange={event => setTemplateId(event.target.value)}><option value="">Identificar novos campos</option>{profiles.data?.items.filter(profile => profile.status !== "DISABLED").map(profile => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</select></label></div>
        {templateId ? <p className="muted">Somente os seletores são copiados. Confirme a regra de sucesso para esta URL antes de publicar.</p> : null}
        <button className="primary-button" disabled={busy || active}>Cadastrar login</button>
      </form>
    </section>
    <section className="card"><h2>Perfis cadastrados</h2>
      {profiles.isLoading ? <p>Carregando perfis…</p> : profiles.isError ? <p role="alert">Não foi possível carregar os perfis.</p> : <div className="report-picker">{profiles.data?.items.map(profile => <button type="button" key={profile.id} disabled={busy || active} className={selected?.id === profile.id ? "primary-button" : "secondary-button"} onClick={() => select(profile)}>{profile.name} · v{profile.current_version} · {profile.status === "READY" ? "Configuração pronta" : profile.status === "DISABLED" ? "Desativado" : "Rascunho"}</button>)}</div>}
    </section>
    {selected && draft ? <section className="card form-card"><h2>{selected.name}</h2><p className="muted">{draft.login_url}</p>
      <label>URL de login deste acesso<input type="url" required maxLength={2048} disabled={busy || active || selected.status === "DISABLED"} value={draft.login_url} onChange={event => change({...draft, login_url: event.target.value, username_target: null, password_target: null, submit_target: null, success_rule: null})} /></label>
      <p className="muted">Altere o caminho da página neste site. Para outro site, cadastre um novo acesso. Após alterar a URL, identifique os campos e configure a confirmação de acesso novamente.</p>
      <label>Grupo deste destino<select disabled={busy || active || dirty} value={selected.group_id ?? ""} onChange={event => linkGroup.mutate(event.target.value ? Number(event.target.value) : null)}><option value="">Acesso independente</option>{groups.data?.items.map(group => <option key={group.id} value={group.id}>{group.name}</option>)}</select></label>
      <p>Abra o Edge e aponte o campo de usuário, o campo de senha e o botão de entrada. Não digite credenciais durante o cadastro.</p>
      <button type="button" className="primary-button" disabled={busy || active || selected.status === "DISABLED" || dirty} onClick={() => {setError(null); start.mutate();}}>Identificar campos no Edge</button>
      {dirty ? <p className="muted">Salve as alterações antes de abrir uma nova seleção ou publicar.</p> : null}
      {active ? <div><p role="status">Selecionando no Edge… {Object.keys(progress.data?.targets ?? {}).length}/3 campos.</p><button type="button" disabled={cancel.isPending} onClick={() => cancel.mutate()}>Cancelar seleção</button></div> : null}
      {recording?.status === "DONE" ? <p role="status">Campos identificados. Configure a confirmação de acesso e salve o perfil.</p> : null}
      {recording?.status === "FAILED" || progress.isError ? <p role="alert">A seleção não foi concluída. Verifique a URL e tente novamente.</p> : null}
      <div className="recipe-field-editor">{Object.entries(targetNames).map(([key, label]) => <div key={key}><strong>{label}</strong><p className="muted">{draft[key as keyof typeof targetNames]?.selector ?? "Ainda não identificado"}</p></div>)}</div>
      <div className="recipe-field-editor"><h3>Confirmar que o login foi concluído</h3>
        <label>Tipo de confirmação<select disabled={busy || active} value={draft.success_rule?.kind ?? "url"} onChange={event => change({...draft, success_rule: event.target.value === "url" ? {kind: "url", url: ""} : {kind: "marker", target: {selector: "", frames: []}}})}><option value="url">URL final</option><option value="marker">Elemento da página autenticada</option></select></label>
        {(draft.success_rule?.kind ?? "url") === "url" ? <label>URL após entrar<input type="url" disabled={busy || active} value={draft.success_rule?.url ?? ""} placeholder="https://site.exemplo/home" onChange={event => change({...draft, success_rule: {kind: "url", url: event.target.value}})} /></label> : <label>Seletor do elemento autenticado<input disabled={busy || active} value={draft.success_rule?.target?.selector ?? ""} placeholder="#pagina-inicial" onChange={event => change({...draft, success_rule: {kind: "marker", target: {selector: event.target.value, frames: []}}})} /></label>}
        <p className="muted">O formulário de senha também precisa deixar de estar visível. MFA, CAPTCHA e páginas com várias etapas exigem adaptação.</p>
      </div>
      <div className="button-row"><button type="button" className="primary-button" disabled={busy || active || !dirty || selected.status === "DISABLED"} onClick={() => save.mutate()}>Salvar perfil</button><button type="button" disabled={busy || active || dirty || !complete || selected.status === "DISABLED"} onClick={() => publish.mutate()}>Publicar perfil</button><button type="button" disabled={busy || active || selected.status === "DISABLED"} onClick={() => disable.mutate()}>Desativar perfil</button><button type="button" disabled={busy || active} onClick={() => {if (window.confirm(`Excluir permanentemente o perfil "${selected.name}" e suas versões? Esta ação não pode ser desfeita.`)) {setError(null); remove.mutate(selected.id);}}}>Excluir perfil</button></div>
    </section> : null}
    {error ? <p className="form-error" role="alert">{error}</p> : null}
  </main>;
}
