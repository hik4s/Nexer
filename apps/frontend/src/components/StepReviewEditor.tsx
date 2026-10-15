import {useEffect, useRef, useState} from 'react';
import {associatedAutomaticWait, repairStep, reviewSteps, type Recipe} from '../lib/stepReview';
import {VisualTargetPicker} from './VisualTargetPicker';
import type {TargetKind} from '../lib/api';

type Props = {recipe: Recipe; siteUrl?: string; onChange: (recipe: Recipe) => void; onDirty: (stepId: string, dirty: boolean) => void};

function TargetEditor({recipe, siteUrl, stepId, expanded, onChange, onDirty}: Props & {stepId: string; expanded: boolean}) {
  const step = recipe.steps.find(item => item.id === stepId)!;
  const [selector, setSelector] = useState(String(step.selector));
  const [target, setTarget] = useState(String(step.target_selector ?? ''));
  const [syncWait, setSyncWait] = useState(true);
  const [error, setError] = useState('');
  const [dirty, setDirty] = useState(false);
  const dirtyRef = useRef(false), activeFields = useRef(new Set<string>());
  const [picking, setPicking] = useState(false), [revision, setRevision] = useState(0);
  const wait = associatedAutomaticWait(recipe, stepId);
  let kind: TargetKind | null = null;
  if (!Array.isArray(step.frames) || step.frames.length === 0) {
    if (step.action === 'fill') kind = 'text';
    else if (step.action === 'check') kind = 'checkbox';
    else if (step.action === 'select') kind = 'select';
    else if (step.action === 'set_value' && (step.input_type === 'range' || step.input_type === 'color')) kind = step.input_type;
    else if (!['choose', 'choose_radio', 'set_value'].includes(String(step.action))) kind = 'element';
  }
  const invalidationKey = JSON.stringify([revision, step.selector, step.target_selector]);
  useEffect(() => {
    if (!dirty) {
      setSelector(String(step.selector));
      setTarget(String(step.target_selector ?? ''));
    }
  }, [step.selector, step.target_selector, dirty]);
  function markDirty() {dirtyRef.current = true; setDirty(true); setRevision(value => value + 1); onDirty(stepId, true);}
  function pickerBusy(field: string, value: boolean) {
    if (value) activeFields.current.add(field); else activeFields.current.delete(field);
    setPicking(activeFields.current.size > 0);
    onDirty(stepId, dirtyRef.current || activeFields.current.size > 0);
  }
  function apply() {
    if (activeFields.current.size) return;
    try {
      onChange(repairStep(recipe, stepId, {selector, targetSelector: target, syncWait}));
      dirtyRef.current = false; setDirty(false); onDirty(stepId, false); setError('');
    } catch {
      markDirty(); setError('Revise o alvo desta etapa. Nenhuma alteração foi aplicada.');
    }
  }
  function discard() {
    setSelector(String(step.selector)); setTarget(String(step.target_selector ?? ''));
    dirtyRef.current = false; setSyncWait(true); setError(''); setDirty(false); setRevision(value => value + 1);
    onDirty(stepId, activeFields.current.size > 0);
  }
  return <fieldset className="step-target-editor"><legend>Corrigir etapa · {stepId}</legend>
    <p className="muted">Ajuste o seletor do alvo sem mudar a ordem, os parâmetros ou o contexto da etapa. O alvo será conferido quando o fluxo executar.</p>
    <label>Alvo da etapa {stepId}<input value={selector} maxLength={2048} onChange={event => {setSelector(event.target.value); markDirty();}} /></label>
    {siteUrl && kind ? expanded && <VisualTargetPicker url={siteUrl} kind={kind} label={stepId} invalidationKey={invalidationKey} disabled={picking} onBusy={value => pickerBusy('selector', value)} onPicked={value => {setSelector(value); markDirty();}} /> : siteUrl ? <p className="muted">Este frame ou controle usa correção manual do seletor nesta versão.</p> : null}
    {step.action === 'drag' ? <label>Destino da etapa {stepId}<input value={target} maxLength={2048} onChange={event => {setTarget(event.target.value); markDirty();}} /></label> : null}
    {expanded && step.action === 'drag' && siteUrl && kind ? <VisualTargetPicker url={siteUrl} kind="element" label={`${stepId} · destino`} invalidationKey={invalidationKey} disabled={picking} onBusy={value => pickerBusy('target', value)} onPicked={value => {setTarget(value); markDirty();}} /> : null}
    {wait ? <label className="step-review-checkbox"><input type="checkbox" checked={syncWait} onChange={event => {setSyncWait(event.target.checked); markDirty();}} />Atualizar também a espera automática anterior ({String(wait.id)}). Ela passará a ser uma condição revisada manualmente.</label> : null}
    {error ? <p role="alert">{error}</p> : null}
    <div className="button-row"><button type="button" className="secondary-button" aria-label={`Aplicar correção ${stepId}`} disabled={picking} onClick={apply}>Aplicar correção</button><button type="button" className="secondary-button" aria-label={`Descartar correção ${stepId}`} onClick={discard}>Descartar correção</button></div>
  </fieldset>;
}

export function StepReviewEditor({recipe, siteUrl, onChange, onDirty}: Props) {
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});
  return <section className="step-review" aria-label="Revisão das etapas"><h3>Etapas do fluxo · {recipe.steps.length}</h3>
    <p className="muted">Confira a sequência e abra uma etapa para corrigir seu alvo. Os valores da execução não aparecem nesta revisão.</p>
    <ol className="step-review-list">{reviewSteps(recipe).map(row => <li key={row.id}><details onToggle={event => {
      const expanded = event.currentTarget.open;
      setExpandedSteps(previous => ({...previous, [row.id]: expanded}));
    }}>
      <summary><strong>{row.position}. {row.title}</strong>{row.parameterLabel ? <span className="step-review-parameter">{row.parameterLabel}</span> : null}<span className="step-review-context">{row.context}</span></summary>
      {row.editable ? <TargetEditor recipe={recipe} siteUrl={siteUrl} stepId={row.id} expanded={!!expandedSteps[row.id]} onChange={onChange} onDirty={onDirty} /> : <p className="muted">Esta etapa mantém sua configuração original. Downloads em central são revisados na seção específica; outras configurações avançadas ficam no Studio.</p>}
    </details></li>)}</ol>
  </section>;
}
