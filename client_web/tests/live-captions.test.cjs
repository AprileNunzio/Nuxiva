const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const DEFAULTS = {
  enabled: true,
  scope: 'all',
  speaker: true,
  size: 'medium',
  hold: 6,
  position: 'bottom'
};

const SIZES = ['small', 'medium', 'large'];
const POSITIONS = ['bottom', 'center'];

function sanitizeConfig(raw) {
  const c = raw && typeof raw === 'object' ? raw : {};
  const hold = Number(c.hold);
  const size = SIZES.includes(c.size) ? c.size : DEFAULTS.size;
  const position = POSITIONS.includes(c.position) ? c.position : DEFAULTS.position;
  return {
    enabled: c.enabled !== false,
    scope: c.scope === 'addressed' ? 'addressed' : 'all',
    speaker: c.speaker !== false,
    size,
    hold: Number.isFinite(hold) ? Math.max(2, Math.min(30, hold)) : DEFAULTS.hold,
    position
  };
}

function computeSpeakerHue(slug) {
  let h = 0;
  for (let i = 0; i < slug.length; i++) {
    h = (h * 31 + slug.charCodeAt(i)) % 360;
  }
  return h;
}

class CaptionsEngine {
  constructor(config = DEFAULTS, speakers = {}) {
    this.config = sanitizeConfig(config);
    this.speakers = speakers;
    this.lines = new Map();
    this.maxLines = 3;
  }

  handleEvent(ev) {
    if (!ev || typeof ev !== 'object') return;
    if (ev.type === 'caption_drop' && typeof ev.utt === 'string') {
      this.lines.delete(ev.utt);
      return;
    }

    const isAddressed = ev.type === 'transcript' || Boolean(ev.addressed);
    if (!this.config.enabled) return;
    if (this.config.scope === 'addressed' && !isAddressed) return;

    if (ev.type === 'partial') {
      if (typeof ev.utt !== 'string' || typeof ev.text !== 'string') return;
      const rawWords = ev.text.split(/\s+/).filter(Boolean);
      const stableCount = Number(ev.stable) || 0;
      const speakerSlug = typeof ev.speaker === 'string' ? ev.speaker : '';
      const speakerName = speakerSlug ? (this.speakers[speakerSlug] || speakerSlug) : '';

      const words = rawWords.map((w, idx) => ({
        text: w,
        stable: idx < stableCount
      }));

      if (!this.lines.has(ev.utt) && this.lines.size >= this.maxLines) {
        const oldest = this.lines.keys().next().value;
        if (oldest) this.lines.delete(oldest);
      }

      this.lines.set(ev.utt, {
        utt: ev.utt,
        speaker: speakerSlug,
        speakerName,
        speakerHue: computeSpeakerHue(speakerSlug),
        words,
        addressed: isAddressed,
        final: false,
        done: false
      });
      return;
    }

    if (ev.type === 'heard' || ev.type === 'transcript') {
      if (typeof ev.text !== 'string' || !ev.text.trim()) {
        if (ev.utt) this.lines.delete(ev.utt);
        return;
      }
      const utt = typeof ev.utt === 'string' && ev.utt ? ev.utt : `utt-${Date.now()}`;
      const rawWords = ev.text.split(/\s+/).filter(Boolean);
      const speakerSlug = typeof ev.speaker === 'string' ? ev.speaker : '';
      const speakerName = speakerSlug ? (this.speakers[speakerSlug] || speakerSlug) : '';

      const words = rawWords.map(w => ({ text: w, stable: true }));

      if (!this.lines.has(utt) && this.lines.size >= this.maxLines) {
        const oldest = this.lines.keys().next().value;
        if (oldest) this.lines.delete(oldest);
      }

      this.lines.set(utt, {
        utt,
        speaker: speakerSlug,
        speakerName,
        speakerHue: computeSpeakerHue(speakerSlug),
        words,
        addressed: isAddressed,
        final: true,
        done: true
      });
    }
  }

  getLines() {
    return Array.from(this.lines.values());
  }
}

test('sanitizeConfig sanitizes raw configurations with safe bounds', () => {
  const empty = sanitizeConfig(null);
  assert.equal(empty.enabled, true);
  assert.equal(empty.scope, 'all');
  assert.equal(empty.speaker, true);
  assert.equal(empty.size, 'medium');
  assert.equal(empty.hold, 6);
  assert.equal(empty.position, 'bottom');

  const custom = sanitizeConfig({
    enabled: false,
    scope: 'addressed',
    speaker: false,
    size: 'large',
    hold: 50,
    position: 'center'
  });
  assert.equal(custom.enabled, false);
  assert.equal(custom.scope, 'addressed');
  assert.equal(custom.speaker, false);
  assert.equal(custom.size, 'large');
  assert.equal(custom.hold, 30);
  assert.equal(custom.position, 'center');

  const lowHold = sanitizeConfig({ hold: 0 });
  assert.equal(lowHold.hold, 2);
});

