import {datePeriod} from "../lib/practical";
export function DateShortcuts({onChoose}: {onChoose: (values: {period_start: string; period_end: string}) => void}) {
  return <div className="date-shortcuts" aria-label="Períodos rápidos"><span>Período rápido</span>{([['today', 'Hoje'], ['month', 'Mês atual'], ['previous', 'Mês anterior']] as const).map(([preset, label]) => <button className="secondary-button" type="button" key={preset} onClick={() => onChoose(datePeriod(preset))}>{label}</button>)}<button type="button" className="text-button" onClick={event => {const scope = event.currentTarget.closest("fieldset") ?? event.currentTarget.closest("form"); scope?.querySelector<HTMLInputElement>('input[type="date"]')?.focus();}}>Período personalizado</button></div>;
}
