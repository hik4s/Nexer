import {it,expect,vi} from 'vitest';
import {render,screen,waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {VisualTargetPicker} from './VisualTargetPicker';
import {api} from '../lib/api';
vi.mock('../lib/api',()=>({api:{startTargetPicking:vi.fn(),getTargetPicking:vi.fn(),cancelTargetPicking:vi.fn(async()=>({}))}}));
const active={id:'one',status:'RECORDING',phase:'PREPARING',target:null,error:null};
const done={...active,status:'DONE',phase:'SELECTING',target:{selector:'#search'}};
const props={url:'https://example.test/',kind:'text' as const,label:'alvo',invalidationKey:'original'};

it('delivers only a selected draft and reports busy while preparing',async()=>{
  vi.mocked(api.startTargetPicking).mockResolvedValue(active as never);
  vi.mocked(api.getTargetPicking).mockResolvedValue(done as never);
  const onPicked=vi.fn(),onBusy=vi.fn();render(<VisualTargetPicker {...props} onPicked={onPicked} onBusy={onBusy}/>);
  await userEvent.click(screen.getByRole('button',{name:'Selecionar no Edge · alvo'}));
  expect(onBusy).toHaveBeenCalledWith(true);
  await waitFor(()=>expect(onPicked).toHaveBeenCalledWith('#search'));
  expect(onBusy).toHaveBeenLastCalledWith(false);
});

it('ignores an old result after editing the draft or cancelling',async()=>{
  let finish!:(value:never)=>void;
  vi.mocked(api.startTargetPicking).mockResolvedValue(active as never);
  vi.mocked(api.getTargetPicking).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const onPicked=vi.fn(),onBusy=vi.fn();
  const view=render(<VisualTargetPicker {...props} onPicked={onPicked} onBusy={onBusy}/>);
  await userEvent.click(screen.getByRole('button',{name:'Selecionar no Edge · alvo'}));
  await waitFor(()=>expect(finish).toBeTypeOf('function'));
  view.rerender(<VisualTargetPicker {...props} invalidationKey="edited" onPicked={onPicked} onBusy={onBusy}/>);
  finish(done as never);
  await waitFor(()=>expect(api.cancelTargetPicking).toHaveBeenCalledWith('one'));
  expect(onPicked).not.toHaveBeenCalled();expect(onBusy).toHaveBeenLastCalledWith(false);
});

it('cancels a session that arrives after the editor unmounts',async()=>{
  let finish!:(value:never)=>void;
  vi.mocked(api.startTargetPicking).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const onPicked=vi.fn();const view=render(<VisualTargetPicker {...props} onPicked={onPicked} onBusy={vi.fn()}/>);
  await userEvent.click(screen.getByRole('button',{name:'Selecionar no Edge · alvo'}));
  view.unmount();finish(active as never);
  await waitFor(()=>expect(api.cancelTargetPicking).toHaveBeenCalledWith('one'));
  expect(onPicked).not.toHaveBeenCalled();
});

it('explicit cancel invalidates a pending get before its response arrives',async()=>{
  let finish!:(value:never)=>void;
  vi.mocked(api.startTargetPicking).mockResolvedValue(active as never);
  vi.mocked(api.getTargetPicking).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const onPicked=vi.fn();render(<VisualTargetPicker {...props} onPicked={onPicked} onBusy={vi.fn()}/>);
  await userEvent.click(screen.getByRole('button',{name:'Selecionar no Edge · alvo'}));
  await waitFor(()=>expect(finish).toBeTypeOf('function'));
  await userEvent.click(screen.getByRole('button',{name:'Cancelar seleção · alvo'}));
  finish(done as never);await new Promise(resolve=>setTimeout(resolve,20));
  expect(onPicked).not.toHaveBeenCalled();
});