test('computeSpeakerHue generates deterministic hue in 0-359 range', () => {
  const h1 = computeSpeakerHue('marco');
  const h2 = computeSpeakerHue('marco');
  const h3 = computeSpeakerHue('anna');

  assert.equal(h1, h2);
  assert.ok(h1 >= 0 && h1 < 360);
  assert.ok(h3 >= 0 && h3 < 360);
  assert.notEqual(h1, h3);
});

test('CaptionsEngine processes partial, stable words and transcript events', () => {
  const engine = new CaptionsEngine(DEFAULTS, { marco: 'Marco Fazzina' });

  engine.handleEvent({
    type: 'partial',
    utt: 'u1',
    text: 'accendi la luce del',
    stable: 2,
    speaker: 'marco',
    addressed: true
  });

  let lines = engine.getLines();
  assert.equal(lines.length, 1);
  assert.equal(lines[0].utt, 'u1');
  assert.equal(lines[0].speakerName, 'Marco Fazzina');
  assert.equal(lines[0].words.length, 4);
  assert.equal(lines[0].words[0].stable, true);
  assert.equal(lines[0].words[1].stable, true);
  assert.equal(lines[0].words[2].stable, false);
  assert.equal(lines[0].words[3].stable, false);
  assert.equal(lines[0].final, false);

  engine.handleEvent({
    type: 'transcript',
    utt: 'u1',
    text: 'accendi la luce del salotto',
    speaker: 'marco'
  });

  lines = engine.getLines();
  assert.equal(lines.length, 1);
  assert.equal(lines[0].words.length, 5);
  assert.ok(lines[0].words.every(w => w.stable));
  assert.equal(lines[0].final, true);
  assert.equal(lines[0].done, true);
  assert.equal(lines[0].addressed, true);
});

test('CaptionsEngine filters out unaddressed speech when scope is addressed', () => {
  const engine = new CaptionsEngine({ scope: 'addressed' });

  engine.handleEvent({
    type: 'heard',
    utt: 'u_bg',
    text: 'buongiorno a tutti',
    speaker: null
  });

  assert.equal(engine.getLines().length, 0);

  engine.handleEvent({
    type: 'transcript',
    utt: 'u_cmd',
    text: 'nuxiva che ore sono',
    speaker: 'marco'
  });

  assert.equal(engine.getLines().length, 1);
});

test('CaptionsEngine bounds active lines to maxLines and drops on caption_drop', () => {
  const engine = new CaptionsEngine();

  engine.handleEvent({ type: 'partial', utt: 'u1', text: 'uno', stable: 1 });
  engine.handleEvent({ type: 'partial', utt: 'u2', text: 'due', stable: 1 });
  engine.handleEvent({ type: 'partial', utt: 'u3', text: 'tre', stable: 1 });
  assert.equal(engine.getLines().length, 3);

  engine.handleEvent({ type: 'partial', utt: 'u4', text: 'quattro', stable: 1 });
  const lines = engine.getLines();
  assert.equal(lines.length, 3);
  assert.equal(lines.some(l => l.utt === 'u1'), false);
  assert.equal(lines.some(l => l.utt === 'u4'), true);

  engine.handleEvent({ type: 'caption_drop', utt: 'u2' });
  assert.equal(engine.getLines().length, 2);
  assert.equal(engine.getLines().some(l => l.utt === 'u2'), false);
});

test('Colocated live_captions language dictionaries are present and valid', () => {
  const langDir = path.resolve(__dirname, '../src/features/live_captions/language');
  const locales = ['it', 'en', 'es', 'fr'];

  for (const loc of locales) {
    const file = path.join(langDir, `${loc}.json`);
    assert.ok(fs.existsSync(file), `Manca file dizionario: ${file}`);
    const content = JSON.parse(fs.readFileSync(file, 'utf8'));
    assert.equal(content.meta.locale, loc);
    assert.ok(content.dictionary.cap_unknown, `Manca cap_unknown in ${loc}`);
    assert.ok(content.dictionary.captions_title, `Manca captions_title in ${loc}`);
  }
});
