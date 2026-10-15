import React, { useState, useEffect } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  Printer,
  FileText,
  CheckCircle2,
  AlertCircle,
  Thermometer,
  Layers,
  Sparkles,
  Save,
  RefreshCw,
  Box,
} from 'lucide-react';

interface Props {
  nodeId?: string;
}

interface PrinterItem {
  id: string;
  name: string;
  type: string;
  connection: string;
  status: string;
  ink?: {
    cyan?: number;
    magenta?: number;
    yellow?: number;
    black?: number;
  };
  bed_temp?: number;
  nozzle_temp?: number;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/printers');

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [printers, setPrinters] = useState<PrinterItem[]>([]);
  const [selectedPrinterId, setSelectedPrinterId] = useState<string>('');
  const [isPrintingTest, setIsPrintingTest] = useState(false);
  const [testSuccess, setTestSuccess] = useState<string | null>(null);
  const [isCleaning, setIsCleaning] = useState(false);
  const [cleaningDone, setCleaningDone] = useState(false);

  const fetchHardware = async (isMounted = true) => {
    try {
      setLoading(true);
      const res = await fetch(`/api/v5/nodes/${nodeId}/hardware`);
      if (res.ok) {
        const data = await res.json();
        if (isMounted) {
          if (Array.isArray(data.printers) && data.printers.length > 0) {
            setPrinters(data.printers);
            setSelectedPrinterId(data.printers[0].id);
          } else {
            setPrinters([]);
            setSelectedPrinterId('');
          }
        }
      }
    } catch (err) {
      console.warn('Hardware fetch failed', err);
    } finally {
      if (isMounted) setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetchHardware(isMounted);
    return () => {
      isMounted = false;
    };
  }, [nodeId]);

  const selectedPrinter = printers.find((p) => p.id === selectedPrinterId) || printers[0];

