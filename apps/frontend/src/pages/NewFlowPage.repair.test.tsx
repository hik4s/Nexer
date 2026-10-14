import {it, expect, vi} from 'vitest';
import {render, screen, fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {MemoryRouter} from 'react-router-dom';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {NewFlowPage} from './NewFlowPage';
import {api} from '../lib/api';
vi.mock('../lib/api', () => ({api: {
  listLoginProfiles: vi.fn(async () => ({items: []})), startFlowRecording: vi.fn(), getFlowRecording: vi.fn(), cancelFlowRecording: vi.fn(),
  createAutomation: vi.fn(async () => ({id: 7})), createAutomationVersion: vi.fn(async () => ({version: 1})), testAutomationVersion: vi.fn(), publishAutomationVersion: vi.fn(),
}}));

it('repairs one step with its wait and preserves repairs when reverting query configuration', async () => {
  render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><NewFlowPage /></QueryClientProvider></MemoryRouter>);
  const user = userEvent.setup();
  fireEvent.change(screen.getByLabelText('Nome do fluxo'), {target: {value: 'Reparo'}});
  fireEvent.change(screen.getByLabelText('Endereço do site'), {target: {value: 'http://127.0.0.1/form'}});
  await user.click(screen.getByRole('button', {name: 'Continuar'}));
  await user.click(screen.getByRole('button', {name: 'Continuar'}));
  const recipe = {schema_version: 1, name: 'Review', variables: {company: {type: 'string', label: 'Empresa'}}, output: {type: 'none'}, steps: [
    {id: 'open', action: 'navigate', url: 'http://127.0.0.1/form'},
    {id: 'ready', action: 'wait_for', selector: '#old', frames: ['iframe'], state: 'enabled', learning: {source: 'automatic', confidence: 'high'}},
    {id: 'fill', action: 'fill', selector: '#old', frames: ['iframe'], value: '{{company}}'},
    {id: 'query', action: 'click', selector: '#search', timeout_ms: 5000},
  ]};
  const file = new File(['{}'], 'review.json', {type: 'application/json'});
  Object.defineProperty(file, 'text', {value: async () => JSON.stringify(recipe)});
  await user.upload(screen.getByLabelText('Importar receita JSON'), file);
  await user.click(screen.getByRole('button', {name: 'Continuar'}));
  await user.click(screen.getByText('3. Preencher campo'));
  fireEvent.change(screen.getByLabelText('Alvo da etapa fill'), {target: {value: '#new'}});
  await user.click(screen.getByText('Consulta · query'));
  for (const [label, value] of [['Confirmação da consulta', '#c'], ['Contêiner do resultado', '#r'], ['Estado com dados', '.data'], ['Estado sem dados', '.empty'], ['Estado de erro', '.error']])
    fireEvent.change(screen.getByLabelText(label), {target: {value}});
  await user.click(screen.getByRole('button', {name: 'Aplicar correção fill'}));
  expect(screen.getByRole('button', {name: 'Continuar'})).toBeDisabled();
  expect(screen.getByRole('button', {name: 'Voltar'})).toBeDisabled();
  await user.click(screen.getByRole('button', {name: 'Aplicar consulta'}));
  await user.click(screen.getByText('4. Consultar e verificar resultado'));
  fireEvent.change(screen.getByLabelText('Alvo da etapa query'), {target: {value: '#fixedSearch'}});
  await user.click(screen.getByRole('button', {name: 'Aplicar correção query'}));
  await user.click(screen.getByRole('button', {name: 'Voltar ao clique'}));
  await user.click(screen.getByRole('button', {name: 'Continuar'}));
  await user.click(screen.getByRole('button', {name: 'Voltar'}));
  expect(screen.getByLabelText('Alvo da etapa fill')).toHaveValue('#new');
  await user.click(screen.getByRole('button', {name: 'Continuar'}));
  await user.click(screen.getByText('Validar e publicar fluxo'));
  const published = vi.mocked(api.createAutomationVersion).mock.calls.at(-1)?.[1] as typeof recipe;
  expect(published.steps.map(s => s.id)).toEqual(['open', 'ready', 'fill', 'query']);
  expect(published.steps[1]).toMatchObject({selector: '#new', learning: {source: 'manual'}});
  expect(published.steps[2]).toEqual({...recipe.steps[2], selector: '#new'});
  expect(published.steps[3]).toEqual({...recipe.steps[3], selector: '#fixedSearch'});
  expect(published.variables.company).toEqual(recipe.variables.company);
});

it.each([null,{id:1,action:'click',selector:'#x'},{action:'click',selector:'#x'}])('rejects malformed step IDs during import: %j',async(step)=>{
  render(<MemoryRouter><QueryClientProvider client={new QueryClient()}><NewFlowPage /></QueryClientProvider></MemoryRouter>);
  const user=userEvent.setup();
  fireEvent.change(screen.getByLabelText('Nome do fluxo'),{target:{value:'Invalid'}});
  fireEvent.change(screen.getByLabelText('Endereço do site'),{target:{value:'http://127.0.0.1/form'}});
  await user.click(screen.getByRole('button',{name:'Continuar'}));await user.click(screen.getByRole('button',{name:'Continuar'}));
  const file=new File(['{}'],'invalid.json',{type:'application/json'});
  Object.defineProperty(file,'text',{value:async()=>JSON.stringify({variables:{},steps:[step]})});
  await user.upload(screen.getByLabelText('Importar receita JSON'),file);
  expect(screen.getByRole('alert')).toHaveTextContent('Arquivo de receita inválido.');
  expect(screen.getByRole('button',{name:'Continuar'})).toBeDisabled();
});
