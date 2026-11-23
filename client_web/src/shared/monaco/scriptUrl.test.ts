import { describe, expect, it } from 'vitest';
import { sameOriginScriptUrl } from './scriptUrl';

const ORIGIN = 'https://nuxiva.local';
const BASE = 'https://nuxiva.local/admin/';

describe('sameOriginScriptUrl', () => {
  it('resolves bundled worker paths on the same origin', () => {
    expect(sameOriginScriptUrl('/assets/editor.worker-abc.js', ORIGIN, BASE)).toBe('https://nuxiva.local/assets/editor.worker-abc.js');
  });

  it('rejects scripts from other origins', () => {
    expect(() => sameOriginScriptUrl('https://evil.example/w.js', ORIGIN, BASE)).toThrow('monaco.worker.origin');
    expect(() => sameOriginScriptUrl('//evil.example/w.js', ORIGIN, BASE)).toThrow('monaco.worker.origin');
  });

  it('rejects data and blob script urls', () => {
    expect(() => sameOriginScriptUrl('data:text/javascript,alert(1)', ORIGIN, BASE)).toThrow('monaco.worker.origin');
    expect(() => sameOriginScriptUrl('blob:https://evil.example/1', ORIGIN, BASE)).toThrow('monaco.worker.origin');
  });
});
