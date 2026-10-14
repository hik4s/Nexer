import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {useState} from 'react';
import userEvent from '@testing-library/user-event';
import {StepReviewEditor} from './StepReviewEditor';

it('reviews an action, validates repair and supports discarding without execution values',async()=>{
  const recipe={variables:{company:{type:'string',label:'Empresa'}},steps:[
    {id:'fill',action:'fill',selector:'#old',value:'{{company}}',frames:['iframe']},
    {id:'literal',action:'fill',selector:'input',value:'private-canary'},
  ]};
  const onChange=vi.fn(),onDirty=vi.fn();
  render(<StepReviewEditor recipe={recipe} onChange={onChange} onDirty={onDirty}/>);
  expect(screen.getByText('1. Preencher campo')).toBeInTheDocument();
  expect(screen.getByText('Empresa')).toBeInTheDocument();
  expect(screen.queryByText(/private-canary/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByText('1. Preencher campo'));
  const selector=screen.getByLabelText('Alvo da etapa fill');
  fireEvent.change(selector,{target:{value:''}});
  await userEvent.click(screen.getByRole('button',{name:'Aplicar correção fill'}));
  expect(screen.getByRole('alert')).toBeInTheDocument();expect(onChange).not.toHaveBeenCalled();
  fireEvent.change(selector,{target:{value:'#new'}});
  await userEvent.click(screen.getByRole('button',{name:'Aplicar correção fill'}));
  expect(onChange.mock.lastCall?.[0].steps[0]).toMatchObject({id:'fill',selector:'#new',value:'{{company}}'});
  expect(onDirty).toHaveBeenLastCalledWith('fill',false);
  fireEvent.change(selector,{target:{value:'#unsaved'}});
  await userEvent.click(screen.getByRole('button',{name:'Descartar correção fill'}));
  expect(selector).toHaveValue('#old');expect(onDirty).toHaveBeenLastCalledWith('fill',false);
});

it('keeps a pending target when removing an earlier wait or synchronizing another editor',async()=>{
  const initial={steps:[
    {id:'wait',action:'wait_for',selector:'#old',learning:{source:'automatic',confidence:'high'}},
    {id:'action',action:'click',selector:'#old'},
  ]};
  function Harness(){
    const [recipe,setRecipe]=useState(initial);
    return <><button onClick={()=>setRecipe(r=>({...r,steps:r.steps.filter(s=>s.id!=='wait')}))}>Remove earlier wait</button><StepReviewEditor recipe={recipe} onChange={updated=>setRecipe(updated as typeof initial)} onDirty={()=>{}}/></>;
  }
  render(<Harness/>);
  await userEvent.click(screen.getByText('1. Aguardar condição'));
  await userEvent.click(screen.getByText('2. Clicar'));
  fireEvent.change(screen.getByLabelText('Alvo da etapa wait'),{target:{value:'#pendingWait'}});
  fireEvent.change(screen.getByLabelText('Alvo da etapa action'),{target:{value:'#new'}});
  await userEvent.click(screen.getByRole('button',{name:'Aplicar correção action'}));
  expect(screen.getByLabelText('Alvo da etapa wait')).toHaveValue('#pendingWait');
  fireEvent.change(screen.getByLabelText('Alvo da etapa action'),{target:{value:'#pendingAction'}});
  await userEvent.click(screen.getByText('Remove earlier wait'));
  expect(screen.getByLabelText('Alvo da etapa action')).toHaveValue('#pendingAction');
});

it('treats malformed external IDs as read-only rather than crashing',()=>{
  render(<StepReviewEditor recipe={{steps:[{id:1,action:'click',selector:'#x'}]}} onChange={vi.fn()} onDirty={vi.fn()}/>);
  expect(screen.getByText('1. Clicar')).toBeInTheDocument();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
});

it('retains a pending draft when its displayed position changes',async()=>{
  function Harness(){
    const [recipe,setRecipe]=useState({steps:[
      {id:'wait',action:'wait_for',selector:'#old'},
      {id:'action',action:'click',selector:'#old'},
    ]});
    return <><button onClick={()=>setRecipe(r=>({...r,steps:r.steps.slice(1)}))}>Remove wait</button><StepReviewEditor recipe={recipe} onChange={()=>{}} onDirty={()=>{}}/></>;
  }
  render(<Harness/>);
  await userEvent.click(screen.getByText('2. Clicar'));
  fireEvent.change(screen.getByLabelText('Alvo da etapa action'),{target:{value:'#pending'}});
  await userEvent.click(screen.getByText('Remove wait'));
  expect(screen.getByLabelText('Alvo da etapa action')).toHaveValue('#pending');
});
