import {useEffect, useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Link} from 'react-router-dom';
import {api, type TargetPicking} from '../lib/api';
import {fieldLabel, type ParameterDeclaration} from '../components/RecipeField';

/** Local authenticated diagnostics. The browser's DOM and credentials never cross the API. */
export function DeveloperEyePage() {
  const [poll, setPoll] = useState(true);
  const [url, setUrl] = useState('');
  const [selector, setSelector] = useState('');
  const [picker, setPicker] = useState<TargetPicking | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [probe, setProbe] = useState<Awaited<ReturnType<typeof api.probeDeveloperSelector>> | null>(null);
  const [recipeIdentity, setRecipeIdentity] = useState('');
  const [recipeStatus, setRecipeStatus] = useState('');
  const [validatingRecipe, setValidatingRecipe] = useState(false);
  const [flowId, versionNumber] = recipeIdentity.split(':').map(Number);
  const flows = useQuery({queryKey:['developer-eye','flows'],
    queryFn:()=>api.listAutomations({status:'PUBLISHED',limit:100}),retry:false});
  const recipe = useQuery({queryKey:['developer-eye','recipe',flowId,versionNumber],
    enabled: Number.isInteger(flowId) && flowId > 0 && Number.isInteger(versionNumber) && versionNumber > 0,
    queryFn:()=>api.getAutomationVersion(flowId,versionNumber),retry:false});
  const variables = Object.entries((recipe.data?.recipe.variables ?? {}) as Record<string,ParameterDeclaration>)
    .filter(([, declaration])=>!declaration.secret);
  const recipeSteps = Array.isArray(recipe.data?.recipe.steps) ? recipe.data.recipe.steps : [];
  const validateRecipe = async () => {
    setValidatingRecipe(true);setRecipeStatus('');
    try {
      const result=await api.testAutomationVersion(flowId,versionNumber);
      setRecipeStatus(result.test_status === 'PASSED'
        ? 'Contrato da receita validado. Isso não executa ações no site.'
        : 'A receita precisa de revisão antes da execução.');
    } catch {setRecipeStatus('Não foi possível validar o contrato desta receita.');}
    finally {setValidatingRecipe(false);}
  };
  const diagnostics = useQuery({
    queryKey: ['developer-eye', 'diagnostics'], queryFn: api.getDiagnostics,
    retry: false, refetchInterval: poll ? 5000 : false,
  });
  const executions = useQuery({
    queryKey: ['developer-eye', 'executions'], queryFn: () => api.listExecutions({limit:10}),
    retry: false, refetchInterval: poll ? 5000 : false,
  });
  const selection = useQuery({
    queryKey: ['developer-eye','picker',picker?.id], enabled: picker?.status === 'RECORDING',
    queryFn: () => api.getTargetPicking(picker!.id), retry: false,
    refetchInterval: picker?.status === 'RECORDING' ? 1200 : false,
  });
  useEffect(() => {
    if (selection.data && selection.data.id === picker?.id) setPicker(selection.data);
  }, [selection.data, picker?.id]);
  const reload = () => {void diagnostics.refetch(); void executions.refetch();};
  const openVisual = async () => {
    if (!url.trim()) {setMessage('Informe a URL do site primeiro.');return;}
    setBusy(true);setMessage('');setProbe(null);
    try {
      const started = await api.startTargetPicking(url, 'element');
      setPicker(started);
      setMessage('Edge visível iniciado. Navegue no site e clique no elemento que deseja inspecionar.');
    } catch {
      setMessage('Não foi possível abrir o Edge. Revise a URL e feche outras sessões de inspeção.');
    } finally {setBusy(false);}
  };
  const testHeadless = async () => {
    if (!url.trim() || !selector.trim()) {setMessage('Informe a URL e um seletor para testar.');return;}
    setBusy(true);setMessage('');setProbe(null);
    try {setProbe(await api.probeDeveloperSelector(url,selector));}
    catch {setMessage('O teste headless falhou. Confira a URL e o seletor.');}
    finally {setBusy(false);}
  };
  const cancel = async () => {
    if (!picker || picker.status !== 'RECORDING') return;
    setBusy(true);
    try {setPicker(await api.cancelTargetPicking(picker.id));setMessage('Inspeção encerrada.');}
    catch {setMessage('Não foi possível encerrar a inspeção.');}
    finally {setBusy(false);}
  };
  const copy = async () => {
    if (!picker?.target?.selector) return;
    try {await navigator.clipboard.writeText(picker.target.selector);setMessage('Seletor copiado.');}
    catch {setMessage('Cópia indisponível neste navegador. Selecione o texto manualmente.');}
  };
  const probeState = ({
    FOUND:'Alvo encontrado', NOT_FOUND:'Alvo não encontrado', AMBIGUOUS:'Seletor ambíguo (mais de um alvo)',
    PAGE_UNAVAILABLE:'Página indisponível neste teste', CROSS_ORIGIN_REDIRECT:'Redirecionamento para outra origem'
  } as Record<string,string>);
  return <main className="page-shell">
    <div className="page-heading">
      <p className="eyebrow">Ferramentas locais</p>
      <h1>Eye Developer</h1>
      <p className="muted">Inspecione seletores e o estado do Nexer sem modificar o código. Somente sessões locais autenticadas.</p>
    </div>
    <section className="card" aria-label="Estado do Nexer">
      <h2>Painel de operação</h2>
      <label className="checkbox-label"><input type="checkbox" checked={poll} onChange={e=>setPoll(e.target.checked)}/>
        Atualizar automaticamente a cada 5 segundos</label>
      <button type="button" className="secondary-button" onClick={reload}>Atualizar agora</button>
      {diagnostics.isError ? <p role="alert">Não foi possível consultar o diagnóstico.</p> :
        <p role="status">API: {diagnostics.data?.status ?? 'Carregando'} ·
          Banco: {diagnostics.data?.database.status ?? '…'} ·
          Workers online: {diagnostics.data?.workers.online ?? '…'} /
          {diagnostics.data?.workers.total ?? '…'}</p>}
      <h3>Últimas execuções</h3>
      {executions.isError ? <p role="alert">Não foi possível consultar as execuções.</p> :
        executions.data?.items.length ? <ul>{executions.data.items.map(item=>
          <li key={item.id}><Link to={`/executions/${item.id}`}>Execução #{item.id}</Link>
            {' · '}{item.status} {item.cancel_requested ? '· cancelamento solicitado' : ''}
          </li>)}</ul> : <p className="muted">Nenhuma execução registrada.</p>}
    </section>
    <section className="card" aria-label="Laboratório do navegador">
      <h2>Laboratório do Edge</h2>
      <p className="muted">Headless testa o seletor sem abrir janela; Visual abre um Edge separado para escolher o alvo.
        Nenhum desses modos acompanha ou interfere em uma execução do worker que já esteja aberta.</p>
      <label>Endereço para inspeção
        <input type="url" value={url} maxLength={2048} placeholder="https://seu-site/#/pagina"
          onChange={e=>{setUrl(e.target.value);setProbe(null);}}/>
      </label>
      <label>Seletor CSS a verificar
        <input value={selector} maxLength={2048} placeholder="#dataInicio, [aria-label='Pesquisar']"
          onChange={e=>{setSelector(e.target.value);setProbe(null);}}/>
      </label>
      <div className="button-row">
        <button type="button" className="primary-button" disabled={busy || !url.trim() || !selector.trim()} onClick={testHeadless}>
          {busy ? 'Aguarde…' : 'Testar seletor (headless)'}
        </button>
        <button type="button" className="secondary-button" disabled={busy || !url.trim() || picker?.status === 'RECORDING'}
          onClick={openVisual}>Abrir inspeção visual no Edge</button>
        {picker?.status === 'RECORDING' ? <button type="button" className="secondary-button" disabled={busy} onClick={cancel}>
          Encerrar inspeção</button> : null}
      </div>
      {probe ? <div role="status" className="card">
        <strong>{probeState[probe.status] ?? 'Resultado não identificado'}</strong>
        <p>Alvos: {probe.matches === 2 ? '2 ou mais' : probe.matches} ·
          Visível: {probe.visible ? 'Sim' : 'Não'} ·
          Habilitado: {probe.enabled ? 'Sim' : 'Não'} ·
          Tempo: {probe.elapsed_ms} ms</p>
        <p className="muted">A inspeção não usa sua sessão corporativa: um elemento protegido por login pode não estar acessível.</p>
      </div> : null}
      {picker ? <div role="status" className="card">
        <p>Inspeção visual: {picker.status === 'RECORDING' ? 'Aguardando seleção no Edge' :
          picker.status === 'DONE' ? 'Concluída' : picker.status === 'CANCELLED' ? 'Cancelada' : 'Falhou'}</p>
        {picker.target?.selector ? <>
          <label>Seletor selecionado<input readOnly value={picker.target.selector}/></label>
          <button type="button" className="secondary-button" onClick={copy}>Copiar seletor</button>
          <button type="button" className="secondary-button" onClick={()=>setSelector(picker.target!.selector)}>
            Usar no teste headless</button>
        </> : null}
      </div> : null}
      {selection.isError ? <p role="alert">Acompanhamento da inspeção indisponível.</p> : null}
      {message ? <p role="status">{message}</p> : null}
    </section>
    <section className="card" aria-label="Inspeção de receitas">
      <h2>Analisador de receitas</h2>
      <p className="muted">Confira nomes, formatos de campos e ordem das ações publicadas.
        Valores, credenciais e seletores privados não são mostrados neste painel.</p>
      <label>Fluxo publicado
        <select value={recipeIdentity} onChange={event=>{setRecipeIdentity(event.target.value);setRecipeStatus('');}}>
          <option value="">Selecione um fluxo…</option>
          {flows.data?.items.filter(item=>item.current_version).map(item=>
            <option value={`${item.id}:${item.current_version}`} key={item.id}>
              {item.name} · versão {item.current_version}
            </option>)}
        </select>
      </label>
      {flows.isError || recipe.isError ? <p role="alert">Não foi possível consultar os fluxos publicados.</p> : null}
      {recipe.data ? <>
        <h3>Campos sem valores</h3>
        {variables.length ? <ul>{variables.map(([key,declaration])=>
          <li key={key}><strong>{fieldLabel(key,declaration)}</strong> ·
            {declaration.field?.control ?? declaration.type ?? 'texto'}
            {declaration.field?.site_format ? ` · ${declaration.field.site_format}` : ''}
          </li>)}</ul> : <p className="muted">Esta receita não define parâmetros editáveis.</p>}
        <h3>Sequência da automação</h3>
        <ol>{recipeSteps.map((step,index)=><li key={index}>
          {typeof step.action === 'string' ? step.action : 'Etapa não identificada'}
        </li>)}</ol>
        <button type="button" className="secondary-button" disabled={validatingRecipe} onClick={validateRecipe}>
          {validatingRecipe ? 'Validando…' : 'Validar contrato desta receita'}
        </button>
        {recipeStatus ? <p role="status">{recipeStatus}</p> : null}
      </> : recipeIdentity ? <p className="muted">Carregando receita…</p> : null}
    </section>
    <section className="card">
      <h2>Limites desta versão</h2>
      <p className="muted">O Edge visual é uma sessão de inspeção. Para observar uma execução real em uma janela,
        será necessário configurar o worker para modo headed antes de iniciar a tarefa; isso ainda não é controlado
        por esta tela. Nenhum HTML, texto de relatório, senha, cookie ou screenshot é salvo no Eye Developer.</p>
    </section>
  </main>;
}
