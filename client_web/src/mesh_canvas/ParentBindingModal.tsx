import React, { useState } from 'react';
import { MeshTopologyNode } from '../shared/types';
import { Network, Link2, X, Check, ArrowRight } from 'lucide-react';
import { useScopedI18n } from '../shared/i18n/useScopedI18n';

interface ParentBindingModalProps {
  satellite: MeshTopologyNode;
  availableParents: MeshTopologyNode[];
  onClose: () => void;
  onSaveBinding: (satelliteId: string, parentId: string, streamType: string) => Promise<void>;
}

export const ParentBindingModal: React.FC<ParentBindingModalProps> = ({
  satellite,
  availableParents,
  onClose,
  onSaveBinding,
}) => {
  const { t } = useScopedI18n('mesh_canvas');
  const [selectedParentId, setSelectedParentId] = useState<string>(
    satellite.parent_id || 'virtual-core'
  );
  const [streamType, setStreamType] = useState<string>('audio_pcm');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleSave = async () => {
    setIsSubmitting(true);
    try {
      await onSaveBinding(satellite.id, selectedParentId, streamType);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
      <div className="w-full max-w-lg bg-slate-950 border border-cyan-500/50 rounded-2xl p-6 shadow-[0_0_40px_rgba(0,240,255,0.3)] text-slate-100 flex flex-col gap-4 font-mono text-sm animate-in fade-in zoom-in-95">
        <div className="flex items-center justify-between border-b border-cyan-900/60 pb-3">
          <div className="flex items-center gap-2">
            <Link2 className="w-5 h-5 text-cyan-400" />
            <h2 className="font-bold text-base text-cyan-300">
              {t('bind_parent_title')}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="text-xs text-slate-300">
          Dispositivo: <strong className="text-cyan-400">{satellite.name}</strong> ({satellite.ip})
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-xs font-bold text-slate-300">
            {t('select_parent')}:
          </label>

          <div className="flex flex-col gap-2 max-h-60 overflow-y-auto pr-1">
            <button
              onClick={() => setSelectedParentId('virtual-core')}
              className={`p-3 rounded-xl border text-left flex items-center justify-between transition-all ${
                selectedParentId === 'virtual-core'
                  ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200'
                  : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="font-bold text-xs text-white">{t('auto_balance_core')}</div>
                <div className="text-[11px] text-slate-400">governor/pressure.py (Nodo Compute meno carico)</div>
              </div>
              {selectedParentId === 'virtual-core' && <Check className="w-4 h-4 text-cyan-400" />}
            </button>

            {availableParents
              .filter((p) => p.id !== satellite.id && p.type === 'compute')
              .map((parent) => (
                <button
                  key={parent.id}
                  onClick={() => setSelectedParentId(parent.id)}
                  className={`p-3 rounded-xl border text-left flex items-center justify-between transition-all ${
                    selectedParentId === parent.id
                      ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200'
                      : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="font-bold text-xs text-white">{parent.name} ({parent.ip})</div>
                    <div className="text-[11px] text-slate-400">
                      {parent.tier} — Direct P2P Streaming
                    </div>
                  </div>
                  {selectedParentId === parent.id && <Check className="w-4 h-4 text-cyan-400" />}
                </button>
              ))}
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <label className="text-xs font-bold text-slate-300">
            {t('stream_type_label')}:
          </label>
          <select
            value={streamType}
            onChange={(e) => setStreamType(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-cyan-400"
          >
            <option value="audio_pcm">Live Audio PCM (Microfono I2S/USB)</option>
            <option value="rtsp_video">Live Video RTSP (Camera 1080p WebRTC)</option>
            <option value="sensor_telemetry">Sensori Raw Telemetry</option>
          </select>
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-900">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl border border-slate-800 text-slate-400 hover:bg-slate-900 hover:text-white transition-all text-xs"
          >
            {t('cancel')}
          </button>
          <button
            onClick={handleSave}
            disabled={isSubmitting}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold transition-all text-xs flex items-center gap-2"
          >
            <span>{t('save_binding')}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
