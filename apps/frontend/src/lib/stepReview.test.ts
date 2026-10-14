import {describe, expect, it} from 'vitest';
import {repairStep, reviewSteps, hasValidStepIds, type Recipe} from './stepReview';

const recipe:Recipe={variables:{company:{type:'string',label:'Empresa'}},steps:[
  {id:'open',action:'navigate',url:'https://example.invalid'},
  {id:'ready',action:'wait_for',selector:'#old',frames:['iframe'],state:'enabled',learning:{source:'automatic',confidence:'high'}},
  {id:'fill',action:'fill',selector:'#old',frames:['iframe'],value:'{{company}}'},
  {id:'tab',action:'switch_tab',index:1},
  {id:'export',action:'download',selector:'a',filename:'x',collection:{rows:'tr'}},
]};
describe('step review',()=>{
  it('rejects malformed or repeated step identities before review',()=>{
    expect(hasValidStepIds(recipe.steps)).toBe(true);
    for(const steps of [[null],[{id:1}],[{action:'click'}],[{id:' '}],[{id:'same'},{id:'same'}]])
      expect(hasValidStepIds(steps)).toBe(false);
  });
  it('describes sequence and context without displaying execution values',()=>{
    const rows=reviewSteps(recipe);
    expect(rows[2]).toMatchObject({id:'fill',position:3,title:'Preencher campo',parameterLabel:'Empresa',context:'Aba 1 · 1 frame',editable:true});
    expect(rows[4]).toMatchObject({context:'Aba 2 · página principal',editable:false});
    expect(reviewSteps({steps:[{id:'x',action:'fill',selector:'input',value:'private-canary'}]})[0].parameterLabel).toBeUndefined();
    expect(JSON.stringify(reviewSteps({steps:[{id:'x',action:'press',selector:'input',value:'private-canary'}]}))).not.toContain('private-canary');
  });
  it('repairs only the selected target and its associated automatic wait',()=>{
    const before=structuredClone(recipe);
    const updated=repairStep(recipe,'fill',{selector:'#new',syncWait:true});
    expect(recipe).toEqual(before);
    expect(updated.steps.map(s=>s.id)).toEqual(['open','ready','fill','tab','export']);
    expect(updated.steps[2]).toEqual({...recipe.steps[2],selector:'#new'});
    expect(updated.steps[1]).toEqual({...recipe.steps[1],selector:'#new',learning:{source:'manual',confidence:'high'}});
    expect(updated.variables).toEqual(recipe.variables);
    expect(updated.steps[4]).toEqual(recipe.steps[4]);
  });
  it('keeps manual, unrelated and different-frame waits unchanged',()=>{
    for(const change of [{learning:{source:'manual',confidence:'high'}},{frames:[]},{selector:'#other'}]){
      const input=structuredClone(recipe);Object.assign(input.steps[1],change);
      expect(repairStep(input,'fill',{selector:'#new',syncWait:true}).steps[1]).toEqual(input.steps[1]);
    }
    expect(repairStep(recipe,'fill',{selector:'#new',syncWait:false}).steps[1]).toEqual(recipe.steps[1]);
  });
  it('does not turn an unchanged automatic wait into a manual condition',()=>{
    expect(repairStep(recipe,'fill',{selector:'#old',syncWait:true})).toEqual(recipe);
    expect(repairStep(recipe,'ready',{selector:'#old',syncWait:false})).toEqual(recipe);
  });
  it('rejects invalid, unknown, duplicate and specialized targets without mutating',()=>{
    for(const selector of ['', ' ', 'x'.repeat(2049),'{{unknown}}'])
      expect(()=>repairStep(recipe,'fill',{selector,syncWait:true})).toThrow();
    expect(()=>repairStep(recipe,'export',{selector:'button',syncWait:false})).toThrow();
    expect(()=>repairStep(recipe,'missing',{selector:'button',syncWait:false})).toThrow();
    expect(()=>repairStep({steps:[recipe.steps[2],recipe.steps[2]]},'fill',{selector:'button',syncWait:false})).toThrow();
  });
  it('repairs drag origin and destination without changing the action or frame',()=>{
    const input={steps:[{id:'drag',action:'drag',selector:'#from',target_selector:'#to',frames:['iframe']}]};
    expect(repairStep(input,'drag',{selector:'#newFrom',targetSelector:'#newTo',syncWait:false}).steps[0]).toEqual({...input.steps[0],selector:'#newFrom',target_selector:'#newTo'});
    expect(()=>repairStep(input,'drag',{selector:'#newFrom',targetSelector:'',syncWait:false})).toThrow();
  });
});
