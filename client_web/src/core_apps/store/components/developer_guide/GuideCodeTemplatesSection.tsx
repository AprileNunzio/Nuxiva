import React, { useState } from 'react';
import {
  Code,
  Check,
  Copy,
  Layers,
  Cpu,
  Bot,
  Wrench
} from 'lucide-react';
import type { DeveloperGuideProps, GuideModuleType, CodeFileType } from './types';
import { codeTemplates } from './templatesData';

export const GuideCodeTemplatesSection: React.FC<DeveloperGuideProps> = ({ t }) => {
  const [selectedModule, setSelectedModule] = useState<GuideModuleType>('app');
  const [selectedFile, setSelectedFile] = useState<CodeFileType>('view');
  const [copied, setCopied] = useState<boolean>(false);

  const copyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const currentSnippet = codeTemplates[selectedModule][selectedFile];

  return (
    <div className="space-y-4">
      <div className="rounded-3xl border border-[var(--md-sys-color-outline-variant)] bg-[var(--md-sys-color-surface-container)] p-6 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[var(--md-sys-color-outline-variant)] pb-4">
          <div className="flex items-center gap-2">
            <Code className="w-5 h-5 text-[var(--md-sys-color-primary)]" />
            <h3 className="text-sm font-bold text-[var(--md-sys-color-on-surface)]">
              {t('dev_subtab_code')}
            </h3>
          </div>

          <div className="flex items-center p-1 bg-[var(--md-sys-color-surface)] rounded-xl border border-[var(--md-sys-color-outline-variant)] text-xs font-semibold">
            <button
              type="button"
              onClick={() => setSelectedModule('app')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                selectedModule === 'app'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>{t('dev_tab_app')}</span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedModule('engine')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                selectedModule === 'engine'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>{t('dev_tab_engine')}</span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedModule('agent')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                selectedModule === 'agent'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              <span>{t('dev_tab_agent')}</span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedModule('plugin')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
                selectedModule === 'plugin'
                  ? 'bg-[var(--md-sys-color-primary)] text-white shadow-xs font-bold'
                  : 'text-[var(--md-sys-color-on-surface-variant)]'
              }`}
            >
              <Wrench className="w-3.5 h-3.5" />
              <span>{t('dev_tab_plugin')}</span>
            </button>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--md-sys-color-on-surface-variant)]">
            {t('dev_select_file')}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setSelectedFile('manifest')}
              className={`px-3 py-1 rounded-lg text-xs font-mono transition-all ${
                selectedFile === 'manifest'
                  ? 'bg-blue-500/20 text-blue-300 border border-blue-400/40 font-bold'
                  : 'bg-[var(--md-sys-color-surface)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]'
              }`}
            >
              manifest.json
            </button>

            <button
              type="button"
              onClick={() => setSelectedFile('view')}
              className={`px-3 py-1 rounded-lg text-xs font-mono transition-all ${
                selectedFile === 'view'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-400/40 font-bold'
                  : 'bg-[var(--md-sys-color-surface)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]'
              }`}
            >
              View.tsx
            </button>

            <button
              type="button"
              onClick={() => setSelectedFile('i18n')}
              className={`px-3 py-1 rounded-lg text-xs font-mono transition-all ${
                selectedFile === 'i18n'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-400/40 font-bold'
                  : 'bg-[var(--md-sys-color-surface)] text-[var(--md-sys-color-on-surface-variant)] border border-[var(--md-sys-color-outline-variant)]'
              }`}
            >
              language/it.json
            </button>
          </div>
        </div>

        <div className="rounded-2xl bg-black/70 border border-[var(--md-sys-color-outline-variant)] p-4 space-y-2">
          <div className="flex items-center justify-between pb-2 border-b border-white/10">
            <span className="font-mono text-xs text-white/70">
              {selectedFile === 'manifest' ? 'manifest.json' : selectedFile === 'view' ? 'View.tsx' : 'language/it.json'}
            </span>
            <button
              type="button"
              onClick={() => copyCode(currentSnippet)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-white/10 hover:bg-white/20 text-white transition-all shadow-xs"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-emerald-400">{t('dev_copied')}</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>{t('dev_copy_code')}</span>
                </>
              )}
            </button>
          </div>
          <pre className="font-mono text-[11px] text-blue-200 overflow-x-auto p-2 leading-relaxed max-h-96">
            <code>{currentSnippet}</code>
          </pre>
        </div>
      </div>
    </div>
  );
};
