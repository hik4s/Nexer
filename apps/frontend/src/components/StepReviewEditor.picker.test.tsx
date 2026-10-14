import {it,expect,vi} from 'vitest';
import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {StepReviewEditor} from './StepReviewEditor';
import {api} from '../lib/api';
vi.mock('../lib/api',()=>({api:{startTargetPicking:vi.fn(async()=>({id:'one',status:'RECORDING',phase:'PREPARING'})),getTargetPicking:vi.fn(async()=>({id:'one',status:'DONE',target:{selector:'#search'}})),cancelTargetPicking:vi.fn(async()=>({}))}}));

it('a visual selection changes only the draft and keeps navigation dirty until applied',async()=>{
  const recipe={steps:[{id:'fill',action:'fill',selector:'#old',value:'{{company}}'}],variables:{company:{type:'string'}}};
  const onChange=vi.fn(),onDirty=vi.fn();
  render(<StepReviewEditor recipe={recipe} siteUrl="https://example.test/" onChange={onChange} onDirty={onDirty}/>);
  await userEvent.click(screen.getByText('1. Preencher campo'));
  await userEvent.click(screen.getByRole('button',{name:'Selecionar no Edge · fill'}));
  expect(onDirty).toHaveBeenCalledWith('fill',true);
  await waitFor(()=>expect(screen.getByLabelText('Alvo da etapa fill')).toHaveValue('#search'));
  expect(onChange).not.toHaveBeenCalled();
  expect(onDirty).toHaveBeenLastCalledWith('fill',true);
  await userEvent.click(screen.getByRole('button',{name:'Aplicar correção fill'}));
  expect(onChange.mock.lastCall?.[0].steps[0]).toEqual({...recipe.steps[0],selector:'#search'});
  expect(onDirty).toHaveBeenLastCalledWith('fill',false);
});
