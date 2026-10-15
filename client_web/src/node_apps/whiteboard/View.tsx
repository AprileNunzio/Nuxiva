import React, { useState, useEffect, useRef } from 'react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import {
  Edit3,
  PenTool,
  Highlighter,
  Eraser,
  Trash2,
  Download,
  CloudUpload,
  CheckCircle2,
  Clock,
  Layers,
  RefreshCw,
} from 'lucide-react';

interface Props {
  nodeId?: string;
}

interface WhiteboardEntry {
  id: string;
  title: string;
  created_at: string;
  strokes_count: number;
  data_url?: string;
}

export const View: React.FC<Props> = ({ nodeId = 'node-01' }) => {
  const { t } = useScopedI18n('node_apps/whiteboard');

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentTool, setCurrentTool] = useState<'pen' | 'highlighter' | 'eraser'>('pen');
  const [color, setColor] = useState('#06b6d4'); // Default cyber cyan
  const [strokeWidth, setStrokeWidth] = useState(3);
  const [strokesCount, setStrokesCount] = useState(0);

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [boardTitle, setBoardTitle] = useState('Lavagna Note Nodo');
  const [savedBoards, setSavedBoards] = useState<WhiteboardEntry[]>([]);

  const colors = ['#06b6d4', '#10b981', '#a855f7', '#f59e0b', '#ef4444', '#ffffff'];

  useEffect(() => {
    let isMounted = true;
    const fetchBoards = async () => {
      try {
        const res = await fetch(`/api/v5/nodes/${nodeId}/whiteboards`);
        if (res.ok) {
          const data = await res.json();
          if (isMounted && Array.isArray(data)) {
            setSavedBoards(data);
          }
        }
      } catch (err) {
        console.warn('Whiteboards fetch error', err);
      }
    };
    fetchBoards();
    return () => {
      isMounted = false;
    };
  }, [nodeId]);

  // Canvas drawing handlers
  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    setIsDrawing(true);
    setStrokesCount((prev) => prev + 1);

    const rect = canvas.getBoundingClientRect();
    const x = 'touches' in e ? e.touches[0].clientX - rect.left : e.clientX - rect.left;
    const y = 'touches' in e ? e.touches[0].clientY - rect.top : e.clientY - rect.top;

    ctx.beginPath();
    ctx.moveTo(x, y);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawing) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = 'touches' in e ? e.touches[0].clientX - rect.left : e.clientX - rect.left;
    const y = 'touches' in e ? e.touches[0].clientY - rect.top : e.clientY - rect.top;

    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    if (currentTool === 'eraser') {
      ctx.globalCompositeOperation = 'destination-out';
      ctx.lineWidth = strokeWidth * 4;
    } else if (currentTool === 'highlighter') {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = color;
      ctx.globalAlpha = 0.35;
      ctx.lineWidth = strokeWidth * 3;
    } else {
      ctx.globalCompositeOperation = 'source-over';
      ctx.strokeStyle = color;
      ctx.globalAlpha = 1.0;
      ctx.lineWidth = strokeWidth;
    }

    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const stopDrawing = () => {
    setIsDrawing(false);
  };

  const handleClear = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    setStrokesCount(0);
  };

  const handleExportPNG = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const image = canvas.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = `${boardTitle.toLowerCase().replace(/\s+/g, '_')}_${Date.now()}.png`;
    link.href = image;
    link.click();
  };

  const handleSaveToMesh = async () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    setSaving(true);
    try {
      const dataUrl = canvas.toDataURL('image/png');
      const res = await fetch(`/api/v5/nodes/${nodeId}/whiteboards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: boardTitle,
          data_url: dataUrl,
          strokes_count: strokesCount,
        }),
      });
      const data = await res.json();
      if (data.status === 'saved') {
        setSavedBoards((prev) => [data.whiteboard, ...prev]);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteBoard = async (wbId: string) => {
    try {
      await fetch(`/api/v5/nodes/${nodeId}/whiteboards/${wbId}`, { method: 'DELETE' });
      setSavedBoards((prev) => prev.filter((b) => b.id !== wbId));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6 font-mono text-slate-100">
      {/* Header */}
      <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Edit3 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-wide">{t('title')}</h2>
            <p className="text-xs text-slate-400 mt-0.5">{t('description')}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="text"
            value={boardTitle}
            onChange={(e) => setBoardTitle(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"
          />

          <button
            onClick={handleSaveToMesh}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl text-xs font-semibold shadow-lg shadow-cyan-500/20 transition cursor-pointer"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <CloudUpload className="w-4 h-4" />}
            {saving ? t('saving') : t('save_mesh')}
          </button>
        </div>
      </div>

      {saved && (
        <div className="bg-emerald-950/60 border border-emerald-500/40 p-3.5 rounded-xl flex items-center gap-3 text-xs text-emerald-300">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{t('saved')}</span>
        </div>
      )}

      {/* Toolbar & Canvas Cockpit */}
      <div className="bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        {/* Top Controls */}
        <div className="bg-slate-900/90 border-b border-slate-800 p-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentTool('pen')}
              className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                currentTool === 'pen'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <PenTool className="w-4 h-4" /> {t('tool_pen')}
            </button>

            <button
              onClick={() => setCurrentTool('highlighter')}
              className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                currentTool === 'highlighter'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <Highlighter className="w-4 h-4" /> {t('tool_highlighter')}
            </button>

            <button
              onClick={() => setCurrentTool('eraser')}
              className={`p-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                currentTool === 'eraser'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              <Eraser className="w-4 h-4" /> {t('tool_eraser')}
            </button>
          </div>

          {/* Color Palette */}
          <div className="flex items-center gap-2">
            {colors.map((c) => (
              <button
                key={c}
                onClick={() => {
                  setColor(c);
                  if (currentTool === 'eraser') setCurrentTool('pen');
                }}
                style={{ backgroundColor: c }}
                className={`w-6 h-6 rounded-full transition transform hover:scale-110 ${
                  color === c && currentTool !== 'eraser' ? 'ring-2 ring-white ring-offset-2 ring-offset-slate-950 scale-110' : ''
                }`}
              />
            ))}
          </div>

          {/* Stroke Width & Actions */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <span>{t('stroke_width')}:</span>
              <select
                value={strokeWidth}
                onChange={(e) => setStrokeWidth(parseInt(e.target.value, 10))}
                className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white"
              >
                <option value="2">2px (Fine)</option>
                <option value="5">5px (Medio)</option>
                <option value="12">12px (Spesso)</option>
                <option value="24">24px (Marker)</option>
              </select>
            </div>

            <button
              onClick={handleClear}
              className="p-2 rounded-lg bg-slate-800 hover:bg-rose-950/40 text-slate-400 hover:text-rose-400 transition"
              title={t('clear')}
            >
              <Trash2 className="w-4 h-4" />
            </button>

            <button
              onClick={handleExportPNG}
              className="p-2 rounded-lg bg-slate-800 hover:bg-cyan-950/40 text-slate-400 hover:text-cyan-400 transition"
              title={t('export_png')}
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Drawing Surface */}
        <div className="relative bg-[#020617] cursor-crosshair">
          <canvas
            ref={canvasRef}
            width={1200}
            height={500}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={startDrawing}
            onTouchMove={draw}
            onTouchEnd={stopDrawing}
            className="w-full h-[400px] block"
          />
        </div>
      </div>

      {/* Saved Whiteboards Cluster History */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-4">
        <div className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center justify-between">
          <span className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            {t('saved_boards_title')}
          </span>
          <span className="text-[10px] text-slate-500">{savedBoards.length} salvate</span>
        </div>

        {savedBoards.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-6">{t('no_boards')}</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {savedBoards.map((b) => (
              <div key={b.id} className="bg-slate-950 border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-bold text-white">{b.title}</h4>
                  <div className="text-[10px] text-slate-500 mt-1 flex items-center gap-2">
                    <Clock className="w-3 h-3 text-cyan-400" />
                    <span>{b.created_at}</span>
                    <span>· {b.strokes_count} {t('strokes')}</span>
                  </div>
                </div>

                <div className="mt-4 pt-2 border-t border-slate-800/80 flex items-center justify-end">
                  <button
                    onClick={() => handleDeleteBoard(b.id)}
                    className="text-[10px] text-slate-500 hover:text-rose-400 transition"
                  >
                    {t('delete')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default View;
