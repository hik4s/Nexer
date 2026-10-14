import {useEffect, useState} from 'react';
import {associatedAutomaticWait, repairStep, reviewSteps, type Recipe} from '../lib/stepReview';

type Props = {recipe: Recipe; onChange: (recipe: Recipe) => void; onDirty: (stepId: string, dirty: boolean) => void};

function TargetEditor({recipe, stepId, onChange, onDirty}: Props & {stepId: string}) {
  const step = recipe.steps.find(item => item.id === stepId)!;
  const [selector, setSelector] = useState(String(step.selector));
  const [target, setTarget] = useState(String(step.target_selector ?? ''));
  const [syncWait, setSyncWait] = useState(true);
  const [error, setError] = useState('');
  const [dirty, setDirty] = useState(false);
  const wait = associatedAutomaticWait(recipe, stepId);
  useEffect(() => {
    if (!dirty) {
      setSelector(String(step.selector));
      setTarget(String(step.target_selector ?? ''));
    }
  }, [step.selector, step.target_selector, dirty]);
  function markDirty() {setDirty(true); onDirty(stepId, true);}
  function apply() {
    try {
      onChange(repairStep(recipe, stepId, {selector, targetSelector: target, syncWait}));
      setDirty(false); onDirty(stepId, false); setError('');
    } catch {
      markDirty(); setError('Revise o alvo desta etapa. Nenhuma alteração foi aplicada.');
    }
  }
  function discard() {
    setSelector(String(step.selector)); setTarget(String(step.target_selector ?? ''));
    setSyncWait(true); setError(''); setDirty(false); onDirty(stepId, false);
  }
  return <fieldset className="step-target-editor"><legend>Corrigir etapa · {stepId}</legend>
    <p className="muted">Ajuste o seletor do alvo sem mudar a ordem, os parâmetros ou o contexto da etapa. O alvo será conferido quando o fluxo executar.</p>
    <label>Alvo da etapa {stepId}<input value={selector} maxLength={2048} onChange={event => {setSelector(event.target.value); markDirty();}} /></label>
    {step.action === 'drag' ? <label>Destino da etapa {stepId}<input value={target} maxLength={2048} onChange={event => {setTarget(event.target.value); markDirty();}} /></label> : null}
    {wait ? <label className="step-review-checkbox"><input type="checkbox" checked={syncWait} onChange={event => {setSyncWait(event.target.checked); markDirty();}} />Atualizar também a espera automática anterior ({String(wait.id)}). Ela passará a ser uma condição revisada manualmente.</label> : null}
    {error ? <p role="alert">{error}</p> : null}
    <div className="button-row"><button type="button" className="secondary-button" aria-label={`Aplicar correção ${stepId}`} onClick={apply}>Aplicar correção</button><button type="button" className="secondary-button" aria-label={`Descartar correção ${stepId}`} onClick={discard}>Descartar correção</button></div>
  </fieldset>;
}

export function StepReviewEditor({recipe, onChange, onDirty}: Props) {
  return <section className="step-review" aria-label="Revisão das etapas"><h3>Etapas do fluxo · {recipe.steps.length}</h3>
    <p className="muted">Confira a sequência e abra uma etapa para corrigir seu alvo. Os valores da execução não aparecem nesta revisão.</p>
    <ol className="step-review-list">{reviewSteps(recipe).map(row => <li key={row.id}><details>
      <summary><strong>{row.position}. {row.title}</strong>{row.parameterLabel ? <span className="step-review-parameter">{row.parameterLabel}</span> : null}<span className="step-review-context">{row.context}</span></summary>
      {row.editable ? <TargetEditor recipe={recipe} stepId={row.id} onChange={onChange} onDirty={onDirty} /> : <p className="muted">Esta etapa mantém sua configuração original. Downloads em central são revisados na seção específica; outras configurações avançadas ficam no Studio.</p>}
    </details></li>)}</ol>
  </section>;
}
