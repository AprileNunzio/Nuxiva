import React from 'react';
import { Activity, Loader2, Mic, Square } from 'lucide-react';
import { Panel } from '../../shared/components/ModuleFrame';
import { SettingDraft } from '../../shared/hooks/useNodeSettings';
import { MicTestRequest } from '../data/micTestApi';
import { useMicMeter } from '../hooks/useMicMeter';
import { useMicTest } from '../hooks/useMicTest';
import { useMicI18n } from '../scope';
import { LevelMeter, ZONE_TEXT } from './LevelMeter';
import { MicTestResult } from './MicTestResult';

const TEST_SECONDS = 5;
const buttonBase =
  'flex items-center justify-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-semibold transition disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400';

function requestFrom(ear: SettingDraft, eq: SettingDraft): MicTestRequest {
  const target = Number(ear.NUXIVA_EAR_TARGET_RMS);
  return {
    seconds: TEST_SECONDS,
    ...(Number.isFinite(target) && target > 0 ? { target_rms: target } : {}),
    eq: {
      enabled: Boolean(eq.NUXIVA_EAR_EQ),
      highpass_hz: Number(eq.NUXIVA_EAR_EQ_HIGHPASS) || 0,
      low_db: Number(eq.NUXIVA_EAR_EQ_LOW) || 0,
      mid_db: Number(eq.NUXIVA_EAR_EQ_MID) || 0,
      high_db: Number(eq.NUXIVA_EAR_EQ_HIGH) || 0,
    },
  };
}

interface MicTestPanelProps {
  readonly ear: SettingDraft;
  readonly eq: SettingDraft;
}

export const MicTestPanel: React.FC<MicTestPanelProps> = ({ ear, eq }) => {
  const { t } = useMicI18n();
  const meter = useMicMeter();
  const test = useMicTest();
  const metering = meter.status === 'live' || meter.status === 'connecting';
  const recording = test.phase === 'recording';

  const startTest = () => {
    meter.stop();
    void test.record(requestFrom(ear, eq));
  };

  const zone = meter.level?.zone ?? 'silent';
  const rmsDb = meter.level?.rmsDb ?? -90;
  const error = test.error ?? meter.error;

  return (
    <Panel title={t('test_title')}>
      <div className="flex flex-col gap-3">
        <p className="text-xs text-slate-500">{t('test_intro')}</p>
        <LevelMeter
          rmsDb={rmsDb}
          peakHoldDb={meter.peakHoldDb}
          label={t('test_meter_label')}
          valueText={t('test_meter_value', { db: rmsDb.toFixed(1), zone: t(`test_zone_${zone}`) })}
        />
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <span className={`font-semibold ${ZONE_TEXT[zone]}`} aria-live="polite">
            {meter.status === 'live' ? t(`test_zone_${zone}`) : t(meter.status === 'connecting' ? 'test_meter_connecting' : 'test_meter_off')}
          </span>
          <span className="font-mono text-slate-400">{meter.level ? `${rmsDb.toFixed(1)} dBFS` : '—'}</span>
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <button
            type="button"
            onClick={metering ? meter.stop : meter.start}
            disabled={recording}
            aria-pressed={metering}
            className={`${buttonBase} ${metering ? 'border-rose-400/50 bg-rose-500/10 text-rose-700' : 'border-cyan-400/40 bg-cyan-400/10 text-cyan-800'}`}
          >
            {metering ? <Square className="h-4 w-4" aria-hidden="true" /> : <Activity className="h-4 w-4" aria-hidden="true" />}
            {t(metering ? 'test_meter_stop' : 'test_meter_start')}
          </button>
          <button
            type="button"
            onClick={startTest}
            disabled={recording}
            className={`${buttonBase} border-blue-300 bg-blue-50 text-blue-800 hover:bg-blue-100`}
          >
            {recording ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Mic className="h-4 w-4" aria-hidden="true" />}
            {recording ? t('test_recording', { seconds: test.remaining }) : t('test_record', { seconds: TEST_SECONDS })}
          </button>
        </div>
        {error && (
          <p role="alert" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {t(`test_error_${error}`)}
          </p>
        )}
        {test.report && test.rawUrl && test.processedUrl && (
          <MicTestResult report={test.report} rawUrl={test.rawUrl} processedUrl={test.processedUrl} />
        )}
      </div>
    </Panel>
  );
};
