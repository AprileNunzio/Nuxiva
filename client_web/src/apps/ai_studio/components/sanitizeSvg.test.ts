import { describe, expect, it } from 'vitest';
import { sanitizeSvg } from '../sanitizeSvg';

describe('sanitizeSvg', () => {
  it('strips scripts, inline handlers, foreignObject and javascript: links', () => {
    const dirty =
      '<svg onload="x()"><script>alert(1)</script><foreignObject><div/></foreignObject><a href="javascript:alert(1)">l</a><circle r="1"/></svg>';
    const clean = sanitizeSvg(dirty);
    expect(clean).not.toMatch(/script|onload|foreignObject|javascript:/i);
    expect(clean).toContain('<circle');
  });
});
