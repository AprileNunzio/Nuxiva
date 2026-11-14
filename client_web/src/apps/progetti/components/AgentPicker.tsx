import React, { useState } from 'react';
import { Btn } from '../../shared/kit';
import { useResource } from '../../shared/useResource';

interface FleetItem {
  readonly id: string;
  readonly name: string;
  readonly state: string;
}

interface Props {
  readonly current: readonly string[];
  readonly busy: boolean;
  readonly t: (key: string) => string;
  readonly onSave: (agents: readonly string[]) => void;
}

const URL = '/api/fleet/agents?limit=50&state=active';

export const AgentPicker: React.FC<Props> = ({ current, busy, t, onSave }) => {
  const [chosen, setChosen] = useState<readonly string[]>(current);
  const fleet = useResource<{ readonly items: readonly FleetItem[] }>(URL);
  const items = fleet.data?.items ?? [];
  const toggle = (id: string) => setChosen((now) => (now.includes(id) ? now.filter((x) => x !== id) : [...now, id]));
  const same = chosen.length === current.length && chosen.every((id) => current.includes(id));

  return (
    <div className="flex flex-col gap-2">
      {items.length === 0 ? (
        <p className="text-xs text-on-surface-variant">{t('agents_empty')}</p>
      ) : (
        <ul className="flex flex-wrap gap-2">
          {items.map((agent) => (
            <li key={agent.id}>
              <button
                type="button"
                aria-pressed={chosen.includes(agent.id)}
                onClick={() => toggle(agent.id)}
                className={`md-state rounded-full px-3 py-1 text-xs font-medium ${chosen.includes(agent.id) ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface'}`}
              >
                {agent.name}
              </button>
            </li>
          ))}
        </ul>
      )}
      <div>
        <Btn busy={busy} disabled={same} onClick={() => onSave(chosen)}>
          {t('agents_save')}
        </Btn>
      </div>
    </div>
  );
};
