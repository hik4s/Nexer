/* Structural identifiers only: never values, labels, URLs or arbitrary attributes. */
(() => {
  const vocabulary = new Set(('period start end company regional query search filter filters result results export submit apply run download report form table list menu panel tab tabs content main toolbar date input field button select check checkbox radio frame host').split(' '));
  const values = {
    type: new Set('text search email url tel password hidden file number date datetime-local time month week range color checkbox radio button submit reset'.split(' ')),
    role: new Set('button textbox searchbox combobox listbox option checkbox radio radiogroup slider spinbutton menu menuitem tab tablist table row cell list listitem dialog region navigation main form'.split(' ')),
    'aria-haspopup': new Set(['true', 'false', 'menu', 'listbox', 'tree', 'grid', 'dialog']),
    contenteditable: new Set(['', 'true', 'false', 'plaintext-only'])
  };
  const safeIdentifier = value => typeof value === 'string' && value.length <= 64 &&
    /^[a-z]+(?:[-_][a-z]+)*$/.test(value) && value.split(/[-_]/).every(word => vocabulary.has(word));
  const tagOf = element => /^[a-z][a-z0-9-]*$/.test(element.localName) ? element.localName : null;
  const shadowMatches = (scope, css) => {
    // Generated selectors use simple tokens, descendants and child combinators.
    // Replay crosses open shadow roots and treats their host as a parent.
    const tokens = css.trim().split(/\s+/), parts = [], relations = [];
    let pending = null;
    for (const token of tokens) {
      if (token === '>') { pending = 'child'; continue; }
      if (parts.length) relations.push(pending || 'descendant');
      parts.push(token); pending = null;
    }
    const parent = element => element.parentElement || element.getRootNode().host || null;
    const match = (element, index) => {
      if (!(element instanceof Element)) return false;
      if (parts[index] === ':scope' ? element !== scope : !element.matches(parts[index])) return false;
      if (index === 0) return true;
      let owner = parent(element);
      if (relations[index - 1] === 'child') return match(owner, index - 1);
      while (owner) { if (match(owner, index - 1)) return true; owner = parent(owner); }
      return false;
    };
    const matches = new Set();
    const visit = root => {
      root.querySelectorAll('*').forEach(element => {
        if (match(element, parts.length - 1)) matches.add(element);
        if (element.shadowRoot) visit(element.shadowRoot);
      });
    };
    visit(scope);
    if (scope.shadowRoot) visit(scope.shadowRoot);
    return matches;
  };
  const unique = (scope, css, target) => {
    try { const matches = shadowMatches(scope, css); return matches.size === 1 && matches.has(target); }
    catch { return false; }
  };
  const candidates = (element, identifiers) => {
    const tag = tagOf(element);
    if (!tag) return [];
    const result = [];
    if (identifiers) for (const attribute of ['id', 'data-testid', 'name']) {
      const value = element.getAttribute(attribute);
      if (safeIdentifier(value)) result.push(attribute === 'id' ? '#' + value : tag + '[' + attribute + '="' + value + '"]');
    }
    const attributes = [];
    for (const attribute of ['type', 'role', 'aria-haspopup', 'contenteditable']) {
      const value = element.getAttribute(attribute);
      if ((attribute !== 'type' || tag === 'input') && values[attribute].has(value)) {
        const part = '[' + attribute + '="' + value + '"]';
        attributes.push(part);
        result.push(tag + part);
      }
    }
    if (attributes.length > 1) result.push(tag + attributes.join(''));
    result.push(tag);
    return result;
  };
  const positional = (element, boundary) => {
    const parts = [];
    while (element instanceof Element && element !== boundary) {
      const tag = tagOf(element);
      if (!tag) return null;
      const parent = element.parentElement;
      const siblings = [...(parent || element.getRootNode()).children].filter(child => child.localName === tag);
      parts.unshift(tag + ':nth-of-type(' + (siblings.indexOf(element) + 1) + ')');
      element = parent;
    }
    return parts.join(' > ');
  };
  const localSelector = (element, scope, identifiers) => {
    const own = candidates(element, identifiers);
    for (const css of own) if (unique(scope, css, element)) return css;
    for (let ancestor = element.parentElement; ancestor && ancestor !== scope; ancestor = ancestor.parentElement) {
      for (const anchor of candidates(ancestor, identifiers)) {
        if (!unique(scope, anchor, ancestor)) continue;
        for (const css of own) if (unique(ancestor, css, element)) {
          const combined = anchor + ' ' + css;
          if (unique(scope, combined, element)) return combined;
        }
      }
    }
    const css = positional(element, scope instanceof Element ? scope : null);
    const relative = scope instanceof Element ? ':scope > ' + css : css;
    return css && unique(scope, relative, element) ? relative : null;
  };
  const forElement = element => {
    if (!(element instanceof Element) || !element.isConnected) return null;
    const root = element.getRootNode();
    const local = localSelector(element, root, true);
    if (!local) return null;
    if (!root.host) return local;
    const host = forElement(root.host);
    const matches = shadowMatches(root.host, local);
    return host && matches.size === 1 && matches.has(element) ? host + ' ' + local : null;
  };
  const relativeTo = (element, scope) => {
    if (!(element instanceof Element) || !(scope instanceof Element) || !scope.contains(element) || element === scope) return null;
    // IDs are per-document, not a reusable identity for buttons across rows.
    return localSelector(element, scope, false);
  };
  window.__nexerSelectors = {forElement, relativeTo};
})();
