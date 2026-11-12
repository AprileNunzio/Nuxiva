class CognitiveTriageController {
  constructor() {
    this.container = document.getElementById('cognitiveTriageContainer');
    this.currentLanguage = localStorage.getItem('nuxiva_lang') || 'it';
    this.translations = {};
    this.init();
  }

  async init() {
    await this.loadTranslations();
    this.bindEvents();
    await this.fetchStatus();
    window.addEventListener('languageChanged', (e) => {
      if (e.detail && e.detail.lang) {
        this.currentLanguage = e.detail.lang;
        this.applyTranslations();
      }
    });
  }

  async loadTranslations() {
    try {
      const res = await fetch('/features/cognitive_triage_agents/i18n.json');
      if (res.ok) {
        this.translations = await res.json();
        this.applyTranslations();
      }
    } catch (_) {}
  }

  applyTranslations() {
    const dict = this.translations[this.currentLanguage] || this.translations['it'];
    if (!dict || !this.container) return;

    this.container.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        el.textContent = dict[key];
      }
    });

    this.container.querySelectorAll('[data-i18n-attr]').forEach((el) => {
      const raw = el.getAttribute('data-i18n-attr');
      const parts = raw.split(':');
      if (parts.length === 2) {
        const attr = parts[0];
        const key = parts[1];
        if (dict[key]) {
          el.setAttribute(attr, dict[key]);
        }
      }
    });
  }

  bindEvents() {
    const btn = document.getElementById('triageEvaluateBtn');
    if (btn) {
      btn.addEventListener('click', () => this.handleEvaluate());
    }
  }

  async fetchStatus() {
    try {
      const res = await fetch('/api/v1/cognitive-triage/status');
      if (!res.ok) return;
      const data = await res.json();
      if (data.latest_evaluation) {
        this.renderEvaluation(data.latest_evaluation);
      }
    } catch (_) {}
  }

  async handleEvaluate() {
    const input = document.getElementById('triageTextInput');
    if (!input || !input.value.trim()) return;

    const payload = {
      user_id: 'active_session_user',
      raw_text: input.value.trim(),
      vocal_pitch_hz: 140.0,
      vocal_jitter: 0.02,
      hrv_ms: 45.0,
      heart_rate_bpm: 72.0,
      facial_valence: 0.0,
      gaze_stability: 0.8
    };

    try {
      const res = await fetch('/api/v1/cognitive-triage/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        this.renderEvaluation(data);
      }
    } catch (_) {}
  }

  renderEvaluation(data) {
    const dict = this.translations[this.currentLanguage] || this.translations['it'] || {};
    
    const psych = data.psychological_summary || data.psychological || {};
    const meth = data.methodological_summary || data.methodological || {};
    const psychiatry = data.psychiatric_summary || data.psychiatric || {};

    const psychStateEl = document.getElementById('psychStateVal');
    if (psychStateEl && psych.emotional_state) {
      psychStateEl.textContent = psych.emotional_state.toUpperCase();
    }
    const psychEmpathyEl = document.getElementById('psychEmpathyVal');
    if (psychEmpathyEl && psych.empathy_depth !== undefined) {
      psychEmpathyEl.textContent = Number(psych.empathy_depth).toFixed(2);
    }

    const methComplexityEl = document.getElementById('methComplexityVal');
    if (methComplexityEl && meth.task_complexity !== undefined) {
      methComplexityEl.textContent = Number(meth.task_complexity).toFixed(2);
    }
    const methOverloadEl = document.getElementById('methOverloadVal');
    if (methOverloadEl && meth.overload_index !== undefined) {
      methOverloadEl.textContent = Number(meth.overload_index).toFixed(2);
    }

    const riskBadge = document.getElementById('psychiatryRiskBadge');
    const interlockVal = document.getElementById('psychiatryInterlockVal');
    if (riskBadge && psychiatry.risk_level) {
      riskBadge.className = `risk-badge ${psychiatry.risk_level.toLowerCase()}`;
      const riskKey = `risk_${psychiatry.risk_level.toLowerCase()}`;
      riskBadge.textContent = dict[riskKey] || psychiatry.risk_level.toUpperCase();
    }
    if (interlockVal) {
      interlockVal.textContent = psychiatry.requires_interlock ? 'ATTIVO (BLOCCO)' : 'INATTIVO';
      interlockVal.style.color = psychiatry.requires_interlock ? '#ef4444' : '#34d399';
    }

    const modeTag = document.getElementById('consensusModeTag');
    if (modeTag && data.mode) {
      const modeMap = {
        transparent_coprocessor: 'mode_transparent',
        adaptive_tone: 'mode_adaptive',
        on_demand_coaching: 'mode_coaching',
        safety_interlock: 'mode_interlock'
      };
      const transKey = modeMap[data.mode] || 'mode_transparent';
      modeTag.textContent = dict[transKey] || data.mode;
    }

    const directiveEl = document.getElementById('metaDirectiveOutput');
    if (directiveEl && data.meta_prompt_directive) {
      directiveEl.textContent = data.meta_prompt_directive;
    }

    const rateEl = document.getElementById('speechRateOutput');
    if (rateEl && data.speech_rate_factor !== undefined) {
      rateEl.textContent = `${Number(data.speech_rate_factor).toFixed(2)}x`;
    }

    const emergencyCard = document.getElementById('emergencySafetyCard');
    if (emergencyCard) {
      if (psychiatry.requires_interlock || data.mode === 'safety_interlock') {
        emergencyCard.classList.remove('hidden');
        const msgEl = document.getElementById('emergencyProtocolMessage');
        if (msgEl && data.response_override) {
          msgEl.textContent = data.response_override;
        }
      } else {
        emergencyCard.classList.add('hidden');
      }
    }
  }
}

export function initCognitiveTriageAgents() {
  if (!window.cognitiveTriageController) {
    window.cognitiveTriageController = new CognitiveTriageController();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initCognitiveTriageAgents();
});
