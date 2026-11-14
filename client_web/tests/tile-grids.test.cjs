const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '../src');
const targets = [
  'subapps/videosorveglianza/telecamere/View.tsx',
  'core_apps/store/View.tsx',
  'core_apps/people/identity/IdentityGallery.tsx',
];
const viewportColumns = /(?:^|[\s'"`])(?:xs|sm|md|lg|xl|2xl|3xl|4xl|5xl|6xl|8k):grid-cols-\d+/;

for (const target of targets) {
  const source = fs.readFileSync(path.join(root, target), 'utf8');
  assert.ok(source.includes('os-tiles'), `${target} must use the container-driven os-tiles grid`);
  assert.ok(!viewportColumns.test(source), `${target} must not drive columns from viewport breakpoints`);
}

const css = fs.readFileSync(path.join(root, 'index.css'), 'utf8');
const rule = css.match(/\.os-tiles\s*\{([^}]*)\}/);
assert.ok(rule, 'os-tiles rule must exist');
assert.match(rule[1], /display:\s*grid/);
assert.match(rule[1], /repeat\(auto-fill,\s*minmax\(min\(100%,\s*var\(--tile-min/);

console.log('tile-grids ok');
