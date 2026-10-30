import { afterEach, describe, expect, it, vi } from 'vitest';
import { parseOverview, saveRoleChain } from './brainApi';
import { providerPath } from './parse';
import { validateChange, validateServer } from './providersApi';
import { parseUsage, validateBudgets } from './usageApi';
import { saveFunction } from './functionsApi';

afterEach(() => vi.unstubAllGlobals());

describe('overview parsing', () => {
  it('drops malformed roles and refs', () => {
    const overview = parseOverview({
      routing: 'weird',
      roles: [
        { id: 'chat', custom: true, entries: [{ ref: 'qwen2.5:7b', origin: 'local' }, { ref: '<img>' }], scope: 'home', strategy: 'bad', active: { ref: 'qwen2.5:7b' } },
        { id: 'Bad Id' },
      ],
      catalog: [{ name: 'x', fit: { level: 'nope' }, license: { warning: 'eu' } }],
      hardware: { ram_gb: 16, vram_gb: 'x' },
    });
    expect(overview.routing).toBe('auto');
    expect(overview.roles).toHaveLength(1);
    expect(overview.roles[0].entries.map((e) => e.ref)).toEqual(['qwen2.5:7b']);
    expect(overview.roles[0].scope).toBe('home');
    expect(overview.roles[0].strategy).toBe('order');
    expect(overview.catalog[0].fit.level).toBe('ok');
    expect(overview.catalog[0].restricted).toBe(true);
    expect(overview.hardware).toEqual({ ramGb: 16, vramGb: 0, gpu: null });
  });

  it('refuses invalid chains before any request', async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    await expect(saveRoleChain('chat', ['ok', 'bad ref'])).rejects.toThrow(RangeError);
    await expect(saveRoleChain('../x', [])).rejects.toThrow(RangeError);
    await expect(saveFunction('a:b', 'first', ['x'])).rejects.toThrow(RangeError);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('sends a validated chain as JSON with the CSRF header', async () => {
    const fetchSpy = vi.fn(async () => new Response(JSON.stringify({ roles: [] }), { status: 200 }));
    vi.stubGlobal('fetch', fetchSpy);
    await saveRoleChain('deep', ['cloud:anthropic/claude-haiku-5-5']);
    const [url, init] = fetchSpy.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('/api/brains');
    expect(init.method).toBe('PUT');
    expect(JSON.parse(String(init.body))).toEqual({ deep: ['cloud:anthropic/claude-haiku-5-5'] });
    expect((init.headers as Record<string, string>)['X-Nuxiva-Request']).toBe('1');
  });
});

describe('provider validation', () => {
  it('accepts only safe keys and urls', () => {
    expect(() => validateChange({ key: 'short' })).toThrow(RangeError);
    expect(() => validateChange({ key: 'sk-valid-key-123' })).not.toThrow();
    expect(() => validateChange({ base_url: 'javascript:alert(1)' })).toThrow(RangeError);
    expect(() => validateChange({ base_url: 'https://api.example.com/v1' })).not.toThrow();
  });

  it('sanitizes new servers', () => {
    expect(() => validateServer({ name: '<b>', flavor: 'openai', url: 'https://x.io/v1', key: '' })).toThrow(RangeError);
    expect(validateServer({ name: ' Lab ', flavor: 'ollama', url: ' http://10.0.0.2:11434 ', key: '' })).toEqual({
      name: 'Lab',
      flavor: 'ollama',
      url: 'http://10.0.0.2:11434',
      key: '',
    });
  });

  it('encodes provider ids for paths', () => {
    expect(providerPath('openai')).toBe('openai');
    expect(() => providerPath('../etc')).toThrow(RangeError);
  });
});

describe('usage parsing', () => {
  it('keeps only valid budgets and rows', () => {
    const usage = parseUsage({
      month: '2026-10',
      today: 10,
      cloud: 40,
      budgets: { global: 100, providers: { openai: 50, 'bad id': 5, mistral: -1 } },
      providers: [{ id: 'openai', tokens_in: 30, tokens_out: 10, calls: 2, budget: 50 }, { nope: true }],
      days: [{ date: '2026-10-30', tokens: 40 }, { tokens: 1 }],
    });
    expect(usage.globalBudget).toBe(100);
    expect(usage.providerBudgets).toEqual({ openai: 50 });
    expect(usage.providers).toHaveLength(1);
    expect(usage.days).toHaveLength(1);
  });

  it('validates budgets before sending', () => {
    expect(() => validateBudgets({ global: 1.5, providers: {} })).toThrow(RangeError);
    expect(() => validateBudgets({ global: null, providers: { 'Bad!': 5 } })).toThrow(RangeError);
    expect(validateBudgets({ global: 1000, providers: { openai: null } })).toEqual({ global: 1000, providers: { openai: null } });
  });
});
