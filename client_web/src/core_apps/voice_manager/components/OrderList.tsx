import React from 'react';
import { ArrowDown, ArrowUp, Play, X } from 'lucide-react';
import { Btn, Pill, Row, List, Empty } from '../../shared/kit';
import { VoiceItem } from '../types';

interface Props {
  readonly order: VoiceItem[];
  readonly fallback: string;
  readonly busy: boolean;
  readonly playing: string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
  readonly onChange: (ids: string[]) => void;
  readonly onPlay: (id: string) => void;
}

export const OrderList: React.FC<Props> = ({ order, fallback, busy, playing, t, onChange, onPlay }) => {
  const ids = order.map((voice) => voice.id);
  const move = (index: number, delta: number) => {
    const next = [...ids];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };
  if (order.length === 0) return <Empty>{t('order_empty')}</Empty>;
  return (
    <List>
      {order.map((voice, index) => (
        <Row
          key={voice.id}
          actions={
            <>
              <Btn tone="slate" busy={playing === voice.id} onClick={() => onPlay(voice.id)}>
                <Play className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
              <Btn tone="slate" disabled={busy || index === 0} onClick={() => move(index, -1)} title={t('up')}>
                <ArrowUp className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
              <Btn tone="slate" disabled={busy || index === ids.length - 1} onClick={() => move(index, 1)} title={t('down')}>
                <ArrowDown className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
              <Btn tone="rose" disabled={busy} onClick={() => onChange(ids.filter((id) => id !== voice.id))} title={t('remove')}>
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </Btn>
            </>
          }
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="w-5 text-xs font-bold text-slate-500">{index + 1}</span>
            <strong className="truncate">{voice.name}</strong>
            <span className="text-xs text-slate-500">{voice.locale}</span>
            {voice.id === fallback ? <Pill tone="amber">{t('safety')}</Pill> : null}
            {!voice.installed ? <Pill tone="rose">{t('missing')}</Pill> : null}
          </div>
        </Row>
      ))}
    </List>
  );
};
