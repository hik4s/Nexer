import {describe, expect, it} from 'vitest';
import {configureQuery, removeQuery, type QueryOutcomeConfig} from './queryOutcome';
import {executionErrorMessage} from './executionErrors';

export const config:QueryOutcomeConfig={confirmationSelector:'#c',confirmationAttribute:'data-query-id',container:'#r',resultAttribute:'data-query-id',dataSelector:'.data',emptySelector:'.empty',errorSelector:'.error',timeoutMs:180000};
const recipe={schema_version:1,steps:[{id:'q',action:'click',selector:'#search',frames:['iframe'],label:'Consultar'}]};
describe('query configuration',()=>{
  it('converts without mutating, preserves context and removes only query fields',()=>{
    const updated=configureQuery(recipe,'q',config);
    expect(recipe.steps[0].action).toBe('click');
    expect(updated.steps[0]).toMatchObject({id:'q',action:'query',selector:'#search',frames:['iframe'],label:'Consultar',confirmation:{selector:'#c',attribute:'data-query-id'},result:{container:'#r',attribute:'data-query-id',outcomes:{data:'.data',empty:'.empty',error:'.error'}}});
    expect(removeQuery(updated,'q').steps[0]).toEqual(recipe.steps[0]);
  });
  it('rejects invalid config and conflicting click semantics without partial changes',()=>{
    for(const changes of [{button:'right'},{click_count:2},{retry:{max_attempts:2}},{generation:'x'}]){
      const input={steps:[{...recipe.steps[0],...changes}]};const before=structuredClone(input);
      expect(()=>configureQuery(input,'q',config)).toThrow();expect(input).toEqual(before);
    }
    for(const changes of [{timeoutMs:999},{timeoutMs:900001},{dataSelector:' '},{emptySelector:'.data'},{confirmationAttribute:'value'},{container:'x'.repeat(2049)}])
      expect(()=>configureQuery(recipe,'q',{...config,...changes})).toThrow();
    const linked={steps:[recipe.steps[0],{id:'download',action:'download',generation:'q'}]};
    expect(()=>configureQuery(linked,'q',config)).toThrow();
  });
  it('keeps all safe query diagnostics fixed and hides unknown details',()=>{
    expect(executionErrorMessage('QUERY_NO_DATA')).toBe('Consulta concluída sem dados; etapas seguintes não executadas.');
    expect(executionErrorMessage('QUERY_SITE_ERROR')).toContain('erro');
    expect(executionErrorMessage('DOWNLOAD_MATCH_AMBIGUOUS')).toContain('mais de um resultado');
    expect(executionErrorMessage('private-canary')).not.toContain('private-canary');
  });
});
