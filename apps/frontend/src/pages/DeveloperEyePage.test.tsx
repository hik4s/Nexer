import {it, expect, vi, beforeEach} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {DeveloperEyePage} from './DeveloperEyePage';

const mock = vi.hoisted(()=>({
  getDiagnostics: vi.fn(), listExecutions: vi.fn(),
  probeDeveloperSelector: vi.fn(), startTargetPicking: vi.fn(),
  getTargetPicking: vi.fn(), cancelTargetPicking: vi.fn(),
  listAutomations: vi.fn(), getAutomationVersion: vi.fn(), testAutomationVersion: vi.fn(),
}));
vi.mock('../lib/api',()=>({api: mock}));
function view(){
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
    <MemoryRouter><DeveloperEyePage/></MemoryRouter>
  </QueryClientProvider>);
}
beforeEach(()=>{
  vi.clearAllMocks();
  mock.getDiagnostics.mockResolvedValue({status:'ok',database:{status:'ok'},workers:{online:1,total:2}});
  mock.listExecutions.mockResolvedValue({items:[{id:7,status:'RUNNING',cancel_requested:false}]});
  mock.probeDeveloperSelector.mockResolvedValue({mode:'headless',status:'FOUND',matches:1,visible:true,enabled:true,elapsed_ms:33});
  mock.startTargetPicking.mockResolvedValue({id:'session-1',status:'RECORDING',phase:'PREPARING',target:null,error:null});
  mock.getTargetPicking.mockResolvedValue({id:'session-1',status:'RECORDING',phase:'SELECTING',target:null,error:null});
  mock.cancelTargetPicking.mockResolvedValue({id:'session-1',status:'CANCELLED',phase:'SELECTING',target:null,error:null});
  mock.listAutomations.mockResolvedValue({items:[{id:3,name:'Fluxo de teste',current_version:2}]});
  mock.getAutomationVersion.mockResolvedValue({recipe:{variables:{
    input_001:{label:'Data Hora Início',type:'string',field:{control:'datetime-local',site_format:'dd/MM/yyyy HH:mm:ss'}},
    credential:{secret:true,label:'Senha protegida'}
  },steps:[{id:'start',action:'click',selector:'#start'},{id:'wait',action:'wait_for_outcome',after_step_id:'start'}]}});
  mock.testAutomationVersion.mockResolvedValue({test_status:'PASSED'});
});
it('shows live diagnostics, recent executions and real headless probe results',async()=>{
  view();
  expect(await screen.findByText(/Workers online: 1 \/2/)).toBeInTheDocument();
  expect(screen.getByRole('link',{name:'Execução #7'})).toHaveAttribute('href','/executions/7');
  fireEvent.change(screen.getByLabelText('Endereço para inspeção'),{target:{value:'https://example.test/'}});
  fireEvent.change(screen.getByLabelText('Seletor CSS a verificar'),{target:{value:'#search'}});
  fireEvent.click(screen.getByRole('button',{name:'Testar seletor (headless)'}));
  await waitFor(()=>expect(mock.probeDeveloperSelector).toHaveBeenCalledWith('https://example.test/','#search'));
  expect(await screen.findByText('Alvo encontrado')).toBeInTheDocument();
  expect(screen.getByText(/Visível: Sim/)).toBeInTheDocument();
});
it('opens a visible Edge inspection through the authorized target picker and allows cancellation',async()=>{
  view();
  fireEvent.change(screen.getByLabelText('Endereço para inspeção'),{target:{value:'https://example.test/'}});
  fireEvent.click(screen.getByRole('button',{name:'Abrir inspeção visual no Edge'}));
  await waitFor(()=>expect(mock.startTargetPicking).toHaveBeenCalledWith('https://example.test/','element'));
  expect(await screen.findByText(/Inspeção visual: Aguardando seleção no Edge/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Encerrar inspeção'}));
  await waitFor(()=>expect(mock.cancelTargetPicking).toHaveBeenCalledWith('session-1'));
  expect(await screen.findByText(/Inspeção visual: Cancelada/)).toBeInTheDocument();
});

it('inspects only safe recipe metadata and validates the contract through the backend',async()=>{
 view();
 const select=await screen.findByLabelText('Fluxo publicado');
 await waitFor(()=>expect(screen.getByRole('option',{name:'Fluxo de teste · versão 2'})).toBeInTheDocument());
 fireEvent.change(select,{target:{value:'3:2'}});
 expect(await screen.findByText(/Data Hora Início/)).toBeInTheDocument();
 expect(screen.getByText(/dd\/MM\/yyyy HH:mm:ss/)).toBeInTheDocument();
 expect(screen.queryByText('Senha protegida')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Validar contrato desta receita'}));
 await waitFor(()=>expect(mock.testAutomationVersion).toHaveBeenCalledWith(3,2));
 expect(await screen.findByText(/Contrato da receita validado/)).toBeInTheDocument();
});
