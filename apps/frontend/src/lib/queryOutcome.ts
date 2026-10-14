export type Step=Record<string,unknown>;
export type Recipe=Record<string,unknown>&{steps:Step[]};
export type QueryOutcomeConfig={confirmationSelector:string;confirmationAttribute:string;container:string;resultAttribute:string;dataSelector:string;emptySelector:string;errorSelector:string;timeoutMs:number};
export const queryIdentityAttributes=['data-query-id','data-request-id'];
const fail=()=>{throw new Error('Revise a confirmação, os estados do resultado e o prazo da consulta.');};
const text=(value:unknown):value is string=>typeof value==='string' && value.trim().length>0 && value.length<=2048;

export function canConfigureQuery(recipe:Recipe,stepId:string):boolean {
  const step=recipe.steps.find(s=>s.id===stepId);
  if(!step || !['click','query'].includes(String(step.action))) return false;
  const retry=step.retry as Step|undefined;
  return (step.button??'left')==='left' && (step.click_count??1)===1 && (retry?.max_attempts??1)===1 &&
    !('generation' in step) && !('baseline' in step) &&
    !recipe.steps.some(s=>s.generation===stepId || s.baseline===stepId);
}

export function configureQuery(input:Recipe,stepId:string,config:QueryOutcomeConfig):Recipe {
  if(!canConfigureQuery(input,stepId) ||
     ![config.confirmationSelector,config.container,config.dataSelector,config.emptySelector,config.errorSelector].every(text) ||
     !queryIdentityAttributes.includes(config.confirmationAttribute) || !queryIdentityAttributes.includes(config.resultAttribute) ||
     new Set([config.dataSelector.trim(),config.emptySelector.trim(),config.errorSelector.trim()]).size!==3 ||
     !Number.isInteger(config.timeoutMs) || config.timeoutMs<1000 || config.timeoutMs>900000) return fail();
  const recipe=structuredClone(input), step=recipe.steps.find(s=>s.id===stepId)!;
  if(!text(step.selector) || (step.frames!==undefined && (!Array.isArray(step.frames) || step.frames.length>16 || !step.frames.every(text)))) return fail();
  const allowed=new Set(['id','action','selector','frames','timeout_ms','retry','label','button','click_count','confirmation','result']);
  if(Object.keys(step).some(k=>!allowed.has(k))) return fail();
  delete step.button;delete step.click_count;
  Object.assign(step,{action:'query',timeout_ms:config.timeoutMs,
    confirmation:{selector:config.confirmationSelector.trim(),attribute:config.confirmationAttribute},
    result:{container:config.container.trim(),attribute:config.resultAttribute,
      outcomes:{data:config.dataSelector.trim(),empty:config.emptySelector.trim(),error:config.errorSelector.trim()}}});
  return recipe;
}

export function removeQuery(input:Recipe,stepId:string):Recipe {
  const recipe=structuredClone(input), step=recipe.steps.find(s=>s.id===stepId);
  if(!step || step.action!=='query') return fail();
  delete step.confirmation;delete step.result;delete step.timeout_ms;
  step.action='click';return recipe;
}

export function queryConfig(step:Step):QueryOutcomeConfig {
  const c=step.confirmation as Step|undefined,r=step.result as Step|undefined,o=r?.outcomes as Step|undefined;
  return {confirmationSelector:String(c?.selector??''),confirmationAttribute:String(c?.attribute??'data-query-id'),
    container:String(r?.container??''),resultAttribute:String(r?.attribute??'data-query-id'),
    dataSelector:String(o?.data??''),emptySelector:String(o?.empty??''),errorSelector:String(o?.error??''),
    timeoutMs:step.action==='query'?Number(step.timeout_ms??180000):180000};
}
