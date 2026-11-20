import React, { useState, useEffect } from 'react';
import { useStudioI18n } from '../scope';
import type { SmbItem, Attachment } from '../types';
import { fetchSmbTree } from '../api';

interface SmbFilePickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectFile: (attachment: Attachment) => void;
}

export const SmbFilePickerModal: React.FC<SmbFilePickerModalProps> = ({
  isOpen,
  onClose,
  onSelectFile,
}) => {
  const { t } = useStudioI18n();
  const [currentFolder, setCurrentFolder] = useState('');
  const [items, setItems] = useState<SmbItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedItem, setSelectedItem] = useState<SmbItem | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetchSmbTree(currentFolder)
      .then(setItems)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [isOpen, currentFolder]);

  if (!isOpen) return null;

  const navigateUp = () => {
    if (!currentFolder) return;
    const parts = currentFolder.split('/').filter(Boolean);
    parts.pop();
    setCurrentFolder(parts.join('/'));
  };

  const handleAttach = () => {
    if (!selectedItem || selectedItem.is_dir) return;
    const att: Attachment = {
      id: `smb_${Date.now()}`,
      name: selectedItem.name,
      size: selectedItem.size,
      mime_type: 'application/octet-stream',
      kind: 'smb_file',
      path: selectedItem.relative_path,
    };
    onSelectFile(att);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-xl rounded-2xl bg-slate-900 border border-slate-700/80 shadow-2xl p-5 flex flex-col gap-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-cyan-400">🗄️</span>
            <h2 className="text-base font-semibold text-slate-100">
              {t('smb_browser_title')}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 transition-colors p-1"
            aria-label={t('close')}
          >
            ✕
          </button>
        </div>

        <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
          <button
            type="button"
            disabled={!currentFolder}
            onClick={navigateUp}
            className="text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400"
          >
            ⬆
          </button>
          <span className="font-mono text-cyan-400 truncate">
            /srv/nuxiva/condivisa/{currentFolder}
          </span>
        </div>

        <div className="h-64 overflow-y-auto bg-slate-950/60 rounded-xl border border-slate-800 p-2 flex flex-col gap-1">
          {loading ? (
            <div className="flex items-center justify-center h-full text-xs text-slate-500">
              ...
            </div>
          ) : items.length === 0 ? (
            <div className="flex items-center justify-center h-full text-xs text-slate-500">
              {t('folder_empty')}
            </div>
          ) : (
            items.map((item) => {
              const isSelected = selectedItem?.relative_path === item.relative_path;
              return (
                <div
                  key={item.relative_path}
                  onClick={() => {
                    if (item.is_dir) {
                      setCurrentFolder(item.relative_path);
                      setSelectedItem(null);
                    } else {
                      setSelectedItem(item);
                    }
                  }}
                  className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-cyan-950/60 border border-cyan-500/40 text-cyan-200'
                      : 'hover:bg-slate-800/80 text-slate-300'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span>{item.is_dir ? '📁' : '📄'}</span>
                    <span className="truncate">{item.name}</span>
                  </div>
                  {!item.is_dir && (
                    <span className="text-[10px] text-slate-500 font-mono">
                      {Math.round(item.size / 1024)} KB
                    </span>
                  )}
                </div>
              );
            })
          )}
        </div>

        <div className="flex justify-end items-center gap-2 pt-2 border-t border-slate-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            {t('cancel')}
          </button>
          <button
            type="button"
            disabled={!selectedItem || selectedItem.is_dir}
            onClick={handleAttach}
            className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-medium transition-colors disabled:opacity-40"
          >
            {t('smb_select_file')}
          </button>
        </div>
      </div>
    </div>
  );
};
