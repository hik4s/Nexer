import {it,expect,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {DateFormatEditor,configuredDateField} from './DateFormatEditor';

it('switches a recorded calendar mask safely without rewriting unrelated metadata',()=>{
 const declaration={type:'string',label:'Data Hora Início',field:{control:'datetime-local',site_format:'dd/MM/yyyy HH:mm:ss' as const,required:true}};
 const updated=vi.fn();
 render(<DateFormatEditor name="input_001" declaration={declaration} onChange={updated}/>);
 const control=screen.getByLabelText('Formato de data do campo input_001');
 expect(control).toHaveValue('dd/MM/yyyy HH:mm:ss');
 fireEvent.change(control,{target:{value:'dd/MM/yyyy HH:mm'}});
 expect(updated).toHaveBeenCalledWith({control:'datetime-local',site_format:'dd/MM/yyyy HH:mm',required:true});
 expect(declaration.field.site_format).toEqual('dd/MM/yyyy HH:mm:ss');
});
it('allows fixing an unlabeled date input and rejects unexpected formats',()=>{
 const declaration={label:'Data Hora Fim',type:'string',field:{control:'text',required:true}};
 const changed=vi.fn();
 render(<DateFormatEditor name="input_002" declaration={declaration} onChange={changed}/>);
 fireEvent.change(screen.getByLabelText('Formato de data do campo input_002'),{target:{value:'dd/MM/yyyy HH:mm:ss'}});
 expect(changed).toHaveBeenCalledWith({control:'datetime-local',site_format:'dd/MM/yyyy HH:mm:ss',required:true});
 expect(()=>configuredDateField(declaration,'javascript:bad')).toThrow();
});