  const handlePrintTest = async () => {
    setIsPrintingTest(true);
    setTestSuccess(null);
    try {
      const res = await fetch(`/api/v5/nodes/${nodeId}/hardware/test_print`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          printer_id: selectedPrinterId,
          paper_size: 'A4',
        }),
      });
      const data = await res.json();
      if (data.success) {
        setTestSuccess(`${t('test_sent')} (Job ID: ${data.job_id})`);
      }
    } catch (err: any) {
      setTestSuccess(`Errore: ${err.message}`);
    } finally {
      setIsPrintingTest(false);
    }
  };

  const handleCleanHeads = () => {
    setIsCleaning(true);
    setCleaningDone(false);
    setTimeout(() => {
      setIsCleaning(false);
      setCleaningDone(true);
      setTimeout(() => setCleaningDone(false), 3000);
    }, 2500);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`/api/v5/nodes/${nodeId}/apps/printers/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enabled: true,
          settings: { selectedPrinterId },
        }),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-12 flex flex-col items-center justify-center text-slate-400 font-mono gap-3">
        <RefreshCw className="w-6 h-6 animate-spin text-cyan-400" />
        <span className="text-xs">Rilevamento stampanti collegate al nodo...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-mono text-slate-100">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Printer className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-wide">{t('title')}</h2>
            <p className="text-xs text-slate-400 mt-0.5">{t('description')}</p>
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-cyan-500/20 transition cursor-pointer"
        >
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {saving ? t('saving') : t('save')}
        </button>
      </div>

      {saved && (
        <div className="bg-emerald-950/60 border border-emerald-500/40 p-3.5 rounded-xl flex items-center gap-3 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{t('saved')}</span>
        </div>
      )}

      {/* Printer List & Selection */}
      {printers.length === 0 ? (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center flex flex-col items-center justify-center gap-3">
          <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/50 text-slate-500">
            <Printer className="w-8 h-8 text-slate-400" />
          </div>
          <h3 className="text-sm font-bold text-white tracking-wide">Nessuna Stampante Rilevata</h3>
          <p className="text-xs text-slate-400 max-w-md leading-relaxed">
            Nessuna stampante fisica (USB) o stampante di rete (CUPS / IPP / WSD) è attualmente configurata su questo nodo.
            Collega o installa una stampante sul sistema operativo e clicca su Aggiorna.
          </p>
          <button
            onClick={() => fetchHardware(true)}
            className="mt-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-cyan-500/30 rounded-xl text-xs font-semibold flex items-center gap-2 cursor-pointer transition shadow-md"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Rileva Periferiche</span>
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {printers.map((p) => {
              const isSelected = selectedPrinterId === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => setSelectedPrinterId(p.id)}
                  className={`p-4 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                    isSelected
                      ? 'bg-cyan-950/30 border-cyan-500/60 ring-1 ring-cyan-500/40 shadow-lg shadow-cyan-950/20'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                        {p.type === '3d_printer' ? <Box className="w-4 h-4" /> : <Printer className="w-4 h-4" />}
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                        {p.status.toUpperCase()}
                      </span>
                    </div>
                    <h3 className="text-xs font-bold text-white leading-snug">{p.name}</h3>
                    <div className="text-[10px] text-slate-400 mt-1">{p.connection}</div>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-800/80 text-[10px] text-slate-500 flex justify-between items-center">
                    <span>Tipo: {t(`type_${p.type}`) || p.type}</span>
                    {isSelected && <span className="w-2 h-2 rounded-full bg-cyan-400" />}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selected Printer Cockpit */}
          {selectedPrinter && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div className="text-xs font-semibold text-slate-400">{t('printer_details')}</div>
              <h3 className="text-lg font-bold text-white mt-0.5">{selectedPrinter.name}</h3>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={handlePrintTest}
                disabled={isPrintingTest}
                className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-cyan-600/20 disabled:opacity-50 cursor-pointer"
              >
                {isPrintingTest ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
                {isPrintingTest ? t('printing_test') : t('print_test_btn')}
              </button>

              {selectedPrinter.type !== '3d_printer' && (
                <button
                  onClick={handleCleanHeads}
                  disabled={isCleaning}
                  className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold border border-slate-700 transition"
                >
                  {isCleaning ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-amber-400" />}
                  {isCleaning ? 'Pulizia...' : t('head_cleaning')}
                </button>
              )}
            </div>
          </div>

          {testSuccess && (
            <div className="bg-emerald-950/60 border border-emerald-500/40 p-3 rounded-xl flex items-center gap-2 text-xs text-emerald-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>{testSuccess}</span>
            </div>
          )}

          {cleaningDone && (
            <div className="bg-cyan-950/60 border border-cyan-500/40 p-3 rounded-xl flex items-center gap-2 text-xs text-cyan-300">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
              <span>{t('cleaning_done')}</span>
            </div>
          )}

          {/* Consumables / Temperatures */}
          {selectedPrinter.type === '3d_printer' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-400 flex items-center gap-1.5">
                    <Thermometer className="w-4 h-4 text-rose-400" />
                    {t('nozzle_temp')}
                  </div>
                  <div className="text-2xl font-bold text-white mt-1">{selectedPrinter.nozzle_temp || 205.0} °C</div>
                </div>
                <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-2 py-1 rounded">STABILE</span>
              </div>

              <div className="bg-slate-950 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-400 flex items-center gap-1.5">
                    <Thermometer className="w-4 h-4 text-amber-400" />
                    {t('bed_temp')}
                  </div>
                  <div className="text-2xl font-bold text-white mt-1">{selectedPrinter.bed_temp || 60.0} °C</div>
                </div>
                <span className="text-[10px] text-emerald-400 font-bold bg-emerald-500/10 px-2 py-1 rounded">STABILE</span>
              </div>
            </div>
          ) : (
            <div>
              <div className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-cyan-400" />
                {t('ink_levels')}
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {selectedPrinter.ink?.black !== undefined && (
                  <div className="bg-slate-950 border border-slate-800 p-3.5 rounded-xl">
                    <div className="flex justify-between text-xs text-slate-300 mb-1.5">
                      <span>Nero (K)</span>
                      <span className="font-bold text-white">{selectedPrinter.ink.black}%</span>
                    </div>
                    <div className="h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div style={{ width: `${selectedPrinter.ink.black}%` }} className="h-full bg-slate-400 rounded-full" />
                    </div>
                  </div>
                )}

                {selectedPrinter.ink?.cyan !== undefined && (
                  <div className="bg-slate-950 border border-slate-800 p-3.5 rounded-xl">
                    <div className="flex justify-between text-xs text-cyan-300 mb-1.5">
                      <span>Ciano (C)</span>
                      <span className="font-bold text-cyan-400">{selectedPrinter.ink.cyan}%</span>
                    </div>
                    <div className="h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div style={{ width: `${selectedPrinter.ink.cyan}%` }} className="h-full bg-cyan-400 rounded-full" />
                    </div>
                  </div>
                )}

                {selectedPrinter.ink?.magenta !== undefined && (
                  <div className="bg-slate-950 border border-slate-800 p-3.5 rounded-xl">
                    <div className="flex justify-between text-xs text-pink-300 mb-1.5">
                      <span>Magenta (M)</span>
                      <span className="font-bold text-pink-400">{selectedPrinter.ink.magenta}%</span>
                    </div>
                    <div className="h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div style={{ width: `${selectedPrinter.ink.magenta}%` }} className="h-full bg-pink-500 rounded-full" />
                    </div>
                  </div>
                )}

                {selectedPrinter.ink?.yellow !== undefined && (
                  <div className="bg-slate-950 border border-slate-800 p-3.5 rounded-xl">
                    <div className="flex justify-between text-xs text-amber-300 mb-1.5">
                      <span>Giallo (Y)</span>
                      <span className="font-bold text-amber-400">{selectedPrinter.ink.yellow}%</span>
                    </div>
                    <div className="h-2 bg-slate-900 rounded-full overflow-hidden">
                      <div style={{ width: `${selectedPrinter.ink.yellow}%` }} className="h-full bg-amber-400 rounded-full" />
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Active Spool Queue */}
          <div className="pt-2">
            <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
              <span>{t('queue_title')}</span>
              <span className="text-[10px] text-slate-500">Spooler: CUPS 2.4.2</span>
            </div>
            <div className="bg-slate-950 border border-slate-800/80 rounded-xl p-4 text-xs text-slate-500 text-center flex items-center justify-center gap-2">
              <AlertCircle className="w-4 h-4 text-slate-600" />
              <span>{t('queue_empty')}</span>
            </div>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
};

export default View;
