import React, { useState } from 'react';
import { Btn, Field, inputClass } from '../shared/kit';
import { CATEGORIES, EFFECTS } from './types';
import type { Category, Effect, Scenario } from './types';

const LANG = /^[a-z]{2,3}$/;

interface Props {
  scenario: Scenario;
  t: (key: string, values?: Record<string, string | number>) => string;
  onChange: (next: Scenario) => void;
  onRemove: () => void;
}

export function ScenarioEditor({ scenario, t, onChange, onRemove }: Props) {
  const [newLang, setNewLang] = useState('');
  const patch = (next: Partial<Scenario>) => onChange({ ...scenario, ...next });
  const setText = (code: string, value: string) => patch({ texts: { ...scenario.texts, [code]: value } });
  const dropText = (code: string) => {
    const { [code]: _removed, ...rest } = scenario.texts;
    patch({ texts: rest });
  };
  const toggleEffect = (effect: Effect) => {
    const has = scenario.expected.effects.includes(effect);
    patch({ expected: { ...scenario.expected, effects: has ? scenario.expected.effects.filter(item => item !== effect) : [...scenario.expected.effects, effect] } });
  };
  const addLang = () => {
    if (LANG.test(newLang) && !(newLang in scenario.texts)) {
      setText(newLang, '');
      setNewLang('');
    }
  };
  const adversarial = scenario.category === 'adversarial';

  return (
    <details className="rounded-2xl bg-surface-container px-3 py-2">
      <summary className="cursor-pointer text-sm font-semibold">{scenario.id || t('new_scenario')} <span className="font-normal text-on-surface-variant">· {t(`category_${scenario.category}`)} · {Object.keys(scenario.texts).join(', ')}</span></summary>
      <div className="mt-3 grid gap-3 cq-lg:grid-cols-2">
        <Field label={t('scenario_id')}><input className={inputClass} value={scenario.id} maxLength={64} onChange={event => patch({ id: event.target.value.toLowerCase() })} /></Field>
        <Field label={t('category')}>
          <select className={inputClass} value={scenario.category} onChange={event => patch({ category: event.target.value as Category, external_content: event.target.value === 'adversarial' ? scenario.external_content ?? '' : null })}>
            {CATEGORIES.map(item => <option key={item} value={item}>{t(`category_${item}`)}</option>)}
          </select>
        </Field>
        <Field label={t('expected_intent')}><input className={inputClass} value={scenario.expected.intent} maxLength={64} onChange={event => patch({ expected: { ...scenario.expected, intent: event.target.value.toLowerCase() } })} /></Field>
        <fieldset className="flex flex-wrap gap-3 text-xs">
          <legend className="mb-1 font-semibold text-on-surface-variant">{t('expected_effects')}</legend>
          {EFFECTS.map(effect => (
            <label key={effect} className="flex items-center gap-1"><input type="checkbox" checked={scenario.expected.effects.includes(effect)} onChange={() => toggleEffect(effect)} />{t(`effect_${effect}`)}</label>
          ))}
        </fieldset>
        {adversarial && (
          <div className="cq-lg:col-span-2">
            <Field label={t('external_content')}>
              <textarea className={inputClass} rows={3} maxLength={8192} value={scenario.external_content ?? ''} onChange={event => patch({ external_content: event.target.value })} />
            </Field>
          </div>
        )}
        <div className="flex flex-col gap-2 cq-lg:col-span-2">
          <span className="text-xs font-semibold text-on-surface-variant">{t('texts')}</span>
          {Object.entries(scenario.texts).map(([code, text]) => (
            <div key={code} className="flex items-start gap-2">
              <span className="mt-2 w-8 shrink-0 font-mono text-xs">{code}</span>
              <textarea aria-label={code} className={`${inputClass} min-w-0 flex-1`} rows={2} maxLength={2048} value={text} onChange={event => setText(code, event.target.value)} />
              <span className="shrink-0"><Btn tone="rose" onClick={() => dropText(code)}>{t('remove')}</Btn></span>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <input aria-label={t('language_code')} className={`${inputClass} max-w-[6rem]`} placeholder="it" maxLength={3} value={newLang} onChange={event => setNewLang(event.target.value.toLowerCase())} />
            <span className="shrink-0"><Btn onClick={addLang} disabled={!LANG.test(newLang) || newLang in scenario.texts}>{t('add_language')}</Btn></span>
          </div>
        </div>
        <div className="cq-lg:col-span-2"><Btn tone="rose" onClick={onRemove}>{t('remove_scenario')}</Btn></div>
      </div>
    </details>
  );
}
