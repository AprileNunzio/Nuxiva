import React, { useEffect, useState } from 'react';
import { Fingerprint, Users } from 'lucide-react';
import { reportError } from '../../../shared/errors/errorBus';
import { FaceInsight, fetchFaceInsight } from '../data/faceApi';
import { usePeopleI18n } from '../scope';

interface FaceInsightCardProps {
  readonly slug: string;
  readonly tick: number;
}

export const FaceInsightCard: React.FC<FaceInsightCardProps> = ({ slug, tick }) => {
  const { t } = usePeopleI18n();
  const [insight, setInsight] = useState<FaceInsight | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchFaceInsight(slug, controller.signal)
      .then(setInsight)
      .catch((cause: unknown) => !controller.signal.aborted && reportError('people_face_insight_failed', cause));
    return () => controller.abort();
  }, [slug, tick]);

  if (!insight) {
    return null;
  }
  return (
    <section className="md-enter rounded-2xl bg-surface-container p-3 text-on-surface" aria-label={t('face_insight_title')}>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
        <span className="flex items-center gap-1.5 font-semibold">
          <Fingerprint className="h-4 w-4 text-primary" aria-hidden="true" />
          {t('face_insight_title')}
        </span>
        <span className="text-on-surface-variant">{t('face_samples', { count: insight.samples })}</span>
        {insight.threshold !== null && (
          <span className="font-mono text-on-surface-variant">{t('face_threshold', { value: insight.threshold.toFixed(2) })}</span>
        )}
        <span className="text-on-surface-variant">{t('face_marks_samples', { count: insight.marksSamples })}</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-on-surface-variant">{t('face_marks')}</span>
        {insight.marks.length === 0 ? (
          <span className="text-xs text-on-surface-variant">{t('face_marks_none')}</span>
        ) : (
          insight.marks.map((m) => (
            <span key={`${m.region}-${m.side}`} className="rounded-full bg-secondary-container px-2.5 py-0.5 text-[11px] font-semibold text-on-secondary-container">
              {t('face_mark', { region: t(`mark_region_${m.region}`), side: t(`mark_side_${m.side}`) })}
            </span>
          ))
        )}
      </div>
      {insight.similar.length > 0 && (
        <p className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-on-surface-variant">
          <Users className="h-3.5 w-3.5" aria-hidden="true" />
          {t('face_similar', { names: insight.similar.map((s) => `${s.name} ${Math.round(s.similarity * 100)}%`).join(', ') })}
        </p>
      )}
      {insight.shadowOf && <p className="mt-2 text-xs text-tertiary">{t('face_shadow', { name: insight.shadowOf })}</p>}
    </section>
  );
};
