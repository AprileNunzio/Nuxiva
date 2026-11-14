const assert = require('node:assert/strict');
const path = require('node:path');
const postcss = require('postcss');
const tailwind = require('tailwindcss');

(async () => {
  const config = path.resolve(__dirname, '../tailwind.config.js');
  const result = await postcss([
    tailwind({
      config,
      content: [{ raw: 'md:flex hover:underline cq-lg:grid-cols-2 w-[18rem]', extension: 'html' }],
    }),
  ]).process('@tailwind utilities;', { from: undefined });
  const css = result.css;
  assert.ok(css.includes('.hover\\:underline:hover'), 'variant selectors must be escaped with a single backslash');
  assert.ok(!css.includes('\\\\:'), 'variant selectors must not be escaped twice');
  assert.ok(css.includes('.cq-lg\\:grid-cols-2'), 'container variants must be emitted');
  console.log('tailwind-escape ok');
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
