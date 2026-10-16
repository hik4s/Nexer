import {describe, expect, it} from 'vitest';
import {ensureDownloadValidations, validationForDownload} from './guidedFileValidation';

const recipe = {schema_version: 1, name: 'Recorded', variables: {}, output: {type: 'file'},
  steps: [{id:'open', action:'navigate', url:'https://example.test'},
    {id:'fetch', action:'download', selector:'#export', filename:'{{file_name}}', preserve_filename:true}]};

describe('guided file validations', () => {
  it('adds a linked validation directly after a download without inventing a filename', () => {
    const original = structuredClone(recipe);
    const result = ensureDownloadValidations(recipe);
    expect(recipe).toEqual(original);
    expect(result.steps.map(s => s.action)).toEqual(['navigate','download','validate_file']);
    expect(result.steps[2]).toMatchObject({action:'validate_file', source_download:'fetch', min_size:1});
    expect(result.steps[2]).not.toHaveProperty('path');
    expect(validationForDownload(result, 'fetch')).toBeTruthy();
  });
  it('is idempotent and never inserts an extra validation for a linked source', () => {
    const once = ensureDownloadValidations(recipe);
    expect(ensureDownloadValidations(once)).toBe(once);
    expect(ensureDownloadValidations(once).steps).toHaveLength(3);
  });
  it('allocates unique step identifiers and validates each download independently', () => {
    const imported = {...recipe, steps: [
      {id:'file_check_fetch',action:'wait_for',selector:'#x'},
      ...recipe.steps,
      {id:'other',action:'download',selector:'#other',filename:'other.csv'}
    ]};
    const result = ensureDownloadValidations(imported);
    const ids = result.steps.map(s=>s.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(result.steps.filter(s=>s.action==='validate_file').map(s=>(s as {source_download?:string}).source_download)).toEqual(['fetch','other']);
  });
  it('keeps workflows without downloads unchanged and does not replace existing explicit validation', () => {
    const without = {...recipe,steps:recipe.steps.slice(0,1)};
    expect(ensureDownloadValidations(without)).toBe(without);
    const withLinked = {...recipe,steps:[...recipe.steps,{id:'explicit',action:'validate_file',source_download:'fetch',min_size:64}]};
    expect(ensureDownloadValidations(withLinked)).toBe(withLinked);
  });
});
