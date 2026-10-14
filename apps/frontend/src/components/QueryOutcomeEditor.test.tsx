import {describe,expect,it,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {useState} from 'react';
import {QueryOutcomeEditor} from './QueryOutcomeEditor';
const initial={steps:[{id:'q',action:'click',selector:'#search',frames:['iframe'],timeout_ms:3000,button:'left',click_count:1}]};
function Harness({onDirty=vi.fn(),onChange=vi.fn()}){
  const [recipe,setRecipe]=useState<Record<string,unknown>&{steps:Record<string,unknown>[]}>(initial);
  return <QueryOutcomeEditor recipe={recipe} stepId="q" onDirty={onDirty} onChange={r=>{setRecipe(r);onChange(r)}}/>;
}
describe('query outcome editor',()=>{
  it('blocks incomplete config, applies a query and restores original click',async()=>{
    const onDirty=vi.fn(),onChange=vi.fn();render(<Harness onDirty={onDirty} onChange={onChange}/>);
    const user=userEvent.setup();
    await user.click(screen.getByRole('button',{name:'Aplicar consulta'}));
    expect(screen.getByRole('alert')).toBeInTheDocument();expect(onChange).not.toHaveBeenCalled();
    for(const [label,value] of [['Confirmação da consulta','#c'],['Contêiner do resultado','#r'],['Estado com dados','.data'],['Estado sem dados','.empty'],['Estado de erro','.error']])
      fireEvent.change(screen.getByLabelText(label),{target:{value}});
    expect(onDirty).toHaveBeenLastCalledWith(true);
    await user.click(screen.getByRole('button',{name:'Aplicar consulta'}));
    expect(onChange.mock.lastCall?.[0].steps[0]).toMatchObject({action:'query',frames:['iframe']});
    expect(onDirty).toHaveBeenLastCalledWith(false);
    await user.click(screen.getByRole('button',{name:'Voltar ao clique'}));
    expect(onChange.mock.lastCall?.[0]).toEqual(initial);
  });
  it('cancels unapplied editing and rejects an out-of-range timeout',async()=>{
    const onDirty=vi.fn(),onChange=vi.fn();render(<Harness onDirty={onDirty} onChange={onChange}/>);
    fireEvent.change(screen.getByLabelText('Prazo total (segundos)'),{target:{value:'901'}});
    await userEvent.click(screen.getByRole('button',{name:'Aplicar consulta'}));
    expect(screen.getByRole('alert')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button',{name:'Descartar edição'}));
    expect(onDirty).toHaveBeenLastCalledWith(false);expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Prazo total (segundos)')).toHaveValue(180);
  });
});
