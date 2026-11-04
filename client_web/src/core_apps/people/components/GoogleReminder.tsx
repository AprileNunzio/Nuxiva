import React, { useEffect, useState } from 'react';
import { BellRing } from 'lucide-react';
import { googleSetReminder } from '../data/connectorsApi';
import { chipClass, fieldClass, usePeopleI18n } from '../scope';

interface Props {
  readonly slug: string;
  readonly minutes: number;
  readonly busy: string | null;
  readonly run: (key: string, task: () => Promise<unknown>, code: string) => Promise<boolean>;
}

const MAX_MINUTES = 240;

export const GoogleReminder: React.FC<Props> = ({ slug, minutes, busy, run }) => {
  const { t } = usePeopleI18n();
  const [value, setValue] = useState(String(minutes));

  useEffect(() => setValue(String(minutes)), [minutes]);

  const parsed = Number(value);
  const valid = value.trim() !== '' && Number.isInteger(parsed) && parsed >= 0 && parsed <= MAX_MINUTES;

  return (
    <div className="flex flex-wrap items-end gap-2">
      <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-xs font-semibold text-slate-800">
        <span className="flex items-center gap-1.5">
          <BellRing className="h-3.5 w-3.5" aria-hidden="true" />
          {t('gg_remind')}
        </span>
        <input type="number" inputMode="numeric" min={0} max={MAX_MINUTES} value={value} onChange={(event) => setValue(event.target.value)} className={fieldClass} />
        <span className="text-[11px] font-normal text-slate-600">{t('gg_remind_hint')}</span>
      </label>
      <button
        type="button"
        disabled={busy !== null || !valid || parsed === minutes}
        onClick={() => void run('gg-remind', () => googleSetReminder(slug, parsed), 'people_connectors_failed')}
        className={`${chipClass} border-blue-300 bg-blue-50 px-3 py-2 text-blue-900`}
      >
        {t('gg_remind_save')}
      </button>
    </div>
  );
};
