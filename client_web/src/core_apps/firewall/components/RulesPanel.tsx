import React, { FormEvent, useState } from 'react';
import { ListChecks, Trash2 } from 'lucide-react';
import { Btn, Empty, Field, List, Panel, Pill, Row, Toggle, inputClass } from '../../shared/kit';
import { addRule, deleteRule, toggleRule } from '../api';
import { FirewallRule } from '../types';

const ACTIONS = ['accept', 'drop', 'reject', 'limit'] as const;
const DIRECTIONS = ['input', 'output', 'forward'] as const;
const PROTOCOLS = ['any', 'tcp', 'udp', 'icmp'] as const;
const TONE: Record<string, 'emerald' | 'rose' | 'amber' | 'cyan'> = { accept: 'emerald', drop: 'rose', reject: 'rose', limit: 'amber' };
const PORT = /^\d{1,5}(-\d{1,5})?$/;

interface RulesPanelProps {
  readonly rules: readonly FirewallRule[];
  readonly busy: boolean;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly run: <R>(task: () => Promise<R>, code?: string) => Promise<R | null>;
}

export const RulesPanel: React.FC<RulesPanelProps> = ({ rules, busy, t, run }) => {
  const [action, setAction] = useState<string>('drop');
  const [direction, setDirection] = useState<string>('input');
  const [protocol, setProtocol] = useState<string>('tcp');
  const [ports, setPorts] = useState('');
  const [source, setSource] = useState('');
  const [comment, setComment] = useState('');

  const portList = ports.split(/[\s,]+/).filter(Boolean);
  const valid = portList.every((port) => PORT.test(port)) && (portList.length === 0 || protocol === 'tcp' || protocol === 'udp') && action !== 'limit';

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!valid) {
      return;
    }
    const done = await run(
      () => addRule({ action, direction, protocol, ports: portList, sources: source.trim() ? [source.trim()] : [], comment: comment.trim() }),
      'firewall_rule_failed',
    );
    if (done !== null) {
      setPorts('');
      setSource('');
      setComment('');
    }
  };

  return (
    <Panel title={t('rules_title')} icon={<ListChecks className="h-4 w-4 text-cyan-300" aria-hidden="true" />}>
      {rules.length === 0 ? (
        <Empty>{t('rules_empty')}</Empty>
      ) : (
        <List>
          {rules.map((rule) => (
            <Row
              key={rule.id}
              actions={
                <>
                  <Toggle checked={rule.enabled} disabled={busy} label={t('rule_enabled')} onChange={(value) => void run(() => toggleRule(rule, value), 'firewall_rule_failed')} />
                  <Btn tone="rose" busy={busy} onClick={() => void run(() => deleteRule(rule.id), 'firewall_rule_failed')} title={t('delete')}>
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </Btn>
                </>
              }
            >
              <div className="flex flex-wrap items-center gap-2">
                <Pill tone={TONE[rule.action] ?? 'cyan'}>{rule.action}</Pill>
                <Pill>{rule.direction}</Pill>
                <Pill>{rule.protocol}</Pill>
                {rule.ports.length ? <span className="font-mono text-xs">:{rule.ports.join(',')}</span> : null}
              </div>
              <p className="mt-1 truncate text-xs text-slate-400">
                {rule.sources.length ? rule.sources.join(', ') : t('any_source')} {rule.comment ? `· ${rule.comment}` : ''}
              </p>
            </Row>
          ))}
        </List>
      )}
      <form onSubmit={submit} className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-800 pt-4 sm:grid-cols-3">
        <Field label={t('field_action')}>
          <select className={inputClass} value={action} onChange={(event) => setAction(event.target.value)}>
            {ACTIONS.filter((item) => item !== 'limit').map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t('field_direction')}>
          <select className={inputClass} value={direction} onChange={(event) => setDirection(event.target.value)}>
            {DIRECTIONS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t('field_protocol')}>
          <select className={inputClass} value={protocol} onChange={(event) => setProtocol(event.target.value)}>
            {PROTOCOLS.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t('field_ports')}>
          <input className={inputClass} value={ports} onChange={(event) => setPorts(event.target.value)} placeholder="22, 8000-8100" />
        </Field>
        <Field label={t('field_source')}>
          <input className={inputClass} value={source} onChange={(event) => setSource(event.target.value)} placeholder="192.168.1.0/24" />
        </Field>
        <Field label={t('field_comment')}>
          <input className={inputClass} value={comment} maxLength={80} onChange={(event) => setComment(event.target.value)} />
        </Field>
        <div className="col-span-2 sm:col-span-3">
          <Btn type="submit" busy={busy} disabled={!valid}>
            {t('add_rule')}
          </Btn>
        </div>
      </form>
    </Panel>
  );
};
