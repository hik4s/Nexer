/* Nexer local smart observation: DOM structure and readiness, never values/text/network. */
(() => {
  if (window.__nexerIntelligenceInstalled) return;
  window.__nexerIntelligenceInstalled = true;
  const candidates = 'button,a,input,select,textarea,[role="button"],[role="option"],[role="listbox"],[contenteditable]';
  const observed = new WeakMap();
  const changes = new WeakMap();
  let generation = 0;
  let previousActionAt = 0;

  const forbidden = element => {
    for (let node = element; node instanceof Element; node = node.parentElement) {
      if (node.matches('[data-nexer-recorder],input[type="password"],input[type="hidden"],input[type="file"]')) return true;
      if (/password|passwd|username|cre_username|cre_password|token|secret|credential/i.test(
        [node.getAttribute('name') || '', node.id || '', node.getAttribute('autocomplete') || ''].join(' '))) return true;
      if (node.matches('form') && node.querySelector('input[type="password"]')) return true;
    }
    return false;
  };
  const inspect = element => ({
    visible: Boolean(element.isConnected && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden'),
    enabled: !element.matches(':disabled') && element.getAttribute('aria-disabled') !== 'true'
  });
  const watch = (element, added = false) => {
    if (!(element instanceof Element) || !element.matches(candidates) || forbidden(element)) return;
    const current = inspect(element);
    const before = observed.get(element);
    observed.set(element, current);
    if (!generation || performance.now() - previousActionAt > 30000) return;
    let state = null;
    if ((!before && added && current.visible) || (before && !before.visible && current.visible)) state = 'visible';
    else if (before && !before.enabled && current.enabled && current.visible) state = 'enabled';
    if (state) changes.set(element, {generation, state, at: performance.now()});
  };
  const subtree = (root, added) => {
    if (!(root instanceof Element)) return;
    watch(root, added);
    let count = 0;
    for (const element of root.querySelectorAll(candidates)) {
      if (++count > 250) break;
      watch(element, added);
    }
  };
  const setup = () => {
    subtree(document.documentElement, false);
    const observer = new MutationObserver(records => {
      if (window.__nexerRecorderActive === false) return;
      let count = 0;
      for (const record of records) {
        if (++count > 200) break;
        if (record.type === 'attributes') {
          const element = record.target;
          if (element instanceof Element) {
            if (element.matches(candidates)) watch(element);
            // Parent visibility can change without changing the button's own attributes.
            else subtree(element, false);
          }
        } else {
          for (const node of record.addedNodes) {
            if (++count > 200) break;
            subtree(node, true);
          }
        }
      }
    });
    observer.observe(document.documentElement, {
      subtree: true, childList: true,
      attributes: true, attributeFilter: ['disabled', 'aria-disabled', 'hidden', 'style', 'class']
    });
  };
  window.__nexerActionRecorded = () => {
    generation += 1;
    previousActionAt = performance.now();
  };
  window.__nexerReadinessFor = element => {
    const observation = changes.get(element);
    if (!observation || observation.generation !== generation || !generation ||
        performance.now() - observation.at > 30000 || forbidden(element)) return null;
    const now = inspect(element);
    if (!now.visible || (observation.state === 'enabled' && !now.enabled)) return null;
    changes.delete(element);
    return {state: observation.state};
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup, {once: true});
  else setup();
})();
