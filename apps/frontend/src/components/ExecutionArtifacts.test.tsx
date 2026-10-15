import {it, expect, vi} from 'vitest';
import {render, screen, waitFor} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {ExecutionArtifacts} from './ExecutionArtifacts';
import {api} from '../lib/api';

vi.mock('../lib/api',()=>({api:{listExecutionArtifacts:vi.fn(),downloadExecutionArtifact:vi.fn()}}));

function show() {
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
    <ExecutionArtifacts executionId={7} status="SUCCEEDED" />
  </QueryClientProvider>);
}

it('lists the execution file and downloads its authenticated bytes',async()=>{
  vi.mocked(api.listExecutionArtifacts).mockResolvedValue({items:[{id:3,execution_automation_id:9,filename:'result.csv',size:5,checksum:'a'.repeat(64)}]});
  vi.mocked(api.downloadExecutionArtifact).mockResolvedValue(new Blob(['A,42\n']));
  const create=vi.fn(()=> 'blob:fixture'),revoke=vi.fn();
  vi.stubGlobal('URL',Object.assign(URL,{createObjectURL:create,revokeObjectURL:revoke}));
  const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
  show();
  await userEvent.click(await screen.findByRole('button',{name:'Baixar result.csv'}));
  await waitFor(()=>expect(api.downloadExecutionArtifact).toHaveBeenCalledWith(7,3));
  await waitFor(()=>expect(click).toHaveBeenCalled());
  expect(create).toHaveBeenCalled();
  click.mockRestore();
});

it('explains download failure without exposing internal error details',async()=>{
  vi.mocked(api.listExecutionArtifacts).mockResolvedValue({items:[{id:3,execution_automation_id:9,filename:'result.csv',size:5,checksum:'a'.repeat(64)}]});
  vi.mocked(api.downloadExecutionArtifact).mockRejectedValue(new Error('private-path-canary'));
  show();
  await userEvent.click(await screen.findByRole('button',{name:'Baixar result.csv'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('O arquivo está indisponível ou foi alterado.');
  expect(screen.queryByText(/private-path-canary/)).not.toBeInTheDocument();
});

it('shows an empty validated-file list without claiming a download exists',async()=>{
  vi.mocked(api.listExecutionArtifacts).mockResolvedValue({items:[]});
  show();
  expect(await screen.findByText('Nenhum arquivo validado disponível nesta execução.')).toBeInTheDocument();
  expect(screen.queryByRole('button',{name:/Baixar/})).not.toBeInTheDocument();
});
