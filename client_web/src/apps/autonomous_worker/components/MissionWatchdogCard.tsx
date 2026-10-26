import React, { useEffect, useState } from 'react';
import { fetchMissionAutomations, saveMissionWatchdog } from '../api';
import { MissionAutomation } from '../types';

interface Props {
  missionId: string;
  t: (key: string) => string;
}

export const MissionWatchdogCard: React.FC<Props> = ({ missionId, t }) => {
  const [automations, setAutomations] = useState<MissionAutomation[]>([]);
  const [intervalMin, setIntervalMin] = useState<number>(30);
  const [enabled, setEnabled] = useState<boolean>(true);
  const [telegram, setTelegram] = useState<boolean>(true);
  const [display, setDisplay] = useState<boolean>(true);
  const [email, setEmail] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [message, setMessage] = useState<string>('');

  const loadData = async () => {
    try {
      const list = await fetchMissionAutomations(missionId);
      setAutomations(list);
      const wd = list.find((a) =>
        a.actions?.some((act) => act.type === 'mission_watchdog')
      );
      if (wd) {
        setEnabled(wd.enabled);
        const trig = wd.triggers?.find((tr) => tr.type === 'interval');
        if (trig?.every) setIntervalMin(trig.every);
        const act = wd.actions?.find((ac) => ac.type === 'mission_watchdog');
        if (act?.channels) {
          setTelegram(act.channels.includes('telegram'));
          setDisplay(act.channels.includes('display'));
          setEmail(act.channels.includes('email'));
        }
      }
    } catch {
      setAutomations([]);
    }
  };

  useEffect(() => {
    loadData();
  }, [missionId]);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      const channels: string[] = [];
      if (telegram) channels.push('telegram');
      if (display) channels.push('display');
      if (email) channels.push('email');
      await saveMissionWatchdog(missionId, {
        interval_minutes: intervalMin,
        channels,
        enabled,
      });
      setMessage(t('watchdog_saved_ok'));
      await loadData();
    } catch {
      setMessage(t('watchdog_saved_err'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="nx-card nx-p-4 nx-mb-4 nx-border nx-border-slate-800 nx-rounded-xl nx-bg-slate-900/60">
      <div className="nx-flex nx-items-center nx-justify-between nx-mb-3">
        <div className="nx-flex nx-items-center nx-gap-2">
          <span className="nx-text-xl">🕵️</span>
          <h3 className="nx-text-base nx-font-semibold nx-text-slate-100">
            {t('watchdog_card_title')}
          </h3>
        </div>
        <span className="nx-text-xs nx-px-2 nx-py-0.5 nx-rounded nx-bg-cyan-950 nx-text-cyan-400 nx-border nx-border-cyan-800">
          {t('watchdog_ephemeral_badge')}
        </span>
      </div>

      <p className="nx-text-xs nx-text-slate-400 nx-mb-4">
        {t('watchdog_card_desc')}
      </p>

      <div className="nx-grid nx-grid-cols-1 md:nx-grid-cols-3 nx-gap-4 nx-mb-4">
        <div>
          <label className="nx-block nx-text-xs nx-text-slate-300 nx-mb-1">
            {t('watchdog_status_label')}
          </label>
          <button
            type="button"
            onClick={() => setEnabled(!enabled)}
            className={`nx-w-full nx-py-2 nx-px-3 nx-rounded nx-text-xs nx-font-medium nx-border ${
              enabled
                ? 'nx-bg-emerald-950/60 nx-text-emerald-300 nx-border-emerald-700'
                : 'nx-bg-slate-800 nx-text-slate-400 nx-border-slate-700'
            }`}
          >
            {enabled ? t('watchdog_enabled') : t('watchdog_disabled')}
          </button>
        </div>

        <div>
          <label className="nx-block nx-text-xs nx-text-slate-300 nx-mb-1">
            {t('watchdog_interval_label')}
          </label>
          <select
            value={intervalMin}
            onChange={(e) => setIntervalMin(Number(e.target.value))}
            className="nx-w-full nx-py-2 nx-px-3 nx-rounded nx-text-xs nx-bg-slate-800 nx-text-slate-200 nx-border nx-border-slate-700"
          >
            <option value={10}>10 min</option>
            <option value={15}>15 min</option>
            <option value={30}>30 min</option>
            <option value={60}>60 min (1h)</option>
            <option value={120}>120 min (2h)</option>
          </select>
        </div>

        <div>
          <label className="nx-block nx-text-xs nx-text-slate-300 nx-mb-1">
            {t('watchdog_channels_label')}
          </label>
          <div className="nx-flex nx-items-center nx-gap-2 nx-pt-1">
            <label className="nx-inline-flex nx-items-center nx-gap-1 nx-text-xs nx-text-slate-300 nx-cursor-pointer">
              <input
                type="checkbox"
                checked={telegram}
                onChange={(e) => setTelegram(e.target.checked)}
                className="nx-rounded nx-bg-slate-800"
              />
              Telegram
            </label>
            <label className="nx-inline-flex nx-items-center nx-gap-1 nx-text-xs nx-text-slate-300 nx-cursor-pointer">
              <input
                type="checkbox"
                checked={display}
                onChange={(e) => setDisplay(e.target.checked)}
                className="nx-rounded nx-bg-slate-800"
              />
              {t('watchdog_channel_display')}
            </label>
            <label className="nx-inline-flex nx-items-center nx-gap-1 nx-text-xs nx-text-slate-300 nx-cursor-pointer">
              <input
                type="checkbox"
                checked={email}
                onChange={(e) => setEmail(e.target.checked)}
                className="nx-rounded nx-bg-slate-800"
              />
              Email
            </label>
          </div>
        </div>
      </div>

      <div className="nx-flex nx-items-center nx-justify-between nx-pt-2 nx-border-t nx-border-slate-800/80">
        <span className="nx-text-xs nx-text-slate-400">
          {message ||
            `${t('watchdog_active_rules')}: ${automations.length}`}
        </span>
        <button
          type="button"
          disabled={saving}
          onClick={handleSave}
          className="nx-px-4 nx-py-1.5 nx-rounded nx-bg-cyan-600 hover:nx-bg-cyan-500 nx-text-white nx-text-xs nx-font-semibold disabled:nx-opacity-50"
        >
          {saving ? t('watchdog_saving') : t('watchdog_save_btn')}
        </button>
      </div>
    </div>
  );
};
