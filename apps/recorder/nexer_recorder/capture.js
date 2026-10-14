(() => {
  window.__nexerRecorderBootstrap?.abort();
  window.__nexerRecorderController?.abort();
  const bootstrap = new AbortController();
  window.__nexerRecorderBootstrap = bootstrap;
  window.__nexerRecorderInstalled = false;
  let initialization = 0;
  let replacing = false;
  const install = () => {
  replacing = true;
  window.__nexerRecorderController?.abort();
  replacing = false;
  if (bootstrap.signal.aborted) return;
  const controller = new AbortController();
  window.__nexerRecorderController = controller;
  bootstrap.signal.addEventListener('abort', () => controller.abort(), {once: true, signal: controller.signal});
  controller.signal.addEventListener('abort', () => { if (!replacing) bootstrap.abort(); }, {once: true});
  const options = {capture: true, signal: controller.signal};
  window.__nexerRecorderDocument = document;
  window.__nexerRecorderInstalled = true;
  const active = () => window.__nexerRecorderActive !== false;
  window.__nexerIntelligence?.install(controller.signal);
  const semantic = new Set(['period_start', 'period_end', 'company', 'regional']);
  const parent = element => element.parentElement || element.getRootNode().host || null;
  const blocked = element => {
    for (let node = element; node; node = parent(node)) {
      if (node.matches('[data-nexer-recorder],input[type="password"],input[type="hidden"],input[type="file"]') ||
          /password|passwd|username|cre_username|cre_password|token|secret|credential/i.test(
            [node.getAttribute('name') || '', node.id || '', node.getAttribute('autocomplete') || ''].join(' ')) ||
          (node.matches('form') && node.querySelector('input[type="password"]'))) return true;
    }
    return false;
  };
  const selector = element => window.__nexerSelectors.forElement(element);
  window.__nexerStructuralSelector = selector;
  const fieldSnapshots = new WeakMap();
  const labelSnapshots = new WeakMap();
  const structuralText = node => {
    if (!node) return '';
    if (node.matches('input,select,textarea,[contenteditable]')) return '';
    const copy = node.cloneNode(true);
    copy.querySelectorAll('input,select,textarea,[contenteditable],script,style').forEach(child => child.remove());
    return (copy.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 100);
  };
  const snapshot = element => {
    if (!active() || fieldSnapshots.has(element) || blocked(element)) return;
    let control = element.matches('textarea,[contenteditable]') ? 'textarea' : element.matches('select') ? (element.multiple ? 'multiselect' : 'select') : element.type;
    if (element.matches('[role="listbox"]')) control = 'select';
    if (element.matches('[role="radiogroup"],fieldset,form') && element.querySelector('input[type="radio"]')) control = 'radio';
    if (!['text','textarea','date','datetime-local','time','month','week','number','email','url','tel','search','range','color','select','multiselect','checkbox','radio'].includes(control)) return;
    const field = {control, required: Boolean(element.required)};
    const labelled = (element.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean)
      .map(id => structuralText(element.getRootNode().getElementById?.(id))).join(' ').trim();
    const label = labelled || element.getAttribute('aria-label') ||
      [...(element.labels || [])].map(structuralText).join(' ').trim() || structuralText(element.querySelector('legend'));
    if (label) labelSnapshots.set(element, label.slice(0, 100));
    for (const [attribute, key] of [['minlength','min_length'], ['maxlength','max_length'], ['rows','rows']]) {
      const raw = element.getAttribute(attribute);
      if (raw !== null && /^\d+$/.test(raw)) field[key] = Number(raw);
    }
    if (['number','range','date','datetime-local','time','month','week'].includes(control)) for (const key of ['min','max','step']) {
      const raw = element.getAttribute(key);
      if (key === 'step' && raw === 'any') field.step = 'any';
      else if (raw !== null && raw.trim() && key !== 'step' && ['date','datetime-local','time','month','week'].includes(control)) field[key] = raw;
      else if (raw !== null && raw.trim() && Number.isFinite(Number(raw))) field[key] = Number(raw);
    }
    const pattern = element.getAttribute('pattern');
    if (pattern && pattern.length <= 512) field.pattern = pattern;
    const mode = element.getAttribute('inputmode');
    if (['none','text','decimal','numeric','tel','search','email','url'].includes(mode)) field.input_mode = mode;
    fieldSnapshots.set(element, field);
  };
  document.querySelectorAll('input,select,textarea,[contenteditable]').forEach(snapshot);
  document.addEventListener('focusin', event => {if (!active()) return; const element = event.composedPath().find(node => node instanceof Element); if (element) snapshot(element);}, options);
  const target = event => event.composedPath().find(node => node instanceof Element);
  const send = (action, element, extra = {}) => {
    if (!active() || controller.signal.aborted || !(element instanceof Element) || blocked(element)) return false;
    const location = selector(element);
    if (!location) { window.nexerUnsupported?.('selector'); return false; }
    const frames = [];
    try {
      for (let owner = window; owner !== owner.top; owner = owner.parent) {
        if (!owner.frameElement || !owner.parent.__nexerStructuralSelector) throw new Error('FRAME_UNSUPPORTED');
        frames.unshift(owner.parent.__nexerStructuralSelector(owner.frameElement));
      }
    } catch { window.nexerUnsupported?.('frame'); return false; }
    let field;
    if (['fill','select','check','set_value','choose','choose_radio'].includes(action)) {
      snapshot(element);
      field = fieldSnapshots.get(element) || {control: action === 'choose_radio' ? 'radio' : action === 'choose' ? 'select' : 'text'};
    }
    const label = field ? labelSnapshots.get(element) : null;
    const readiness = ['click', 'download', 'fill', 'select', 'check', 'choose', 'choose_radio', 'set_value'].includes(action)
      ? window.__nexerIntelligence?.readinessFor(element) : null;
    window.nexerCapture({action, selector: location, ...extra, ...(readiness ? {readiness} : {}),
      ...(field ? {field} : {}), ...(label ? {label} : {}), ...(frames.length ? {frames} : {})}).catch(() => {});
    if (!['scroll', 'hover', 'wait_for'].includes(action)) window.__nexerIntelligence?.recordAction();
    return true;
  };
  const parameter = element => semantic.has(element.id) ? {parameter: element.id} : {};
  const radio = element => {
    const group = element.closest('[role="radiogroup"],fieldset,form') || element.parentElement;
    if (group && !blocked(element)) {
      const groups = [];
      for (const option of group.querySelectorAll('input[type="radio"]')) {
        const identity = option.name || option;
        if (!groups.includes(identity)) groups.push(identity);
      }
      send('choose_radio', group, {...parameter(group), group_index: groups.indexOf(element.name || element)});
    }
  };
  let activation = null;
  let manualWaitState = null;
  let guideManualWait = () => {};
  // Read only structural labels, never control values, selected options, URLs or request bodies.
  document.addEventListener('click', event => {
    const original = target(event);
    if (!active() || !original) return;
    if (manualWaitState) {
      if (original.closest('[data-nexer-recorder]')) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      const state = manualWaitState;
      manualWaitState = null;
      if (send('wait_for', original.closest('button,a,input,select,[role="button"]') || original,
          {state, learning: {source: 'manual', confidence: 'high'}})) {
        guideManualWait('Condição adicionada à gravação.');
      } else guideManualWait('Não foi possível marcar este elemento. Tente outro.');
      return;
    }
    if (original.closest('canvas')) { window.nexerUnsupported?.('canvas'); return; }
    const element = original.closest('button,a,[role="button"],input,[role="option"]') || original;
    if (element.matches('option,select')) return;
    const label = original.closest('label');
    if (label?.control?.matches('input[type="checkbox"],input[type="radio"]') && !element.matches('input')) return;
    if (element.matches('input[type="radio"]')) { radio(element); return; }
    if (element.matches('input[type="checkbox"]')) { send('check', element, parameter(element)); return; }
    if (element.matches('[role="option"]')) {
      const listbox = element.closest('[role="listbox"]');
      if (listbox) send('choose', listbox, parameter(listbox));
      else window.nexerUnsupported?.('custom-option');
      return;
    }
    if (event.detail === 0 && activation && performance.now() - activation.time < 1000 &&
        (element === activation.element || (activation.form && element.closest('form') === activation.form))) {
      activation = null;
      return;
    }
    const download = element.matches('a[download]') || (window.__nexerDownloadSelectors || []).some(location => element.matches(location)) ||
      (element.matches('button,a,[role="button"]') && /^(baixar|download)(\b|\s)/i.test(
        element.getAttribute('aria-label') || element.getAttribute('title') || structuralText(element)));
    const row = download ? element.closest('tr,li,[role="row"],[role="listitem"]') : null;
    let collection;
    if (row && row.parentElement) {
      const relativeButton = window.__nexerSelectors.relativeTo(element, row);
      const container = selector(row.parentElement);
      if (relativeButton && container) {
        collection = {rows: container + ' > ' + row.tagName.toLowerCase(),
          name: row.matches('tr') ? 'td:first-child' : ':scope',
          button: relativeButton};
      }
    }
    send(download ? 'download' : 'click', element,
      {...(download && collection ? {collection} : !download && event.detail > 1 ? {click_count: Math.min(event.detail, 3)} : {})});
  }, options);
  for (const [eventName, button] of [['contextmenu', 'right'], ['auxclick', 'middle']]) {
    document.addEventListener(eventName, event => {
      if (button === 'middle' && event.button !== 1) return;
      send('click', target(event), {button});
    }, options);
  }
  const input = event => {
    const element = target(event);
    if (!active() || !element) return;
    if (element.matches('input[type="file"]')) { window.nexerUnsupported?.('upload'); return; }
    if (element.matches('input[readonly],textarea[readonly]')) { window.nexerUnsupported?.('readonly-field'); return; }
    if (element.matches('input[type="range"],input[type="color"]')) {
      send('set_value', element, {...parameter(element), input_type: element.type});
    } else if (element.matches('select')) {
      send('select', element, {...parameter(element), multiple: element.multiple});
    } else if (element.matches('input[type="radio"]')) {
      radio(element);
    } else if (element.matches('input[type="checkbox"]')) {
      send('check', element, parameter(element));
    } else if (element.matches('textarea,input:not([type="button"]):not([type="submit"]):not([type="reset"]):not([type="file"])') || element.isContentEditable) {
      const editable = element.closest('[contenteditable="true"],[contenteditable=""]') || element;
      send('fill', editable, parameter(editable));
    }
  };
  const edited = new WeakSet();
  document.addEventListener('input', event => { if (!active()) return; const element = target(event); if (element) edited.add(element); input(event); }, options);
  document.addEventListener('change', event => {
    if (!active()) return;
    const element = target(event);
    if (element && edited.has(element)) { edited.delete(element); return; }
    input(event);
  }, options);
  document.addEventListener('keydown', event => {
    if (!active()) return;
    const element = target(event);
    if (!element || event.ctrlKey || event.metaKey || event.altKey || element.matches('select,input[type="checkbox"],input[type="radio"]')) return;
    const editable = element.matches('input,textarea') || element.isContentEditable;
    const navigation = ['Enter', 'Tab', 'Escape', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End', 'PageUp', 'PageDown'];
    const key = event.key === ' ' ? 'Space' : event.key;
    const multiline = element.matches('textarea') || element.isContentEditable;
    if ((!editable && [...navigation, 'Space'].includes(key)) || (editable && ['Tab', 'Escape', ...(multiline ? [] : ['Enter'])].includes(key))) {
      if (send('press', element, {key})) activation = ['Enter', 'Space'].includes(key) ? {element, form: element.closest('form'), time: performance.now()} : null;
    }
  }, options);
  const pendingScrolls = new Map();
  document.addEventListener('scroll', event => {
    if (!active()) return;
    const element = event.target === document ? document.documentElement : target(event);
    if (!element || blocked(element)) return;
    clearTimeout(pendingScrolls.get(element));
    pendingScrolls.set(element, setTimeout(() => {
      pendingScrolls.delete(element);
      const position = element === document.documentElement ? document.scrollingElement : element;
      send('scroll', element, {x: Math.max(0, Math.round(position.scrollLeft)), y: Math.max(0, Math.round(position.scrollTop))});
    }, 120));
  }, options);
  const pendingHovers = new Map();
  document.addEventListener('pointerover', event => {
    if (!active()) return;
    const element = target(event)?.closest('[aria-haspopup],[role="menuitem"]');
    if (!element || element.contains(event.relatedTarget)) return;
    clearTimeout(pendingHovers.get(element));
    pendingHovers.set(element, setTimeout(() => { pendingHovers.delete(element); send('hover', element); }, 250));
  }, options);
  document.addEventListener('pointerout', event => {
    if (!active()) return;
    const element = target(event)?.closest('[aria-haspopup],[role="menuitem"]');
    if (element && !element.contains(event.relatedTarget)) { clearTimeout(pendingHovers.get(element)); pendingHovers.delete(element); }
  }, options);
  let dragged = null;
  document.addEventListener('dragstart', event => { if (active()) dragged = target(event); }, options);
  document.addEventListener('drop', event => {
    if (!active()) { dragged = null; return; }
    const destination = target(event);
    if (dragged && destination && !blocked(destination)) send('drag', dragged, {target_selector: selector(destination)});
    dragged = null;
  }, options);
  if (window === window.top && document.body && typeof window.nexerFinishRecording === 'function') {
    document.querySelector('[data-nexer-recorder="toolbar"]')?.remove();
    const toolbar = document.createElement('div');
    toolbar.setAttribute('data-nexer-recorder', 'toolbar');
    toolbar.style.cssText = 'position:fixed;top:16px;right:16px;z-index:2147483647;background:#171719;color:white;padding:12px;border-radius:12px;box-shadow:0 4px 20px #0004;font:14px system-ui';
    const button = document.createElement('button');
    button.textContent = active() ? 'Parar gravação' : 'Iniciar gravação';
    button.type = 'button';
    button.style.cssText = 'background:white;color:#171719;border:0;border-radius:8px;padding:10px 16px;cursor:pointer;font:inherit';
    const guidance = document.createElement('p');
    guidance.textContent = active() ? '' : 'Faça login manual, abra a rota configurada e inicie a gravação.';
    toolbar.append(guidance);
    button.onclick = async () => {
      if (!active()) {
        button.disabled = true;
        try {
          let result = await window.nexerStartRecording();
          while (result.pending && !controller.signal.aborted) {
            await new Promise(resolve => setTimeout(resolve, 100));
            result = await window.nexerStartRecordingStatus();
          }
          if (result.started) { window.__nexerRecorderActive = true; window.__nexerIntelligence?.reset(); button.textContent = 'Parar gravação'; guidance.textContent = 'Gravando ações.'; }
          else guidance.textContent = result.message;
        } catch { guidance.textContent = 'Não foi possível iniciar. Revise a página configurada.'; }
        button.disabled = false;
        return;
      }
      button.disabled = true;
      button.textContent = 'Finalizando…';
      for (const timer of pendingScrolls.values()) clearTimeout(timer);
      for (const timer of pendingHovers.values()) clearTimeout(timer);
      controller.abort();
      await window.nexerFinishRecording();
    };
    toolbar.append(button);
    const waitBox = document.createElement('div');
    waitBox.style.cssText = 'display:flex;gap:6px;margin-top:8px;align-items:center;flex-wrap:wrap';
    const waitState = document.createElement('select');
    waitState.setAttribute('aria-label', 'Tipo da espera inteligente');
    waitState.style.cssText = 'background:white;color:#171719;padding:7px;border-radius:6px;max-width:150px';
    for (const [value, caption] of [['visible', 'Aguardar aparecer'], ['enabled', 'Aguardar habilitar'],
                                    ['hidden', 'Aguardar desaparecer'], ['disabled', 'Aguardar desabilitar']]) {
      const option = document.createElement('option');
      option.value = value;
      option.textContent = caption;
      waitState.append(option);
    }
    const markWait = document.createElement('button');
    markWait.type = 'button';
    markWait.textContent = 'Marcar espera';
    markWait.style.cssText = 'background:#eef2fb;color:#171719;border:0;border-radius:6px;padding:8px;cursor:pointer';
    markWait.onclick = () => {
      if (!active()) { guidance.textContent = 'Inicie a gravação antes de marcar uma espera.'; return; }
      manualWaitState = waitState.value;
      guidance.textContent = 'Clique no elemento que deve atingir essa condição. O clique não será executado.';
    };
    guideManualWait = message => { guidance.textContent = message; };
    waitBox.append(waitState, markWait);
    toolbar.append(waitBox);
    document.body.append(toolbar);
  }
  };
  const initialize = async () => {
    const revision = ++initialization;
    if (bootstrap.signal.aborted) return;
    if (typeof window.nexerRecordingState === 'function') {
      window.__nexerRecorderActive = false;
      let recordingActive;
      try { recordingActive = await window.nexerRecordingState(); }
      catch { return; }
      if (bootstrap.signal.aborted || revision !== initialization) return;
      window.__nexerRecorderActive = recordingActive;
    }
    if (bootstrap.signal.aborted || revision !== initialization) return;
    install();
  };
  initialize();
  if (document.readyState === 'loading') window.addEventListener('DOMContentLoaded', initialize, {once: true, signal: bootstrap.signal});
})();


