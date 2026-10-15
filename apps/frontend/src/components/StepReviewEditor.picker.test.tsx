import {it,expect,vi} from 'vitest';
import {render,screen,waitFor,fireEvent,act} from '@testing-library/react';
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

it('closing the step cancels polling and preserves a manual draft against a late result',async()=>{
  let finish!:(value:never)=>void;
  vi.mocked(api.startTargetPicking).mockResolvedValueOnce({id:'pending-poll',status:'RECORDING',phase:'SELECTING'} as never);
  vi.mocked(api.getTargetPicking).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  const onChange=vi.fn(),onDirty=vi.fn();
  render(<StepReviewEditor recipe={{steps:[{id:'fill',action:'fill',selector:'#old',value:'{{company}}'}]}} siteUrl="https://example.test/" onChange={onChange} onDirty={onDirty}/>);
  const summary=screen.getByText('1. Preencher campo');
  await userEvent.click(summary);
  fireEvent.change(screen.getByLabelText('Alvo da etapa fill'),{target:{value:'#manual'}});
  await userEvent.click(screen.getByRole('button',{name:'Selecionar no Edge · fill'}));
  await waitFor(()=>expect(finish).toBeTypeOf('function'));
  await userEvent.click(summary);
  await waitFor(()=>expect(api.cancelTargetPicking).toHaveBeenCalledWith('pending-poll'));
  await act(async()=>finish({id:'pending-poll',status:'DONE',target:{selector:'#late'}} as never));
  await userEvent.click(summary);
  expect(screen.getByLabelText('Alvo da etapa fill')).toHaveValue('#manual');
  expect(onChange).not.toHaveBeenCalled();
  expect(onDirty).toHaveBeenLastCalledWith('fill',true);
  expect(screen.getByRole('button',{name:'Selecionar no Edge · fill'})).toBeEnabled();
});

it('closing while opening cancels the late session and leaves an unedited step clean',async()=>{
  let finish!:(value:never)=>void;
  vi.mocked(api.startTargetPicking).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
  const onDirty=vi.fn();
  render(<StepReviewEditor recipe={{steps:[{id:'fill',action:'fill',selector:'#old',value:'{{company}}'}]}} siteUrl="https://example.test/" onChange={vi.fn()} onDirty={onDirty}/>);
  const summary=screen.getByText('1. Preencher campo');
  await userEvent.click(summary);
  await userEvent.click(screen.getByRole('button',{name:'Selecionar no Edge · fill'}));
  await userEvent.click(summary);
  await waitFor(()=>expect(onDirty).toHaveBeenLastCalledWith('fill',false));
  await act(async()=>finish({id:'pending-open',status:'RECORDING',phase:'PREPARING'} as never));
  await waitFor(()=>expect(api.cancelTargetPicking).toHaveBeenCalledWith('pending-open'));
  await userEvent.click(summary);
  expect(screen.getByLabelText('Alvo da etapa fill')).toHaveValue('#old');
  expect(screen.getByRole('button',{name:'Selecionar no Edge · fill'})).toBeEnabled();
});
