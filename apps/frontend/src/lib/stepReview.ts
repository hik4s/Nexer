import type {Recipe, Step} from './queryOutcome';
export type {Recipe} from './queryOutcome';

const editableActions = new Set([
  'click', 'fill', 'select', 'press', 'check', 'choose', 'choose_radio', 'set_value',
  'wait_for', 'hover', 'scroll', 'drag', 'query', 'request_download', 'download',
]);
const titles: Record<string, string> = {
  navigate: 'Abrir página', click: 'Clicar', fill: 'Preencher campo', select: 'Selecionar opção',
  press: 'Pressionar tecla', check: 'Marcar opção', choose: 'Escolher opção', choose_radio: 'Escolher alternativa',
  set_value: 'Ajustar controle', wait_for: 'Aguardar condição', wait_for_any: 'Aguardar uma das condições',
  wait_for_outcome: 'Aguardar resultado da operação',
  hover: 'Apontar para elemento', scroll: 'Rolar página', drag: 'Arrastar elemento',
  query: 'Consultar e verificar resultado', request_download: 'Solicitar relatório',
  download: 'Baixar arquivo', snapshot_downloads: 'Verificar central antes da solicitação',
  switch_tab: 'Mudar de aba', close_tab: 'Fechar aba', validate_file: 'Verificar arquivo',
};

export type StepRepair = {selector: string; targetSelector?: string; syncWait: boolean};
export type ReviewedStep = {
  id: string; position: number; title: string; context: string; parameterLabel?: string; editable: boolean;
};

export function hasValidStepIds(steps: unknown): steps is Step[] {
  if (!Array.isArray(steps) || !steps.length) return false;
  const seen = new Set<string>();
  return steps.every(step => {
    if (!step || typeof step !== 'object' || Array.isArray(step) ||
        typeof step.id !== 'string' || !step.id.trim() || seen.has(step.id)) return false;
    seen.add(step.id);
    return true;
  });
}

export function canRepairStep(step: Step): boolean {
  return typeof step.id === 'string' && Boolean(step.id.trim()) &&
    editableActions.has(String(step.action)) && typeof step.selector === 'string' &&
    !(step.action === 'download' && step.collection !== undefined);
}

export function associatedAutomaticWait(recipe: Recipe, stepId: string): Step | undefined {
  const index = recipe.steps.findIndex(step => step.id === stepId);
  if (index < 1) return;
  const step = recipe.steps[index], previous = recipe.steps[index - 1];
  if (previous.action === 'wait_for' && (previous.learning as Step | undefined)?.source === 'automatic' &&
      previous.selector === step.selector && JSON.stringify(previous.frames ?? []) === JSON.stringify(step.frames ?? []))
    return previous;
}

export function reviewSteps(recipe: Recipe): ReviewedStep[] {
  let tab: number | null = 0;
  return recipe.steps.map((step, index) => {
    if (step.action === 'switch_tab') tab = typeof step.index === 'number' ? step.index : null;
    const frames = Array.isArray(step.frames) ? step.frames.length : 0;
    const parameter = typeof step.value === 'string' ? /^{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}$/.exec(step.value)?.[1] : undefined;
    const declaration = parameter ? (recipe.variables as Record<string, Step> | undefined)?.[parameter] : undefined;
    const parameterLabel = declaration && !declaration.secret ? String(declaration.label ?? parameter) : undefined;
    const row = {
      id: String(step.id), position: index + 1, title: titles[String(step.action)] ?? 'Etapa avançada',
      context: `${tab === null ? 'Aba definida na execução' : `Aba ${tab + 1}`} · ${frames ? `${frames} ${frames === 1 ? 'frame' : 'frames'}` : 'página principal'}`,
      parameterLabel, editable: canRepairStep(step),
    };
    if (step.action === 'close_tab') tab = null;
    return row;
  });
}

export function repairStep(input: Recipe, stepId: string, repair: StepRepair): Recipe {
  const fail = (): never => {throw new Error('Revise o alvo desta etapa. Nenhuma alteração foi aplicada.');};
  const targets = input.steps.filter(step => step.id === stepId);
  if (targets.length !== 1 || !canRepairStep(targets[0])) return fail();
  const validSelector = (value: unknown): value is string => {
    if (typeof value !== 'string' || !value.trim() || value.length > 2048) return false;
    const variables = input.variables as Record<string, Step> | undefined;
    return [...value.matchAll(/{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}/g)].every(match =>
      variables && Object.hasOwn(variables, match[1]));
  };
  if (!validSelector(repair.selector) || typeof repair.syncWait !== 'boolean' ||
      (targets[0].action === 'drag' && !validSelector(repair.targetSelector))) return fail();
  const recipe = structuredClone(input), step = recipe.steps.find(step => step.id === stepId)!;
  const selectorChanged = repair.selector.trim() !== step.selector;
  const wait = repair.syncWait && selectorChanged ? associatedAutomaticWait(recipe, stepId) : undefined;
  step.selector = repair.selector.trim();
  if (step.action === 'drag') step.target_selector = repair.targetSelector!.trim();
  if (selectorChanged && step.action === 'wait_for' && step.learning) step.learning = {source: 'manual', confidence: 'high'};
  if (wait) {
    wait.selector = step.selector;
    wait.learning = {source: 'manual', confidence: 'high'};
  }
  return recipe;
}

export type OutcomeRepair = {busySelector: string; readySelector: string;
  readyState: 'enabled'|'visible'; timeoutMs: number; errorSelector: string};

/** Change only the reviewed wait. Do not change the original click or its retry policy. */
export function repairOutcomeWait(input: Recipe, stepId: string, repair: OutcomeRepair | null): Recipe {
  const matches = input.steps.filter(step => step.id === stepId);
  const index = input.steps.findIndex(step => step.id === stepId);
  const step = matches[0];
  if (matches.length !== 1 || !step || step.action !== 'wait_for_outcome' ||
      index < 1 || input.steps[index - 1].action !== 'click' ||
      input.steps[index - 1].id !== step.after_step_id)
    throw new Error('A espera deve permanecer imediatamente após a ação original.');
  const updated = structuredClone(input);
  if (repair === null) {
    updated.steps.splice(index, 1);
    return updated;
  }
  const valid = (value: string) => typeof value === 'string' && value.length <= 2048 &&
    !value.includes('{{') && !value.includes('}}');
  if (!valid(repair.busySelector) || !valid(repair.readySelector) || !repair.readySelector.trim() ||
      !valid(repair.errorSelector) ||
      !['enabled','visible'].includes(repair.readyState) ||
      !Number.isInteger(repair.timeoutMs) || repair.timeoutMs < 100 || repair.timeoutMs > 180000)
    throw new Error('Revise os seletores e o tempo limite desta espera.');
  const target = updated.steps[index];
  if (repair.busySelector.trim()) target.busy_selector = repair.busySelector.trim();
  else delete target.busy_selector;
  target.ready_selector = repair.readySelector.trim();
  target.ready_state = repair.readyState;
  target.timeout_ms = repair.timeoutMs;
  if (repair.errorSelector.trim()) target.error_selector = repair.errorSelector.trim();
  else delete target.error_selector;
  target.learning = {source: 'manual', confidence: 'high'};
  return updated;
}
