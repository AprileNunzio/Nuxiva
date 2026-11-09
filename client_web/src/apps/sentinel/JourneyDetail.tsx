import { useState } from 'react';
import { useResource } from '../shared/useResource';
import type { SentinelJourney } from './types';
import type { SentinelModel } from './useSentinel';

type Translate = SentinelModel['t'];

function JourneyContent({ id, t }: { id: string; t: Translate }) {
  const { data, error } = useResource<SentinelJourney>(`/api/sentinel/journeys/${encodeURIComponent(id)}`, 0);
  if (error) return <p role="status">{t('journey_unavailable')}</p>;
  if (!data) return <p role="status">{t('loading')}</p>;
  return <div className="sentinel-journey">
    <h4>{t('journey_question')}</h4>
    <p>{data.question}</p>
    <h4>{t('journey_answer')}</h4>
    <p>{data.answer}</p>
    <h4>{t('journey_steps')}</h4>
    <ol>{data.steps.map(step => <li key={step.id}>
      <strong>{step.name}</strong> <small>{step.start}–{step.end} s · {t(`journey_state_${step.state}`)}</small>
      {step.detail && <p>{step.detail}</p>}
    </li>)}</ol>
  </div>;
}

export function JourneyDetail({ id, t }: { id: string; t: Translate }) {
  const [expanded, setExpanded] = useState(false);
  return <details onToggle={event => setExpanded(event.currentTarget.open)}>
    <summary>{t('journey_open')}</summary>
    {expanded && <JourneyContent id={id} t={t}/>}
  </details>;
}
