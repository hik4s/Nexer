import {render,screen,fireEvent} from '@testing-library/react';
import {it,expect,vi} from 'vitest';
import {DownloadGenerationEditor} from './DownloadGenerationEditor';
it('keeps changes pending and applies a complete request without asking for actual report data',()=>{
  const change=vi.fn(),dirty=vi.fn();
  render(<DownloadGenerationEditor recipe={{steps:[{id:'generate',action:'click',selector:'#export'},{id:'get',action:'download',collection:{rows:'#table tr',name:'.name',button:'a',pattern:'{{pattern}}'}}]}} downloadId="get" onChange={change} onDirty={dirty}/>);
  fireEvent.change(screen.getByLabelText('Ação que gera o relatório'),{target:{value:'generate'}});
  fireEvent.change(screen.getByLabelText('Contêiner da central'),{target:{value:'#table'}});
  fireEvent.change(screen.getByLabelText('Seletor da confirmação'),{target:{value:'#confirmation'}});
  expect(dirty).toHaveBeenCalledWith(true);expect(change).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Aplicar vínculo'));
  expect(change.mock.calls[0][0].steps.map((s:Record<string,unknown>)=>s.action)).toEqual(['snapshot_downloads','request_download','download']);
  expect(dirty).toHaveBeenLastCalledWith(false);
});
