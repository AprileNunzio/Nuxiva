import React, { useState } from 'react';
import { useStudioI18n } from '../scope';
import type { Artifact } from '../types';
import { saveSmbFile } from '../api';

interface ArtifactCanvasProps {
  artifact: Artifact | null;
  onClose: () => void;
  defaultSmbFolder?: string;
}

export const ArtifactCanvas: React.FC<ArtifactCanvasProps> = ({
  artifact,
  onClose,
  defaultSmbFolder = '04 Codice',
}) => {
  const { t } = useStudioI18n();
  const [activeTab, setActiveTab] = useState<'code' | 'preview'>('preview');
  const [copied, setCopied] = useState(false);
  const [savingSmb, setSavingSmb] = useState(false);
  const [savedUnc, setSavedUnc] = useState<string | null>(null);

  if (!artifact) return null;

  const canPreview = artifact.kind === 'html' || artifact.kind === 'svg' || artifact.kind === 'markdown';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const handleSaveSmb = async () => {
    setSavingSmb(true);
    setSavedUnc(null);
    try {
      const res = await saveSmbFile({
        folder: defaultSmbFolder,
        filename: artifact.title,
        content: artifact.content,
      });
      setSavedUnc(res.unc_path);
      setTimeout(() => setSavedUnc(null), 4000);
    } catch (err) {
      console.error(err);
    } finally {
      setSavingSmb(false);
    }
  };

  return (
    <aside className="w-full md:w-[480px] lg:w-[560px] h-full flex flex-col bg-slate-950 border-l border-slate-800/80 backdrop-blur-md shadow-2xl z-20">
      <div className="px-4 py-3 border-b border-slate-800/80 bg-slate-900/80 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-cyan-400 font-bold">📄</span>
          <span className="font-semibold text-xs text-slate-100 truncate">
            {artifact.title}
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-cyan-400 font-mono">
            {artifact.language}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {canPreview && (
            <div className="flex items-center bg-slate-800/90 p-0.5 rounded-lg border border-slate-700 text-[11px]">
              <button
                type="button"
                onClick={() => setActiveTab('preview')}
                className={`px-2 py-0.5 rounded-md font-medium transition-all ${
                  activeTab === 'preview'
                    ? 'bg-cyan-500/20 text-cyan-300'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t('preview')}
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('code')}
                className={`px-2 py-0.5 rounded-md font-medium transition-all ${
                  activeTab === 'code'
                    ? 'bg-cyan-500/20 text-cyan-300'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {t('code_view')}
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={handleCopy}
            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200 transition-colors"
          >
            {copied ? t('copied') : t('copy_code')}
          </button>

          <button
            type="button"
            disabled={savingSmb}
            onClick={handleSaveSmb}
            className="px-2.5 py-1 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 border border-cyan-500/40 text-xs text-cyan-300 font-medium transition-colors"
          >
            {savingSmb ? t('saving') : `🗄️ ${t('save_to_smb')}`}
          </button>

          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors ml-1"
            title={t('close')}
          >
            ✕
          </button>
        </div>
      </div>

      {savedUnc && (
        <div className="px-4 py-2 bg-emerald-950/40 border-b border-emerald-800/40 text-xs text-emerald-300 flex items-center justify-between">
          <span>✓ {t('saved_smb_success')}</span>
          <span className="font-mono text-[10px] text-emerald-400/80 truncate max-w-[200px]">
            {savedUnc}
          </span>
        </div>
      )}

      <div className="flex-1 overflow-auto bg-slate-950/60 p-4">
        {canPreview && activeTab === 'preview' ? (
          artifact.kind === 'html' ? (
            <iframe
              title={artifact.title}
              sandbox="allow-scripts"
              srcDoc={artifact.content}
              className="w-full h-full min-h-[400px] rounded-xl border border-slate-800 bg-white"
            />
          ) : artifact.kind === 'svg' ? (
            <div
              className="w-full h-full min-h-[400px] flex items-center justify-center p-4 bg-slate-900 rounded-xl border border-slate-800"
              dangerouslySetInnerHTML={{ __html: artifact.content }}
            />
          ) : (
            <div className="whitespace-pre-wrap font-sans text-xs text-slate-200 leading-relaxed">
              {artifact.content}
            </div>
          )
        ) : (
          <pre className="font-mono text-xs text-slate-200 leading-relaxed overflow-x-auto whitespace-pre p-2">
            <code>{artifact.content}</code>
          </pre>
        )}
      </div>
    </aside>
  );
};
