import { ATTR, EVENT, SELECTOR, TRANSLATABLE_ATTRIBUTES } from "./contracts.js";
import { decodeParams, validKey, validLocale, validScope } from "./sanitizer.js";
import { render } from "./translator.js";

export class DomScanner {
  constructor({ store, boundary, locale }) {
    this._store = store;
    this._boundary = boundary;
    this._locale = locale;
    this._generation = 0;
    this._observer = null;
    this._pending = new Set();
    this._scheduled = false;
    this._report = (code, context, level) => this._boundary.report(code, context, level);
  }

  get locale() {
    return this._locale;
  }

  observe(root) {
    this._observer?.disconnect();
    this._observer = new MutationObserver((records) => {
      for (const record of records) {
        if (record.type === "attributes") this._queue(record.target);
        else record.addedNodes.forEach((node) => this._queue(node));
      }
    });
    this._observer.observe(root, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: [ATTR.scope, ATTR.text, ATTR.attributes, ATTR.params],
    });
    return this.scan(root);
  }

  async setLocale(candidate) {
    const locale = validLocale(candidate);
    if (!locale) {
      this._report("LOCALE_REJECTED", { requested: String(candidate) });
      return;
    }
    if (locale === this._locale) return;
    this._locale = locale;
    this._generation += 1;
    await this.scan(document.body);
    window.dispatchEvent(new CustomEvent(EVENT.changed, { detail: Object.freeze({ locale }) }));
  }

  async scan(root) {
    if (!root || root.nodeType !== Node.ELEMENT_NODE) return;
    const groups = this._collect(root);
    await Promise.all([...groups].map(([scope, group]) => this._apply(scope, group)));
  }

  _queue(node) {
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    this._pending.add(node);
    if (this._scheduled) return;
    this._scheduled = true;
    queueMicrotask(() => {
      this._scheduled = false;
      const roots = [...this._pending].filter((candidate) => candidate.isConnected);
      this._pending.clear();
      roots.forEach((candidate) => this._boundary.guard(this.scan(candidate), "SCAN_FAILURE"));
    });
  }

  _collect(root) {
    const nodes = root.matches(SELECTOR.node) ? [root] : [];
    nodes.push(...root.querySelectorAll(SELECTOR.node));
    const groups = new Map();
    for (const node of nodes) {
      const owner = node.closest(SELECTOR.scope);
      const scope = owner ? validScope(owner.getAttribute(ATTR.scope)) : null;
      if (!scope) {
        this._report(owner ? "INVALID_SCOPE" : "ORPHAN_I18N_NODE", { key: node.getAttribute(ATTR.text), scope: owner?.getAttribute(ATTR.scope) });
        continue;
      }
      const group = groups.get(scope) || { owners: new Set(), nodes: [] };
      group.owners.add(owner);
      group.nodes.push(node);
      groups.set(scope, group);
    }
    return groups;
  }

  async _apply(scope, group) {
    const generation = this._generation;
    const locale = this._locale;
    const bundle = await this._store.load(scope, locale);
    if (!bundle || generation !== this._generation) return;
    group.owners.forEach((owner) => {
      owner.setAttribute("lang", locale);
      owner.setAttribute("dir", bundle.direction);
    });
    group.nodes.forEach((node) => this._translate(node, bundle));
  }

  _translate(node, bundle) {
    const params = this._params(node, bundle.scope);
    if (!params) return;
    const key = node.getAttribute(ATTR.text);
    if (key !== null) this._text(node, key, bundle, params);
    const spec = node.getAttribute(ATTR.attributes);
    if (spec !== null) this._attributes(node, spec, bundle, params);
  }

  _params(node, scope) {
    const raw = node.getAttribute(ATTR.params);
    if (raw === null) return Object.create(null);
    const params = decodeParams(raw);
    if (!params) this._report("MALFORMED_I18N_PARAMS", { scope, key: node.getAttribute(ATTR.text) });
    return params;
  }

  _text(node, key, bundle, params) {
    if (!validKey(key)) {
      this._report("INVALID_TRANSLATION_KEY", { scope: bundle.scope, key });
      return;
    }
    if (node.childElementCount > 0) {
      this._report("NON_LEAF_I18N_NODE", { scope: bundle.scope, key });
      return;
    }
    const text = render(bundle, key, params, this._report);
    if (text !== null && node.textContent !== text) node.textContent = text;
  }

  _attributes(node, spec, bundle, params) {
    for (const pair of spec.split(",")) {
      const [name, key] = pair.split(":").map((part) => part.trim());
      if (!TRANSLATABLE_ATTRIBUTES.includes(name) || !validKey(key)) {
        this._report("I18N_ATTRIBUTE_REJECTED", { scope: bundle.scope, name, key });
        continue;
      }
      const text = render(bundle, key, params, this._report);
      if (text !== null && node.getAttribute(name) !== text) node.setAttribute(name, text);
    }
  }
}
