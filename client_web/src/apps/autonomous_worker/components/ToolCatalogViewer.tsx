import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  Cpu,
  Filter,
  Hammer,
  Layers,
  Plus,
  RefreshCw,
  Search,
  Sliders,
  Terminal,
  Wrench,
  Zap,
} from 'lucide-react';
import { fetchToolCatalog, scanToolsNow, studyAndForgeTool } from '../api';
import { inputFieldClass, primaryBtnClass, secondaryBtnClass, useAutonomousI18n } from '../scope';
import { ToolCatalogResponse, ToolMetadata } from '../types';

export const ToolCatalogViewer: React.FC = () => {
  const { t } = useAutonomousI18n();
  const [catalog, setCatalog] = useState<ToolCatalogResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [showForgeModal, setShowForgeModal] = useState(false);
  const [forgeName, setForgeName] = useState('');
  const [forgeDesc, setForgeDesc] = useState('');
  const [forgeStepsRaw, setForgeStepsRaw] = useState('[{"tool": "list_dir", "args": {"path": "."}}]');
  const [forging, setForging] = useState(false);
  const [forgeError, setForgeError] = useState('');

  useEffect(() => {
    void loadCatalog();
  }, []);

  async function loadCatalog() {
    setLoading(true);
    try {
      const data = await fetchToolCatalog();
      setCatalog(data);
    } catch {
    } finally {
      setLoading(false);
    }
  }

  async function handleScan() {
    setScanning(true);
    try {
      const data = await scanToolsNow();
      setCatalog(data);
    } catch {
    } finally {
      setScanning(false);
    }
  }

  async function handleForgeSubmit(e: React.FormEvent) {
    e.preventDefault();
    setForgeError('');
    let parsedSteps: Array<{ tool: string; args: Record<string, any> }> = [];
    try {
      parsedSteps = JSON.parse(forgeStepsRaw);
      if (!Array.isArray(parsedSteps) || parsedSteps.length === 0) {
        setForgeError('I passi devono essere un array JSON non vuoto');
        return;
      }
    } catch {
      setForgeError('Sintassi JSON dei passi non valida');
      return;
    }

    setForging(true);
    try {
      await studyAndForgeTool({
        name: forgeName.trim().toLowerCase(),
        description: forgeDesc.trim(),
        params: {},
        steps: parsedSteps,
      });
      setShowForgeModal(false);
      setForgeName('');
      setForgeDesc('');
      await loadCatalog();
    } catch (err: any) {
      setForgeError(err?.message || 'Errore forgiatura');
    } finally {
      setForging(false);
    }
  }

  const tools = catalog?.tools || [];
  const filteredTools = tools.filter((tool) => {
    if (selectedCategory !== 'all' && tool.category !== selectedCategory) {
      return false;
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchName = tool.name.toLowerCase().includes(q);
      const matchDesc = tool.description.toLowerCase().includes(q);
      const matchCat = tool.category.toLowerCase().includes(q);
      return matchName || matchDesc || matchCat;
    }
    return true;
  });

  const categories = Object.keys(catalog?.categories || {});

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4 backdrop-blur-md">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-black text-white">
            <Wrench className="h-6 w-6 text-emerald-400" />
            {t('tools_title')}
          </h2>
          <p className="mt-1 text-xs text-slate-400">{t('tools_desc')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setShowForgeModal(true)}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600/30 px-3 py-1.5 text-xs font-semibold text-emerald-300 border border-emerald-500/40 hover:bg-emerald-600/50 transition"
          >
            <Hammer className="h-4 w-4" />
            {t('tools_forge_btn')}
          </button>
          <button
            type="button"
            disabled={scanning || loading}
            onClick={() => void handleScan()}
            className={secondaryBtnClass}
          >
            <RefreshCw className={`h-4 w-4 ${scanning ? 'animate-spin' : ''}`} />
            {t('tools_scan_btn')}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="rounded-lg bg-blue-500/10 p-2.5 text-blue-400">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <div className="text-2xl font-black text-white">{catalog?.total_tools || 0}</div>
            <div className="text-xs text-slate-400">{t('tools_total')}</div>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="rounded-lg bg-emerald-500/10 p-2.5 text-emerald-400">
            <Zap className="h-5 w-5" />
          </div>
          <div>
            <div className="text-2xl font-black text-white">{catalog?.enabled_tools || 0}</div>
            <div className="text-xs text-slate-400">{t('tools_enabled')}</div>
          </div>
        </div>

        <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <div className="rounded-lg bg-amber-500/10 p-2.5 text-amber-400">
            <Hammer className="h-5 w-5" />
          </div>
          <div>
            <div className="text-2xl font-black text-white">{catalog?.categories?.custom_recipes || 0}</div>
            <div className="text-xs text-slate-400">{t('tools_custom')}</div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('tools_search_placeholder')}
              className={`${inputFieldClass} pl-9`}
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-800/60">
          <button
            type="button"
            onClick={() => setSelectedCategory('all')}
            className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
              selectedCategory === 'all'
                ? 'bg-blue-600 text-white shadow-sm'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            Tutti ({catalog?.total_tools || 0})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              onClick={() => setSelectedCategory(cat)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                selectedCategory === cat
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {cat} ({catalog?.categories[cat] || 0})
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center p-12 text-slate-400">
          <RefreshCw className="h-6 w-6 animate-spin mr-2 text-blue-400" />
          {t('loading')}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {filteredTools.map((tool) => (
            <div
              key={tool.name}
              className="flex flex-col justify-between rounded-xl border border-slate-800/80 bg-slate-900/50 p-4 transition hover:border-slate-700 hover:bg-slate-800/40"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <span className="font-mono text-sm font-bold text-emerald-300">
                    {tool.name}
                  </span>
                  <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-300 border border-slate-700/60">
                    {tool.category}
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-300 leading-relaxed line-clamp-3">
                  {tool.description || 'Nessuna descrizione specificata'}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-400">
                <div className="flex items-center gap-1.5">
                  <span className={`inline-block h-2 w-2 rounded-full ${tool.enabled ? 'bg-emerald-400' : 'bg-red-400'}`} />
                  <span>{tool.enabled ? 'Attivo' : 'Disattivato'}</span>
                </div>
                <span className="font-mono text-[10px] text-slate-500">
                  {tool.source === 'custom_recipe' ? 'custom recipe' : tool.agent}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForgeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl">
            <h3 className="text-lg font-black text-white flex items-center gap-2">
              <Hammer className="h-5 w-5 text-emerald-400" />
              {t('tools_forge_btn')}
            </h3>
            <p className="mt-1 text-xs text-slate-400">
              Sintetizza un nuovo strumento combinando capacità esistenti per estendere il catalogo agentico.
            </p>

            {forgeError && (
              <div className="mt-3 rounded-lg border border-red-500/40 bg-red-950/40 p-2.5 text-xs text-red-300">
                {forgeError}
              </div>
            )}

            <form onSubmit={handleForgeSubmit} className="mt-4 flex flex-col gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-300">Nome Strumento (es. backup_daily)</label>
                <input
                  type="text"
                  required
                  value={forgeName}
                  onChange={(e) => setForgeName(e.target.value)}
                  placeholder="nome_in_minuscolo"
                  className={inputFieldClass}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300">Descrizione Funzionale</label>
                <input
                  type="text"
                  required
                  value={forgeDesc}
                  onChange={(e) => setForgeDesc(e.target.value)}
                  placeholder="A cosa serve questo nuovo strumento..."
                  className={inputFieldClass}
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300">Passi Operativi (JSON)</label>
                <textarea
                  rows={4}
                  required
                  value={forgeStepsRaw}
                  onChange={(e) => setForgeStepsRaw(e.target.value)}
                  className={`${inputFieldClass} font-mono text-xs`}
                />
              </div>

              <div className="mt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowForgeModal(false)}
                  className={secondaryBtnClass}
                >
                  Annulla
                </button>
                <button
                  type="submit"
                  disabled={forging}
                  className={primaryBtnClass}
                >
                  {forging ? 'Sintesi in corso...' : 'Forgia e Registra'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
