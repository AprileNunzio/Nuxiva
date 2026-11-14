const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '../src');
const viewport = /(?<![\w-])(?:xs|sm|md|lg|xl|2xl|3xl|4xl|5xl|6xl|8k):(?:[a-z-]+:)*(?:grid-cols-|col-span-|col-start-|col-end-|grid-flow-|auto-cols-|row-span-)/;
const pageWidthCap = /max-w-(?:\[?\d|[2-7]?xl\b|screen)/;

const walk = (dir) =>
  fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return walk(full);
    return /\.tsx$/.test(entry.name) && !/\.test\.tsx$/.test(entry.name) ? [full] : [];
  });

const offenders = [];
for (const file of walk(root)) {
  const lines = fs.readFileSync(file, 'utf8').split('\n');
  lines.forEach((line, index) => {
    if (viewport.test(line)) offenders.push(`${path.relative(root, file)}:${index + 1} viewport-driven grid, use cq-* or os-tiles`);
  });
}
assert.deepEqual(offenders, [], offenders.join('\n'));

const layout = fs.readFileSync(path.join(root, 'shared/ui/layout.ts'), 'utf8');
assert.ok(!pageWidthCap.test(layout), 'PAGE_CLASS must not cap the page width');
assert.ok(/cq-/.test(layout), 'PAGE_CLASS spacing must be container-driven');

const plugin = fs.readFileSync(path.resolve(__dirname, '../design/layout/plugin.js'), 'utf8');
assert.match(plugin, /@container \(min-width/);
const config = fs.readFileSync(path.resolve(__dirname, '../tailwind.config.js'), 'utf8');
assert.match(config, /layoutPlugin/);

const kit = fs.readFileSync(path.join(root, 'core_apps/shared/kit.tsx'), 'utf8');
assert.ok(/PAGE_CLASS/.test(kit), 'AppFrame must use the shared page layout');

console.log('layout-system ok');
