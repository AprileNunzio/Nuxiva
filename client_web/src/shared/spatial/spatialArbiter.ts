import {
  ArbitrationResult,
  ContextManifest,
  NotificationEvent,
  SafeZone,
} from './contextManifest';

export function evaluateSpatialArbitration(
  event: NotificationEvent,
  manifest: ContextManifest
): ArbitrationResult {
  const lock = manifest.focusLockLevel;
  const preferred = manifest.assistantRequirement.preferredMorphology;
  const fallback = manifest.assistantRequirement.fallbackMorphology;
  const safeZones = manifest.assistantRequirement.allowedSafeZones;

  if (event.priority === 'P0_CRITICAL') {
    return {
      action: 'PREEMPTION_TOTAL',
      targetMorphology: 'CORE_HERO',
      suspendPrimaryStage: true,
      targetLayer: 'Z4_CriticalInterrupt',
      shouldDefer: false,
      reasonCode: 'p0_preemption',
    };
  }

  if (event.priority === 'P1_HIGH') {
    if (lock === 3) {
      return {
        action: 'VOICE_INTERJECT',
        targetMorphology: 'AMBIENT_STREAM',
        suspendPrimaryStage: false,
        targetLayer: 'Z3_Assistant',
        shouldDefer: false,
        reasonCode: 'p1_voice_interject',
      };
    }
    const zone: SafeZone = safeZones[0] || 'TOP_RIGHT';
    return {
      action: 'SMART_PIP',
      targetMorphology: preferred,
      assignedSafeZone: zone,
      suspendPrimaryStage: false,
      targetLayer: 'Z2_ContextualHud',
      shouldDefer: false,
      reasonCode: 'p1_smart_pip',
    };
  }

  if (event.priority === 'P2_NORMAL') {
    if (lock === 0) {
      return {
        action: 'SMART_PIP',
        targetMorphology: 'CORE_HERO',
        assignedSafeZone: 'CENTER',
        suspendPrimaryStage: false,
        targetLayer: 'Z2_ContextualHud',
        shouldDefer: false,
        reasonCode: 'p2_immediate',
      };
    }
    if (lock === 1) {
      const zone: SafeZone = safeZones[0] || 'BOTTOM_RIGHT';
      return {
        action: 'MICRO_BADGE',
        targetMorphology: preferred,
        assignedSafeZone: zone,
        suspendPrimaryStage: false,
        targetLayer: 'Z2_ContextualHud',
        shouldDefer: false,
        reasonCode: 'p2_micro_badge',
      };
    }
    return {
      action: 'DEFERRAL',
      targetMorphology: lock === 3 ? fallback : preferred,
      suspendPrimaryStage: false,
      targetLayer: 'Z1_PrimaryStage',
      shouldDefer: true,
      reasonCode: 'p2_deferred',
    };
  }

  return {
    action: 'SILENT_LOG',
    targetMorphology: preferred,
    suspendPrimaryStage: false,
    targetLayer: 'Z0_Ambient',
    shouldDefer: false,
    reasonCode: 'p3_silent',
  };
}
