import {useState} from 'react';
import {configureDownloadGeneration, removeDownloadGeneration, identityAttributes, DownloadGenerationConfig} from '../lib/downloadGeneration';
type Step=Record<string,unknown>;
type Recipe=Record<string,unknown>&{steps:Step[]};
export function DownloadGenerationEditor({recipe,downloadId,onChange,onDirty}: {recipe:Recipe;downloadId:string;onChange:(recipe:Recipe)=>void;onDirty:(dirty:boolean)=>void}) {
  const download=recipe.steps.find(s=>s.id===downloadId)!;
  const request=recipe.steps.find(s=>s.id===download.generation);
  const collection=download.collection as Step;
  const confirmation=request?.confirmation as Step|undefined;
  const [config,setConfig]=useState<DownloadGenerationConfig>({triggerId:String(request?.id??''),container:String(collection.container??''),confirmationSelector:String(confirmation?.selector??''),confirmationAttribute:String(confirmation?.attribute??''),identityAttribute:String(collection.identity_attribute??''),shared:collection.shared===true,timeoutMs:Number(download.timeout_ms??180000)});
  const [error,setError]=useState('');
  function update<K extends keyof DownloadGenerationConfig>(key:K,value:DownloadGenerationConfig[K]) {setConfig(c=>({...c,[key]:value}));onDirty(true);}
  function apply(remove=false) {try {onChange(remove?removeDownloadGeneration(recipe,downloadId):configureDownloadGeneration(recipe,downloadId,config));onDirty(false);setError('');} catch {setError('Revise a ação de geração, os seletores e os vínculos. Nenhuma alteração foi aplicada.');}}
  return <fieldset className="download-generation-editor"><legend>Vincular download à solicitação</legend><p className="muted">Use uma confirmação que informe o nome completo do arquivo ou um identificador da solicitação. O padrão do nome sozinho não identifica o seu relatório em uma central compartilhada.</p>
    <label>Ação que gera o relatório<select value={config.triggerId} onChange={e=>update('triggerId',e.target.value)}><option value="">Selecione uma ação anterior</option>{recipe.steps.slice(0,recipe.steps.indexOf(download)).filter(s=>s.action==='click'||s.id===request?.id).map(s=><option key={String(s.id)} value={String(s.id)}>{String(s.id)}</option>)}</select></label>
    <label>Contêiner da central<input value={config.container} onChange={e=>update('container',e.target.value)}/></label>
    <label>Seletor da confirmação<input value={config.confirmationSelector} onChange={e=>update('confirmationSelector',e.target.value)}/></label>
    <label>Identificação na confirmação<select value={config.confirmationAttribute} onChange={e=>update('confirmationAttribute',e.target.value)}><option value="">Texto: nome completo do arquivo</option>{identityAttributes.map(a=><option key={a}>{a}</option>)}</select></label>
    <label>Identificação na linha<select value={config.identityAttribute} onChange={e=>update('identityAttribute',e.target.value)}><option value="">Nome completo do arquivo</option>{identityAttributes.map(a=><option key={a}>{a}</option>)}</select></label>
    <label>Prazo por etapa (minutos)<input type="number" min={1} max={15} value={config.timeoutMs/60000} onChange={e=>update('timeoutMs',Number(e.target.value)*60000)}/></label>
    <label className="download-generation-shared"><input type="checkbox" checked={config.shared} onChange={e=>update('shared',e.target.checked)}/>Central compartilhada por várias solicitações</label>
    {error?<p role="alert">{error}</p>:null}<button type="button" className="secondary-button" onClick={()=>apply()}>Aplicar vínculo</button>{download.generation?<button type="button" className="secondary-button" onClick={()=>apply(true)}>Remover vínculo</button>:null}
  </fieldset>;
}
