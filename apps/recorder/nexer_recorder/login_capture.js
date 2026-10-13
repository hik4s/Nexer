(() => {
  const install = () => {
    if (window.__nexerLoginPickerInstalled) return;
    window.__nexerLoginPickerInstalled = true;
    const fields = ['username_target', 'password_target', 'submit_target'];
    const names = ['Clique no campo de usuário', 'Clique no campo de senha', 'Clique no botão de entrada'];
    const structural = element => {
      const root = element.getRootNode(); const parts = [];
      while (element instanceof Element) {
        const tag = element.tagName.toLowerCase();
        if (!/^[a-z][a-z0-9-]*$/.test(tag)) return null;
        const siblings = [...(element.parentElement ? element.parentElement.children : element.getRootNode().children)].filter(item => item.tagName === element.tagName);
        parts.unshift(`${tag}:nth-of-type(${siblings.indexOf(element) + 1})`);
        element = element.parentElement;
      }
      return root.host ? structural(root.host) + ' ' + parts.join(' > ') : parts.join(' > ');
    };
    window.__nexerLoginSelector = structural;
    if (window === window.top) {
      window.__nexerLoginStage = 0;
      const panel = document.createElement('div'); panel.dataset.nexerLoginPicker = 'true';
      panel.style.cssText = 'position:fixed;top:12px;right:12px;z-index:2147483647;background:#102033;color:white;padding:18px;border-radius:12px;font:15px system-ui;max-width:360px;box-shadow:0 4px 24px #0005';
      const instruction = document.createElement('strong'); instruction.textContent = names[0]; panel.append(instruction);
      const note = document.createElement('p'); note.textContent = 'Aponte os campos sem digitar credenciais. A seleção não envia o formulário.'; panel.append(note);
      fields.forEach((field, index) => {
        const button = document.createElement('button'); button.type = 'button'; button.textContent = ['Usuário', 'Senha', 'Entrar'][index];
        button.style.cssText = 'margin-right:8px;padding:8px';
        button.addEventListener('click', () => {window.__nexerLoginStage = index; instruction.textContent = names[index];}); panel.append(button);
      });
      document.documentElement.append(panel);
      window.__nexerLoginInstruction = instruction;
    }
    const picker = element => element?.closest('[data-nexer-login-picker]');
    for (const eventName of ['beforeinput','keydown','paste','submit','pointerdown','mousedown']) document.addEventListener(eventName, event => {
      const element = event.composedPath().find(node => node instanceof Element);
      if (!picker(element)) {event.preventDefault(); event.stopImmediatePropagation();}
    }, true);
    document.addEventListener('click', event => {
      const element = event.composedPath().find(node => node instanceof Element);
      if (!element || picker(element)) return;
      event.preventDefault(); event.stopImmediatePropagation();
      try {
        const stage = window.top.__nexerLoginStage;
        if (stage < 0 || stage > 2) return;
        const target = stage === 2 ? element.closest('button,input[type=submit],input[type=button],[role=button]') : element;
        if (!target || (stage === 0 && !target.matches('input:not([type=password]):not([type=hidden]):not([type=file]),textarea')) || (stage === 1 && !target.matches('input[type=password]'))) return;
        const frames = [];
        for (let owner = window; owner !== owner.top; owner = owner.parent) {
          if (!owner.frameElement || !owner.parent.__nexerLoginSelector) return;
          frames.unshift(owner.parent.__nexerLoginSelector(owner.frameElement));
        }
        const selector = structural(target); if (!selector) return;
        window.nexerLoginTarget({field: fields[stage], selector, frames}).catch(() => {});
        window.top.__nexerLoginStage = stage + 1;
        window.top.__nexerLoginInstruction.textContent = names[stage + 1] || 'Campos identificados. Concluindo…';
      } catch { /* Cross-origin frames are not recorded. */ }
    }, true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', install, {once:true}); else install();
})();
