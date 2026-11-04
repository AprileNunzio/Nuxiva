import React, { useEffect, useState } from 'react';
import { getFileUrl, fetchFileText, ShareFileItem } from './api';
import { formatBytes } from '../shared/kit';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { Download, Copy, Check, ArrowLeft, FileText, Image as ImageIcon, Music, Video, Box, File } from 'lucide-react';

interface UniversalFileViewerProps {
  readonly file: ShareFileItem;
  readonly uncPath: string;
  readonly onClose: () => void;
}

export const UniversalFileViewer: React.FC<UniversalFileViewerProps> = ({ file, uncPath, onClose }) => {
  const { t } = useScopedI18n('apps/explorer');
  const [textData, setTextData] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const ext = file.ext.toLowerCase();
  const fileUrl = getFileUrl(file.path);

  const isImage = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'].includes(ext);
  const isPdf = ext === '.pdf';
  const isAudio = ['.mp3', '.wav', '.ogg', '.m4a', '.flac'].includes(ext);
  const isVideo = ['.mp4', '.webm'].includes(ext);
  const is3D = ['.stl', '.obj', '.glb', '.gltf'].includes(ext);
  const isText = [
    '.txt', '.md', '.json', '.py', '.js', '.ts', '.tsx', '.jsx',
    '.html', '.css', '.log', '.sh', '.yaml', '.yml', '.conf',
    '.c', '.cpp', '.h', '.rs', '.go', '.sql', '.env', '.ini'
  ].includes(ext);

  useEffect(() => {
    if (isText) {
      setLoading(true);
      setError(null);
      const controller = new AbortController();
      fetchFileText(file.path, controller.signal)
        .then((data) => {
          setTextData(data);
          setLoading(false);
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : t('viewer_error'));
          setLoading(false);
        });
      return () => controller.abort();
    }
  }, [file.path, isText, t]);

  const handleCopyUnc = async () => {
    try {
      await navigator.clipboard.writeText(uncPath);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // noop
    }
  };

  const getFileCategoryIcon = () => {
    if (isImage) return <ImageIcon className="h-5 w-5 text-emerald-600" />;
    if (isPdf) return <FileText className="h-5 w-5 text-rose-600" />;
    if (isAudio) return <Music className="h-5 w-5 text-purple-600" />;
    if (isVideo) return <Video className="h-5 w-5 text-blue-600" />;
    if (is3D) return <Box className="h-5 w-5 text-amber-600" />;
    if (isText) return <FileText className="h-5 w-5 text-blue-600" />;
    return <File className="h-5 w-5 text-slate-500" />;
  };

  return (
    <div className="flex h-full w-full flex-col bg-slate-50 overflow-hidden">
      {/* Viewer Header */}
      <header className="flex items-center justify-between border-b border-slate-200/80 bg-white px-4 py-2.5">
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            onClick={onClose}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>{t('viewer_back')}</span>
          </button>
          <div className="flex items-center gap-2 min-w-0">
            {getFileCategoryIcon()}
            <div className="min-w-0">
              <strong className="block truncate text-xs font-bold text-slate-900">{file.name}</strong>
              <span className="block truncate text-[11px] text-slate-400 font-mono">{formatBytes(file.size)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void handleCopyUnc()}
            title={t('viewer_copy_smb')}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 transition"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{copied ? t('copied') : t('smb_path')}</span>
          </button>
          <a
            href={fileUrl}
            download={file.name}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1 text-xs font-semibold text-white hover:bg-blue-700 transition"
          >
            <Download className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">{t('download')}</span>
          </a>
        </div>
      </header>

      {/* Viewer Main Canvas */}
      <div className="flex-1 overflow-auto p-4 flex items-center justify-center">
        {isImage && (
          <div className="flex h-full w-full items-center justify-center rounded-xl border border-slate-200 bg-white p-2 shadow-xs">
            <img src={fileUrl} alt={file.name} className="max-h-full max-w-full rounded object-contain" />
          </div>
        )}

        {isPdf && (
          <div className="h-full w-full rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
            <iframe src={fileUrl} title={file.name} className="h-full w-full border-0" />
          </div>
        )}

        {isAudio && (
          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-slate-200 bg-white p-8 shadow-xs max-w-md w-full">
            <div className="rounded-full bg-purple-100 p-6 text-purple-600">
              <Music className="h-12 w-12" />
            </div>
            <div className="text-center">
              <h4 className="text-sm font-bold text-slate-800">{file.name}</h4>
              <p className="text-xs text-slate-400 mt-1">{formatBytes(file.size)}</p>
            </div>
            <audio controls src={fileUrl} className="w-full mt-2" />
          </div>
        )}

        {isVideo && (
          <div className="flex h-full w-full items-center justify-center rounded-xl border border-slate-200 bg-black overflow-hidden shadow-xs">
            <video controls src={fileUrl} className="max-h-full max-w-full" />
          </div>
        )}

        {isText && (
          <div className="flex h-full w-full flex-col rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
            {loading && <div className="p-8 text-center text-xs text-slate-400">{t('viewer_loading')}</div>}
            {error && <div className="p-8 text-center text-xs text-rose-500">{error}</div>}
            {!loading && !error && textData !== null && (
              <pre className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed text-slate-800 select-text">
                <code>{textData}</code>
              </pre>
            )}
          </div>
        )}

        {is3D && (
          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-slate-200 bg-white p-8 shadow-xs max-w-md w-full text-center">
            <div className="rounded-full bg-amber-100 p-6 text-amber-600">
              <Box className="h-12 w-12" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-800">{file.name}</h4>
              <p className="text-xs text-slate-400 mt-1">{t('viewer_3d_model')} ({ext.toUpperCase()}) · {formatBytes(file.size)}</p>
            </div>
            <span className="text-[11px] text-slate-500">
              {t('viewer_3d_desc')}
            </span>
            <a
              href={fileUrl}
              download={file.name}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700"
            >
              <Download className="h-4 w-4" />
              <span>{t('viewer_download_3d')}</span>
            </a>
          </div>
        )}

        {!isImage && !isPdf && !isAudio && !isVideo && !isText && !is3D && (
          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border border-slate-200 bg-white p-8 shadow-xs max-w-md w-full text-center">
            <div className="rounded-full bg-slate-100 p-6 text-slate-500">
              <File className="h-12 w-12" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-800">{file.name}</h4>
              <p className="text-xs text-slate-400 mt-1">{ext.toUpperCase() || t('file')} · {formatBytes(file.size)}</p>
            </div>
            <a
              href={fileUrl}
              download={file.name}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-700"
            >
              <Download className="h-4 w-4" />
              <span>{t('viewer_download')}</span>
            </a>
          </div>
        )}
      </div>
    </div>
  );
};
