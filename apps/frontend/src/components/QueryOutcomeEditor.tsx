import {useRef,useState} from 'react';
import {configureQuery,removeQuery,queryConfig,queryIdentityAttributes,type Recipe,type Step,type QueryOutcomeConfig} from '../lib/queryOutcome';

type Props={recipe:Recipe;stepId:string;originalStep?:Step;onChange:(recipe:Recipe)=>void;onDirty:(dirty:boolean)=>void};
export function QueryOutcomeEditor({recipe,stepId,originalStep,onChange,onDirty}:Props){
  const step=recipe.steps.find(s=>s.id===stepId)!;
  const original=useRef<Step|null>(originalStep?structuredClone(originalStep):step.action==='click'?structuredClone(step):null);
  const [config,setConfig]=useState(()=>queryConfig(step));
  const [error,setError]=useState('');
  function update<K extends keyof QueryOutcomeConfig>(key:K,value:QueryOutcomeConfig[K]){
    setConfig(c=>({...c,[key]:value}));onDirty(true);
  }
  function apply(){try{onChange(configureQuery(recipe,stepId,config));onDirty(false);setError('');}
    catch{onDirty(true);setError('Revise a confirmação, os estados e o prazo. Nenhuma alteração foi aplicada.');}}
  function remove(){try{
    const updated=removeQuery(recipe,stepId);
    if(original.current) updated.steps=updated.steps.map(s=>s.id===stepId?structuredClone(original.current!):s);
    onChange(updated);setConfig(queryConfig(updated.steps.find(s=>s.id===stepId)!));onDirty(false);setError('');
  }catch{setError('Não foi possível restaurar o clique.');}}
  const fields:[keyof QueryOutcomeConfig,string][]=[['confirmationSelector','Confirmação da consulta'],['container','Contêiner do resultado'],['dataSelector','Estado com dados'],['emptySelector','Estado sem dados'],['errorSelector','Estado de erro']];
  return <fieldset className="query-outcome-editor"><legend>Verificar resultado da consulta · {stepId}</legend>
    <p className="muted">Use uma identificação fornecida pelo site que vincule esta solicitação ao resultado. Sem dados ou com erro, as etapas seguintes serão interrompidas. A identificação não é gravada.</p>
    {fields.map(([key,label])=><label key={key}>{label}<input value={String(config[key])} maxLength={2048} onChange={e=>update(key,e.target.value)}/></label>)}
    <label>Identificação na confirmação<select value={config.confirmationAttribute} onChange={e=>update('confirmationAttribute',e.target.value)}>{queryIdentityAttributes.map(a=><option key={a}>{a}</option>)}</select></label>
    <label>Identificação no resultado<select value={config.resultAttribute} onChange={e=>update('resultAttribute',e.target.value)}>{queryIdentityAttributes.map(a=><option key={a}>{a}</option>)}</select></label>
    <label>Prazo total (segundos)<input type="number" min={1} max={900} value={config.timeoutMs/1000} onChange={e=>update('timeoutMs',Number(e.target.value)*1000)}/></label>
    {error?<p role="alert">{error}</p>:null}
    <div className="button-row"><button type="button" className="secondary-button" onClick={apply}>Aplicar consulta</button>
      <button type="button" className="secondary-button" onClick={()=>{setConfig(queryConfig(step));onDirty(false);setError('');}}>Descartar edição</button>
      {step.action==='query'?<button type="button" className="secondary-button" onClick={remove}>Voltar ao clique</button>:null}</div>
  </fieldset>;
}
