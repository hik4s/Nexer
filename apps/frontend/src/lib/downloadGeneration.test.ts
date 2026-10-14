import {describe, it, expect} from 'vitest';
import {configureDownloadGeneration, removeDownloadGeneration, downloadErrorMessage} from './downloadGeneration';
const recipe = {steps: [{id:'generate',action:'click',selector:'#export'}, {id:'get',action:'download',selector:'a',filename:'report',collection:{rows:'#table tr',name:'.name',button:'a',pattern:'{{pattern}}'}}]};
const config = {triggerId:'generate',container:'#table',confirmationSelector:'#confirmation',confirmationAttribute:'data-job-id',identityAttribute:'data-job-id',shared:true,timeoutMs:180000};
describe('download generation',()=>{
  it('allocates a new baseline ID when an imported step already owns the expected ID',()=>{
    const imported={...recipe,steps:[{id:'generate_downloads_before',action:'wait_for',selector:'#ready'},...recipe.steps]};
    const result=configureDownloadGeneration(imported,'get',config);
    const ids=result.steps.map(s=>s.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(result.steps[2].baseline).toBe('generate_downloads_before_1');
    expect(result.steps[0]).toEqual(imported.steps[0]);
  });
  it('builds ordered references without mutating the original and edits without accumulating snapshots',()=>{
    const before=structuredClone(recipe);
    const result=configureDownloadGeneration(recipe,'get',config);
    expect(recipe).toEqual(before);
    expect(result.steps.map(s=>s.action)).toEqual(['snapshot_downloads','request_download','download']);
    expect(result.steps[2].generation).toBe('generate');
    expect(result.steps[0].collection).toEqual(result.steps[2].collection);
    expect(configureDownloadGeneration(result,'get',config).steps).toHaveLength(3);
    const restored=removeDownloadGeneration(result,'get');
    expect(restored.steps.map(s=>s.action)).toEqual(['click','download']);
    expect(restored.steps[1].generation).toBeUndefined();
  });
  it('rejects incompatible triggers, unsafe attributes, retries and missing configuration',()=>{
    for(const change of [{triggerId:'get'},{container:''},{confirmationSelector:''},{confirmationAttribute:'value'},{identityAttribute:'value'},{timeoutMs:100}])
      expect(()=>configureDownloadGeneration(recipe,'get',{...config,...change})).toThrow();
    expect(()=>configureDownloadGeneration({...recipe,steps:[{...recipe.steps[0],retry:{max_attempts:2}},recipe.steps[1]]},'get',config)).toThrow();
  });
  it('does not remove a request shared by another download',()=>{
    const result=configureDownloadGeneration(recipe,'get',config);
    expect(()=>removeDownloadGeneration({...result,steps:[...result.steps,{...result.steps[2],id:'other'}]},'get')).toThrow();
  });
  it('exposes only fixed safe diagnostics',()=>{
    expect(downloadErrorMessage('DOWNLOAD_MATCH_AMBIGUOUS')).toContain('mais de um');
    expect(downloadErrorMessage('secret-canary')).not.toContain('secret-canary');
  });
});
