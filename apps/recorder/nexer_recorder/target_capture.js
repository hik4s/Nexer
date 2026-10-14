/* Target metadata only. Installed before page handlers in a fresh context. */
(() => {
  if (window.__nexerTargetPicker) return;
  let active = true, kind = 'element', busy = false, revision = 0, selected = null, panel, note;
  const api = window.__nexerTargetPicker = {
    get active() { return active; },
    get selected() { return selected; },
    setActive(value, nextKind = kind, message = '') {
      revision++; active = value; kind = nextKind; busy = false; selected = null;
      if (note) note.textContent = message || (active ? 'Clique no elemento da etapa. A seleção intercepta os eventos usuais da página.' : 'Prepare manualmente a página da etapa e depois ative a seleção.');
    }
  };
  const selecting = () => {try { return window.top.__nexerTargetPicker?.active ?? active; } catch { return true; }};
  Promise.resolve(window.nexerTargetState()).then(state => {
    if (!revision) api.setActive(state.active === true, state.kind);
  }).catch(() => {}); // Stay locked if the private channel is unavailable.
  const command = name => {
    if (busy) return;
    busy = true;
    Promise.resolve(window.nexerTargetCommand(name)).catch(() => {busy = false;});
  };
  const toolbar = node => node?.closest('[data-nexer-target-picker]');
  const types = ['pointerdown','pointerup','mousedown','mouseup','click','dblclick','auxclick','contextmenu',
    'keydown','keyup','beforeinput','input','paste','submit','pointermove','mousemove','mouseover','mouseout'];
  for (const type of types) window.addEventListener(type, event => {
    const element = event.composedPath().find(node => node instanceof Element);
    if (toolbar(element)) {
      event.stopImmediatePropagation();
      if (event.cancelable) event.preventDefault();
      if (event.isTrusted && (type === 'click' || (type === 'keydown' && ['Enter',' '].includes(event.key)))) {
        const button = element.closest('[data-target-command]');
        if (button) command(button.dataset.targetCommand);
      }
      return;
    }
    if (!selecting()) return;
    if (event.cancelable) event.preventDefault();
    event.stopImmediatePropagation();
    if (type !== 'click' || !event.isTrusted || busy || !element) return;
    const target = kind === 'element' ? element.closest('button,a,input,select,textarea,[role="button"]') || element : element;
    const selector = window.__nexerSelectors?.forElement(target);
    if (!selector) return;
    selected = target;
    busy = true;
    Promise.resolve(window.nexerTargetCandidate({selector})).catch(() => {busy = false;});
  }, {capture: true, passive: false});
  const install = () => {
    if (window !== window.top) return;
    panel = document.createElement('div'); panel.dataset.nexerTargetPicker = 'true';
    panel.style.cssText = 'position:fixed;top:12px;right:12px;z-index:2147483647;background:#fff;color:#171719;padding:18px;border:1px solid #ddd;border-radius:12px;font:14px system-ui;max-width:340px;box-shadow:0 4px 24px #0003';
    const title = document.createElement('strong'); title.textContent = 'Corrigir alvo da etapa'; panel.append(title);
    note = document.createElement('p'); panel.append(note);
    for (const [name, label] of [['activate','Selecionar alvo'],['prepare','Preparar página'],['cancel','Cancelar seleção']]) {
      const button = document.createElement('button'); button.type = 'button';
      button.dataset.targetCommand = name; button.textContent = label;
      button.style.cssText = 'margin:4px;padding:8px;border:1px solid #ccc;border-radius:6px;background:#fff;color:#171719'; panel.append(button);
    }
    document.documentElement.append(panel);
    note.textContent = active ? 'Clique no elemento da etapa. A seleção intercepta os eventos usuais da página.' : 'Prepare manualmente a página da etapa e depois ative a seleção.';
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true});
  else install();
})();
