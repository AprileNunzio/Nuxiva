import React, { useState } from 'react';
import {
  ActiveInferenceStepResult,
  HumanoidJoint,
  ImuBalanceState,
} from './types';
import { Activity, Compass, ShieldAlert, ShieldCheck, Sliders } from 'lucide-react';

interface HumanoidEmbodimentSectionProps {
  readonly joints: readonly HumanoidJoint[];
  readonly imu: ImuBalanceState;
  readonly totalCycles: number;
  readonly lastStep: ActiveInferenceStepResult | null;
  readonly busy: boolean;
  readonly onStepInference: (payload: {
    jointId: string;
    targetAngleRad: number;
    feedforwardTorqueNm: number;
    dtSec: number;
    measuredLoadKg: number;
  }) => Promise<void>;
  readonly t: (key: string) => string;
}

export const HumanoidEmbodimentSection: React.FC<HumanoidEmbodimentSectionProps> = ({
  joints,
  imu,
  totalCycles,
  lastStep,
  busy,
  onStepInference,
  t,
}) => {
  const [selectedJointId, setSelectedJointId] = useState(
    joints[0]?.id || 'hip_pitch_l'
  );
  const [targetAngle, setTargetAngle] = useState(0.35);
  const [torqueNm, setTorqueNm] = useState(24.0);
  const [loadKg, setLoadKg] = useState(2.5);

  const activeJoint =
    joints.find((j) => j.id === selectedJointId) || joints[0];

  const handleTriggerStep = () => {
    void onStepInference({
      jointId: selectedJointId,
      targetAngleRad: targetAngle,
      feedforwardTorqueNm: torqueNm,
      dtSec: 0.02,
      measuredLoadKg: loadKg,
    });
  };

  return (
    <div className="rounded-3xl border border-teal-200 bg-white p-5 sm:p-6 shadow-xs space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-teal-600 text-white">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-black text-slate-950">
              {t('embodied_humanoid_title')}
            </h3>
            <p className="text-xs text-slate-600 font-medium">
              {t('embodied_humanoid_subtitle')}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-teal-50 text-teal-950 border border-teal-200">
            <Activity className="w-3.5 h-3.5 text-teal-600" />
            {t('embodied_cycles_label')}: {totalCycles}
          </span>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-black bg-emerald-50 text-emerald-950 border border-emerald-200">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            ZMP: {imu.zmp_margin_m.toFixed(3)} m
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {joints.map((joint) => (
          <button
            key={joint.id}
            type="button"
            onClick={() => {
              setSelectedJointId(joint.id);
              setTargetAngle(Number(joint.angle_rad.toFixed(2)));
            }}
            className={`text-left p-3.5 rounded-2xl border transition ${
              selectedJointId === joint.id
                ? 'border-teal-600 bg-teal-50/70 shadow-2xs'
                : 'border-slate-200 hover:border-teal-300 bg-slate-50/50'
            }`}
          >
            <div className="text-xs font-black text-slate-900 truncate">{joint.id}</div>
            <div className="mt-2 text-[11px] font-bold text-teal-900">
              {joint.angle_rad.toFixed(3)} rad
            </div>
            <div className="mt-1 flex items-center justify-between text-[10px] font-semibold text-slate-500">
              <span>{joint.temperature_c.toFixed(1)}°C</span>
              <span>G: {joint.calibration_gain.toFixed(2)}</span>
            </div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7 space-y-4 rounded-2xl bg-slate-50 p-4 sm:p-5 border border-slate-200">
          <div className="flex items-center justify-between">
            <span className="text-xs font-black uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-teal-700" />
              {t('active_inference_motor_heading')}
            </span>
            {activeJoint && (
              <span className="text-[11px] font-bold text-slate-500">
                [{activeJoint.min_angle_rad} .. {activeJoint.max_angle_rad} rad]
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <label className="block space-y-1">
              <span className="text-[11px] font-bold text-slate-600">
                {t('target_angle_rad_label')}
              </span>
              <input
                type="number"
                step="0.05"
                value={targetAngle}
                onChange={(e) => setTargetAngle(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-black text-slate-900"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-[11px] font-bold text-slate-600">
                {t('feedforward_torque_label')}
              </span>
              <input
                type="number"
                step="2"
                value={torqueNm}
                onChange={(e) => setTorqueNm(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-black text-slate-900"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-[11px] font-bold text-slate-600">
                {t('payload_mass_kg_label')}
              </span>
              <input
                type="number"
                step="0.5"
                min="0"
                value={loadKg}
                onChange={(e) => setLoadKg(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-black text-slate-900"
              />
            </label>
          </div>

          <button
            type="button"
            disabled={busy}
            onClick={handleTriggerStep}
            className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-black text-xs sm:text-sm shadow-sm transition"
          >
            <Activity className="w-4 h-4" />
            {t('execute_active_inference_btn')}
          </button>
        </div>

        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
            <div className="text-xs font-black uppercase text-slate-700">
              {t('proprioceptive_imu_heading')}
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs font-bold">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                Roll: {imu.roll_deg.toFixed(2)}°
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                Pitch: {imu.pitch_deg.toFixed(2)}°
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                CoM: {imu.com_height_m.toFixed(2)} m
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
                {t('surface_friction_label')}: {imu.surface_friction_est.toFixed(2)}
              </div>
            </div>
          </div>

          {lastStep && (
            <div
              className={`rounded-2xl border-2 p-4 space-y-2 ${
                lastStep.reflex_engaged
                  ? 'border-amber-300 bg-amber-50/70'
                  : 'border-teal-200 bg-teal-50/50'
              }`}
            >
              <div className="flex items-center justify-between text-xs font-black">
                <span className="flex items-center gap-1.5 text-slate-900">
                  {lastStep.reflex_engaged ? (
                    <ShieldAlert className="w-4 h-4 text-amber-600" />
                  ) : (
                    <ShieldCheck className="w-4 h-4 text-teal-600" />
                  )}
                  {t(lastStep.status_key)}
                </span>
                <span className="text-teal-900">{lastStep.latency_ms} ms</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px] font-bold text-slate-700">
                <div>
                  {t('predicted_angle_label')}: {lastStep.predicted_angle_rad} rad
                </div>
                <div>
                  {t('actual_angle_label')}: {lastStep.actual_angle_rad} rad
                </div>
                <div>
                  {t('free_energy_surprise_label')}: {lastStep.free_energy_surprise}
                </div>
                <div>
                  {t('updated_gain_label')}: {lastStep.updated_calibration_gain}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
