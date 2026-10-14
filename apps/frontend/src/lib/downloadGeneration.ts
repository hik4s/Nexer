type Step = Record<string, unknown>;
type Recipe = Record<string, unknown> & {steps: Step[]};
export type DownloadGenerationConfig = {triggerId:string; container:string; confirmationSelector:string; confirmationAttribute:string; identityAttribute:string; shared:boolean; timeoutMs:number};
export const identityAttributes = ['data-job-id','data-report-id','data-download-id'];
const fail = () => {throw new Error('Revise a geração, a confirmação e os seletores da central.');};
function references(recipe:Recipe, requestId:unknown) {return recipe.steps.filter(s=>s.generation===requestId);}
export function removeDownloadGeneration(input:Recipe, downloadId:string):Recipe {
  const recipe=structuredClone(input);
  const download=recipe.steps.find(s=>s.id===downloadId);
  if(!download) return fail();
  if(!download.generation) return recipe;
  const request=recipe.steps.find(s=>s.id===download.generation);
  if(!request || references(recipe,request.id).length!==1) return fail();
  const baseline=recipe.steps.find(s=>s.id===request.baseline && s.action==='snapshot_downloads');
  if(!baseline || recipe.steps.filter(s=>s.baseline===baseline.id).length!==1) return fail();
  recipe.steps=recipe.steps.filter(s=>s.id!==baseline.id);
  request.action='click'; delete request.baseline; delete request.confirmation; delete request.timeout_ms;
  delete download.generation; delete download.timeout_ms;
  const collection=download.collection as Step;
  delete collection.container; delete collection.identity_attribute; delete collection.shared;
  return recipe;
}
export function configureDownloadGeneration(input:Recipe, downloadId:string, config:DownloadGenerationConfig):Recipe {
  let recipe=structuredClone(input);
  const original=recipe.steps.find(s=>s.id===downloadId);
  if(original?.generation) recipe=removeDownloadGeneration(recipe,downloadId);
  const index=recipe.steps.findIndex(s=>s.id===downloadId);
  const download=recipe.steps[index];
  const triggerIndex=recipe.steps.findIndex(s=>s.id===config.triggerId);
  const trigger=recipe.steps[triggerIndex];
  if(!download?.collection || !trigger || triggerIndex>=index || trigger.action!=='click' ||
     (trigger.button??'left')!=='left' || (trigger.click_count??1)!==1 ||
     ((trigger.retry as Step|undefined)?.max_attempts??1)!==1 || ((download.retry as Step|undefined)?.max_attempts??1)!==1 ||
     JSON.stringify(trigger.frames??[])!==JSON.stringify(download.frames??[]) ||
     recipe.steps.slice(triggerIndex+1,index).some(s=>s.action==='switch_tab'||s.action==='close_tab') ||
     !config.container.trim() || !config.confirmationSelector.trim() ||
     (config.confirmationAttribute && !identityAttributes.includes(config.confirmationAttribute)) ||
     (config.identityAttribute && !identityAttributes.includes(config.identityAttribute)) ||
     !Number.isInteger(config.timeoutMs) || config.timeoutMs<60000 || config.timeoutMs>900000) return fail();
  let baselineId=`${String(trigger.id)}_downloads_before`, suffix=1;
  while(recipe.steps.some(s=>s.id===baselineId)) baselineId=`${String(trigger.id)}_downloads_before_${suffix++}`;
  const collection:Step={...(download.collection as Step),container:config.container.trim(),shared:config.shared};
  if(config.identityAttribute) collection.identity_attribute=config.identityAttribute;
  else delete collection.identity_attribute;
  const confirmation:Step={selector:config.confirmationSelector.trim()};
  if(config.confirmationAttribute) confirmation.attribute=config.confirmationAttribute;
  Object.assign(trigger,{action:'request_download',baseline:baselineId,confirmation,timeout_ms:config.timeoutMs});
  Object.assign(download,{generation:trigger.id,collection,timeout_ms:config.timeoutMs});
  const snapshot:Step={id:baselineId,action:'snapshot_downloads',collection:structuredClone(collection)};
  if(trigger.frames) snapshot.frames=structuredClone(trigger.frames);
  recipe.steps.splice(triggerIndex,0,snapshot);
  return recipe;
}
export function downloadErrorMessage(code:string|null):string {
  const messages:Record<string,string>={
    DOWNLOAD_MATCH_AMBIGUOUS:'A central contém mais de um resultado para esta solicitação.',
    DOWNLOAD_BASELINE_UNAVAILABLE:'A central de downloads não foi encontrada. Revise o seletor.',
    DOWNLOAD_BASELINE_INCOMPLETE:'Não foi possível verificar toda a central de downloads.',
    DOWNLOAD_IDENTITY_INVALID:'A central não apresentou uma identificação válida e única.',
    DOWNLOAD_CONTEXT_MISMATCH:'A página ou o contexto mudou durante a geração.',
    DOWNLOAD_CONFIRMATION_AMBIGUOUS:'A confirmação da solicitação não é única.',
    DOWNLOAD_CONFIRMATION_TIMEOUT:'A confirmação de uma nova solicitação não apareceu no prazo.',
    DOWNLOAD_GENERATION_TIMEOUT:'O relatório desta solicitação não ficou disponível no prazo.',
    DOWNLOAD_BUTTON_AMBIGUOUS:'Há mais de um botão de download na linha selecionada.',
    DOWNLOAD_GENERATION_UNAVAILABLE:'A referência à solicitação não está disponível.',
    DOWNLOAD_AUTHORIZATION_REVOKED:'O acesso foi interrompido enquanto o relatório era aguardado.',
    DOWNLOAD_GENERATION_FAILED:'Não foi possível concluir o download desta solicitação.',
  };
  return messages[code??'']??'A automação falhou. Revise o fluxo e tente novamente.';
}
