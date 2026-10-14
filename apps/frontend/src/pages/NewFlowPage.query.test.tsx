import {it,expect,vi} from 'vitest';
import {render,screen,within,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient,QueryClientProvider} from '@tanstack/react-query';
import {NewFlowPage} from './NewFlowPage';
import {api} from '../lib/api';
vi.mock('../lib/api',()=>({api:{listLoginProfiles:vi.fn(async()=>({items:[]})),startFlowRecording:vi.fn(),getFlowRecording:vi.fn(),cancelFlowRecording:vi.fn(),createAutomation:vi.fn(async()=>({id:1})),createAutomationVersion:vi.fn(async()=>({version:1})),testAutomationVersion:vi.fn(),publishAutomationVersion:vi.fn()}}));

it('keeps other query and download editors pending when one is applied, then publishes the query',async()=>{
  render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><NewFlowPage/></QueryClientProvider></MemoryRouter>);
  const user=userEvent.setup();
  fireEvent.change(screen.getByLabelText('Nome do fluxo'),{target:{value:'Consultas'}});
  fireEvent.change(screen.getByLabelText('Endereço do site'),{target:{value:'http://127.0.0.1/form'}});
  await user.click(screen.getByText('Continuar'));await user.click(screen.getByText('Continuar'));
  const recipe={schema_version:1,name:'Queries',variables:{},output:{type:'file'},steps:[
    {id:'q1',action:'click',selector:'#one',frames:['iframe']},
    {id:'q2',action:'click',selector:'#two'},
    {id:'generate',action:'click',selector:'#generate'},
    {id:'dl',action:'download',selector:'a',filename:'download',collection:{rows:'tr',name:'.name',button:'a',pattern:'*.csv'}}]};
  const file=new File(['{}'],'recipe.json',{type:'application/json'});
  Object.defineProperty(file,'text',{value:async()=>JSON.stringify(recipe)});
  await user.upload(screen.getByLabelText('Importar receita JSON'),file);
  await user.click(screen.getByText('Continuar'));
  await user.click(screen.getByText('Consulta · q1'));await user.click(screen.getByText('Consulta · q2'));
  const first=within(screen.getByRole('group',{name:'Verificar resultado da consulta · q1'}));
  const second=within(screen.getByRole('group',{name:'Verificar resultado da consulta · q2'}));
  for(const [label,value] of [['Confirmação da consulta','#c'],['Contêiner do resultado','#r'],['Estado com dados','.data'],['Estado sem dados','.empty'],['Estado de erro','.error']])
    fireEvent.change(first.getByLabelText(label),{target:{value}});
  fireEvent.change(second.getByLabelText('Confirmação da consulta'),{target:{value:'#unfinished'}});
  await user.click(screen.getByText('Central de download · dl'));
  const download=within(screen.getByRole('group',{name:'Vincular download à solicitação'}));
  fireEvent.change(download.getByLabelText('Contêiner da central'),{target:{value:'#downloads'}});
  expect(screen.getByRole('button',{name:'Continuar'})).toBeDisabled();
  expect(screen.getByRole('button',{name:'Voltar'})).toBeDisabled();
  await user.click(first.getByText('Aplicar consulta'));
  expect(screen.getByRole('button',{name:'Continuar'})).toBeDisabled();
  await user.click(second.getByText('Descartar edição'));
  expect(screen.getByRole('button',{name:'Continuar'})).toBeDisabled();
  fireEvent.change(download.getByLabelText('Ação que gera o relatório'),{target:{value:'generate'}});
  fireEvent.change(download.getByLabelText('Seletor da confirmação'),{target:{value:'#download-confirmation'}});
  await user.click(download.getByText('Aplicar vínculo'));
  expect(screen.getByRole('button',{name:'Continuar'})).toBeEnabled();
  await user.click(screen.getByRole('button',{name:'Continuar'}));
  await user.click(screen.getByText('Validar e publicar fluxo'));
  const configured=vi.mocked(api.createAutomationVersion).mock.calls.at(-1)?.[1];
  expect(configured).toMatchObject({steps:expect.arrayContaining([
    expect.objectContaining({id:'q1',action:'query',frames:['iframe']}),
    expect.objectContaining({id:'q2',action:'click'}),
    expect.objectContaining({id:'generate',action:'request_download'}),
  ])});
});

it('restores the original click after leaving and returning to the review step',async()=>{
  render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><NewFlowPage/></QueryClientProvider></MemoryRouter>);
  const user=userEvent.setup();
  fireEvent.change(screen.getByLabelText('Nome do fluxo'),{target:{value:'Restore'}});
  fireEvent.change(screen.getByLabelText('Endereço do site'),{target:{value:'http://127.0.0.1/form'}});
  await user.click(screen.getByText('Continuar'));await user.click(screen.getByText('Continuar'));
  const original={id:'query',action:'click',selector:'#search',timeout_ms:5000,button:'left',click_count:1,frames:['iframe']};
  const recipe={schema_version:1,name:'Restore',variables:{},output:{type:'none'},steps:[original]};
  const file=new File(['{}'],'restore.json',{type:'application/json'});
  Object.defineProperty(file,'text',{value:async()=>JSON.stringify(recipe)});
  await user.upload(screen.getByLabelText('Importar receita JSON'),file);
  await user.click(screen.getByText('Continuar'));await user.click(screen.getByText('Consulta · query'));
  for(const [label,value] of [['Confirmação da consulta','#c'],['Contêiner do resultado','#r'],['Estado com dados','.data'],['Estado sem dados','.empty'],['Estado de erro','.error']])
    fireEvent.change(screen.getByLabelText(label),{target:{value}});
  await user.click(screen.getByText('Aplicar consulta'));
  expect(screen.getByText('Voltar ao clique')).toBeInTheDocument();
  await user.click(screen.getByRole('button',{name:'Continuar'}));
  expect(screen.getByRole('heading',{name:'Publicar'})).toBeInTheDocument();
  await user.click(screen.getByRole('button',{name:'Voltar'}));
  expect(screen.getByRole('heading',{name:'Campos'})).toBeInTheDocument();
  await user.click(screen.getByText('Consulta · query'));
  await user.click(screen.getByText('Voltar ao clique'));
  await user.click(screen.getByRole('button',{name:'Continuar'}));
  await user.click(screen.getByText('Validar e publicar fluxo'));
  const configured=vi.mocked(api.createAutomationVersion).mock.calls.at(-1)?.[1] as {steps:Record<string,unknown>[]};
  expect(configured.steps.find(s=>s.id==='query')).toEqual(original);
});
