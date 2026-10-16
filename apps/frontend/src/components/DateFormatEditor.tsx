import type {ParameterDeclaration, FieldRules} from './RecipeField';
import type {SiteDateFormat} from '../lib/siteDates';

export const DATE_FORMAT_OPTIONS: {value: SiteDateFormat; label: string}[] = [
  {value:'dd/MM/yyyy',label:'Data · DD/MM/AAAA'},
  {value:'dd/MM/yyyy HH:mm',label:'Data e hora · DD/MM/AAAA HH:mm'},
  {value:'dd/MM/yyyy HH:mm:ss',label:'Data e hora · DD/MM/AAAA HH:mm:ss'},
  {value:'yyyy-MM-dd',label:'Data · AAAA-MM-DD (ISO)'},
  {value:'yyyy-MM-dd HH:mm:ss',label:'Data e hora · AAAA-MM-DD HH:mm:ss'},
];

export function configuredDateField(declaration: ParameterDeclaration, siteFormat: string): FieldRules {
  if (!siteFormat) {
    const original = {...(declaration.field ?? {})};
    delete original.site_format;
    return {...original,control:'text'};
  }
  if (!DATE_FORMAT_OPTIONS.some(item=>item.value===siteFormat))
    throw new Error('Formato de data não suportado.');
  return {...(declaration.field ?? {}),
    control: siteFormat.includes('HH:') ? 'datetime-local' : 'date',
    site_format: siteFormat as SiteDateFormat};
}

export function DateFormatEditor({name,declaration,onChange,disabled=false}:{
  name:string; declaration:ParameterDeclaration; onChange:(next:FieldRules)=>void;disabled?:boolean;
}) {
  const label=declaration.label ?? name;
  if (!['date','datetime-local'].includes(declaration.field?.control ?? '') &&
      !/\b(data|hora|date|time)\b/i.test(label)) return null;
  const chosen = declaration.field?.site_format ??
    (declaration.field?.control === 'date' ? 'yyyy-MM-dd' : '');
  return <label>Formato de data do campo {name}
    <select aria-label={`Formato de data do campo ${name}`}
      value={chosen} disabled={disabled}
      onChange={event => onChange(configuredDateField(declaration,event.target.value))}>
      <option value="">Usar campo de texto (sem calendário)</option>
      {DATE_FORMAT_OPTIONS.map(item=><option key={item.value} value={item.value}>{item.label}</option>)}
    </select>
    <small className="muted">O calendário do Nexer enviará ao site exatamente este formato; escolha o padrão aceito pelo formulário.</small>
  </label>;
}
