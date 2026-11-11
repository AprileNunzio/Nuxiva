const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');

const source = fs.readFileSync(path.join(__dirname, '../src/shared/storage/scopedStorage.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;

class MockLocalStorage {
  constructor() {
    this._store = new Map();
  }
  get length() {
    return this._store.size;
  }
  key(index) {
    return Array.from(this._store.keys())[index] || null;
  }
  getItem(key) {
    return this._store.has(key) ? this._store.get(key) : null;
  }
  setItem(key, value) {
    this._store.set(key, String(value));
  }
  removeItem(key) {
    this._store.delete(key);
  }
  clear() {
    this._store.clear();
  }
}

const mockWindow = {
  localStorage: new MockLocalStorage(),
  dispatchEvent: () => true,
  CustomEvent: class CustomEvent { constructor(type, init) { this.type = type; this.detail = init?.detail; } }
};

const context = { exports: {}, window: mockWindow };
vm.runInNewContext(compiled, context);
const createScopedStorage = context.exports.createScopedStorage;

const storageA = createScopedStorage('app_alpha');
const storageB = createScopedStorage('app_beta');

assert.equal(storageA.setItem('theme', 'dark'), true);
assert.equal(storageA.getItem('theme'), 'dark');

assert.equal(storageB.getItem('theme'), null);
assert.equal(storageB.setItem('theme', 'light'), true);

assert.equal(storageA.getItem('theme'), 'dark');
assert.equal(storageB.getItem('theme'), 'light');

assert.deepEqual([...storageA.getAllKeys()], ['theme']);
assert.deepEqual([...storageB.getAllKeys()], ['theme']);

assert.equal(mockWindow.localStorage.getItem('nuxiva:app:app_alpha:theme'), 'dark');
assert.equal(mockWindow.localStorage.getItem('nuxiva:app:app_beta:theme'), 'light');

storageA.clear();
assert.equal(storageA.getItem('theme'), null);
assert.equal(storageB.getItem('theme'), 'light');

console.log('Zero-Trust scoped storage isolation and compartmentalization passed.');
