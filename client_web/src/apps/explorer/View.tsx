import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useOSApp, useWindowToolbar } from '../../app_shell/window_manager/WindowContext';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';
import { useAssistantIdentity } from '../../shared/identity/IdentityContext';
import {
  OSAppLayout,
  OSSidebar,
  OSInspector,
  formatBytes,
  formatTime,
  Loading,
  Empty,
  useOSFileUpload,
} from '../shared/kit';
import {
  fetchSharesOverview,
  fetchShareFiles,
  createFolder,
  uploadShareFile,
  getFileUrl,
  ShareFileItem,
  SharesOverviewResponse,
} from './api';
import { UniversalFileViewer } from './FileViewer';
import {
  Folder,
  FolderPlus,
  FileText,
  Globe,
  Box,
  Code,
  Share2,
  Music,
  Video,
  Image as ImageIcon,
  File,
  RefreshCw,
  Copy,
  Check,
  Download,
  Eye,
  ArrowUp,
  LayoutGrid,
  List,
  Server,
  HardDrive,
  UploadCloud,
} from 'lucide-react';
import './style.css';

export const View: React.FC = () => {
  const { t, lang } = useScopedI18n('apps/explorer');
  const os = useOSApp();
  const assistant = useAssistantIdentity();

  const [overview, setOverview] = useState<SharesOverviewResponse | null>(null);
  const [subpath, setSubpath] = useState<string>('');
  const [items, setItems] = useState<readonly ShareFileItem[]>([]);
  const [uncPath, setUncPath] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedItem, setSelectedItem] = useState<ShareFileItem | null>(null);
  const [openFile, setOpenFile] = useState<ShareFileItem | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [copiedUnc, setCopiedUnc] = useState(false);

  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [folderModalOpen, setFolderModalOpen] = useState(false);

  // Upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);

  // Load Shares Overview on mount
  const loadOverview = useCallback(async () => {
    try {
      const data = await fetchSharesOverview();
      setOverview(data);
      if (!subpath && data.folders.length > 0) {
        setSubpath(data.folders[0].name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('loading_contents'));
    }
  }, [subpath, t]);

  // Load files for current subpath
  const loadFiles = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchShareFiles(path);
      setItems(res.items);
      setUncPath(res.unc);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('loading_contents'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    if (subpath !== undefined) {
      void loadFiles(subpath);
      setSelectedItem(null);
    }
  }, [subpath, loadFiles]);

  // Handle single or multiple files upload
  const handleUploadFiles = useCallback(
    async (files: File[]) => {
      if (!files.length) return;
      setIsUploading(true);
      setUploadStatus(t('uploading_files'));
      setUploadProgress(10);
      try {
        for (let i = 0; i < files.length; i++) {
          await uploadShareFile(subpath, files[i]);
          setUploadProgress(Math.round(((i + 1) / files.length) * 100));
        }
        setUploadStatus(t('upload_success'));
        setTimeout(() => {
          setIsUploading(false);
          setUploadStatus(null);
          setUploadProgress(null);
          void loadFiles(subpath);
        }, 1500);
      } catch (err) {
        setUploadStatus(err instanceof Error ? err.message : t('viewer_error'));
        setTimeout(() => {
          setIsUploading(false);
          setUploadStatus(null);
          setUploadProgress(null);
        }, 3000);
      }
    },
    [subpath, loadFiles, t]
  );

  const { openPicker, fileInput } = useOSFileUpload(handleUploadFiles);

  // Synchronize OS Window Title and Breadcrumbs
  useEffect(() => {
    const rootName = assistant.name || 'Nuxiva';
    const crumbs: Array<{ id: string; label: string; onClick?: () => void }> = [
      {
        id: 'root',
        label: rootName,
        onClick: () => {
          setSubpath('');
          setOpenFile(null);
        },
      },
    ];

    if (subpath) {
      const parts = subpath.split('/').filter(Boolean);
      let accumulated = '';
      parts.forEach((part, index) => {
        accumulated = accumulated ? `${accumulated}/${part}` : part;
        const targetPath = accumulated;
        const isLast = index === parts.length - 1 && !openFile;
        crumbs.push({
          id: targetPath,
          label: part,
          onClick: isLast
            ? undefined
            : () => {
                setSubpath(targetPath);
                setOpenFile(null);
              },
        });
      });
    }

    if (openFile) {
      crumbs.push({
        id: openFile.name,
        label: openFile.name,
      });
    }

    os.setBreadcrumbs?.(crumbs);
  }, [assistant.name, subpath, openFile, os]);

  // Synchronize OS Status Bar
  useEffect(() => {
    os.setStatus({
      connected: overview?.active === 'active',
      itemCount: items.length,
      details: overview?.windows ? `SMB: ${overview.windows}` : t('samba_smb'),
    });
  }, [overview, items.length, os, t]);

  // Toolbar Actions handler
  useWindowToolbar(
    useCallback(
      (id: string, value?: string) => {
        if (id === 'search') {
          os.setSearchQuery(value || '');
        }
        if (id === 'refresh') {
          void loadOverview();
          void loadFiles(subpath);
        }
        if (id === 'new_folder') {
          setFolderModalOpen(true);
        }
        if (id === 'upload') {
          openPicker();
        }
      },
      [loadOverview, loadFiles, subpath, openPicker, os]
    )
  );

  // Filter items according to search query
  const searchQuery = (os.searchQuery || '').trim().toLowerCase();
  const filteredItems = useMemo(() => {
    if (!searchQuery) return items;
    return items.filter((item) => item.name.toLowerCase().includes(searchQuery));
  }, [items, searchQuery]);

  const handleCopyUnc = async (textToCopy: string) => {
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopiedUnc(true);
      setTimeout(() => setCopiedUnc(false), 2000);
    } catch {
      // noop
    }
  };

  const handleCreateFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    setCreatingFolder(true);
    try {
      await createFolder(subpath, newFolderName.trim());
      setNewFolderName('');
      setFolderModalOpen(false);
      await loadFiles(subpath);
    } catch (err) {
      alert(err instanceof Error ? err.message : t('viewer_error'));
    } finally {
      setCreatingFolder(false);
    }
  };

  const getFolderIcon = (name: string) => {
    if (name.includes('Documenti')) return <FileText className="h-4 w-4 text-blue-500" />;
    if (name.includes('Siti')) return <Globe className="h-4 w-4 text-indigo-500" />;
    if (name.includes('3D')) return <Box className="h-4 w-4 text-amber-500" />;
    if (name.includes('Codice')) return <Code className="h-4 w-4 text-emerald-500" />;
    if (name.includes('Scambio')) return <Share2 className="h-4 w-4 text-purple-500" />;
    if (name.includes('Musica')) return <Music className="h-4 w-4 text-rose-500" />;
    return <Folder className="h-4 w-4 text-amber-500" />;
  };

  const getFileIcon = (item: ShareFileItem) => {
    if (item.is_dir) return <Folder className="h-5 w-5 text-amber-500" />;
    const ext = item.ext.toLowerCase();
    if (['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'].includes(ext)) {
      return <ImageIcon className="h-5 w-5 text-emerald-600" />;
    }
    if (ext === '.pdf') {
      return <FileText className="h-5 w-5 text-rose-600" />;
    }
    if (['.mp3', '.wav', '.ogg', '.m4a', '.flac'].includes(ext)) {
      return <Music className="h-5 w-5 text-purple-600" />;
    }
    if (['.mp4', '.webm'].includes(ext)) {
      return <Video className="h-5 w-5 text-blue-600" />;
    }
    if (['.stl', '.obj', '.glb', '.gltf'].includes(ext)) {
      return <Box className="h-5 w-5 text-amber-600" />;
    }
    if (['.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.json', '.sh'].includes(ext)) {
      return <Code className="h-5 w-5 text-indigo-600" />;
    }
    return <File className="h-5 w-5 text-slate-500" />;
  };

  // Sidebar items from overview
  const sidebarItems = useMemo(() => {
    if (!overview?.folders) return [];
    return overview.folders.map((folder) => ({
      id: folder.name,
      label: folder.name,
      icon: getFolderIcon(folder.name),
      count: folder.count,
    }));
  }, [overview]);

  const activeSidebarId = useMemo(() => {
    const rootFolder = subpath.split('/')[0] || '';
    return rootFolder;
  }, [subpath]);

  const navigateUp = () => {
    if (!subpath) return;
    const parts = subpath.split('/').filter(Boolean);
    parts.pop();
    setSubpath(parts.join('/'));
  };

  // If a file is opened in universal preview mode
  if (openFile) {
    const fileUnc = uncPath ? `${uncPath}\\${openFile.name}` : openFile.name;
    return (
      <UniversalFileViewer
        file={openFile}
        uncPath={fileUnc}
        onClose={() => setOpenFile(null)}
      />
    );
  }

  const sidebarFooter = overview ? (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-200/80 bg-white p-2.5 shadow-2xs">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-800">
        <span className="flex items-center gap-1.5">
          <Server className="h-3.5 w-3.5 text-blue-600" />
          <span>{t('samba_smb')}</span>
        </span>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
            overview.active === 'active'
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : 'bg-amber-50 text-amber-700 border border-amber-200'
          }`}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          {overview.active === 'active' ? t('active') : overview.active}
        </span>
      </div>
      <div className="text-[11px] text-slate-500 font-mono truncate" title={overview.windows}>
        {overview.windows}
      </div>
      <button
        type="button"
        onClick={() => void handleCopyUnc(overview.windows)}
        className="inline-flex w-full items-center justify-center gap-1.5 rounded border border-slate-200 bg-slate-50 py-1 text-[11px] font-medium text-slate-700 hover:bg-slate-100 transition"
      >
        {copiedUnc ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
        <span>{copiedUnc ? t('copied') : t('copy_network_path')}</span>
      </button>
    </div>
  ) : null;

  const inspectorContent = selectedItem ? (
    <div className="flex flex-col gap-4">
      {/* File/Folder preview header */}
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-slate-200/80 bg-slate-50/70 p-4 text-center">
        <div className="rounded-xl bg-white p-3 shadow-xs">
          {getFileIcon(selectedItem)}
        </div>
        <strong className="text-xs font-bold text-slate-900 break-all">{selectedItem.name}</strong>
        <span className="text-[11px] text-slate-400">
          {selectedItem.is_dir ? t('shared_folder') : `${selectedItem.ext.toUpperCase() || t('file')} · ${formatBytes(selectedItem.size)}`}
        </span>
      </div>

      {/* Quick image thumbnail if applicable */}
      {!selectedItem.is_dir && ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'].includes(selectedItem.ext.toLowerCase()) && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-100 flex items-center justify-center p-1 max-h-40">
          <img
            src={getFileUrl(selectedItem.path)}
            alt={selectedItem.name}
            className="max-h-36 max-w-full rounded object-contain"
          />
        </div>
      )}

      {/* Metadata list */}
      <div className="flex flex-col gap-2 rounded-lg border border-slate-200/70 bg-white p-3 text-xs">
        <div>
          <span className="block text-[10px] font-bold uppercase text-slate-400">{t('internal_path')}</span>
          <span className="font-mono text-slate-700 break-all select-text">{selectedItem.path}</span>
        </div>
        <div>
          <span className="block text-[10px] font-bold uppercase text-slate-400">{t('windows_network_path')}</span>
          <div className="flex items-center justify-between gap-1 mt-0.5">
            <span className="font-mono text-[11px] text-slate-700 break-all select-text">
              {uncPath ? `${uncPath}\\${selectedItem.name}` : selectedItem.name}
            </span>
            <button
              type="button"
              onClick={() => void handleCopyUnc(uncPath ? `${uncPath}\\${selectedItem.name}` : selectedItem.name)}
              className="p-1 text-slate-400 hover:text-slate-700"
              title={t('copy_network_path')}
            >
              <Copy className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        {!selectedItem.is_dir && (
          <div>
            <span className="block text-[10px] font-bold uppercase text-slate-400">{t('size')}</span>
            <span className="font-mono text-slate-700">{formatBytes(selectedItem.size)}</span>
          </div>
        )}
        {selectedItem.mtime > 0 && (
          <div>
            <span className="block text-[10px] font-bold uppercase text-slate-400">{t('last_modified')}</span>
            <span className="text-slate-700">{formatTime(selectedItem.mtime, lang)}</span>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-2">
        {selectedItem.is_dir ? (
          <button
            type="button"
            onClick={() => setSubpath(selectedItem.path)}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition"
          >
            <Folder className="h-4 w-4" />
            <span>{t('open_folder')}</span>
          </button>
        ) : (
          <>
            <button
              type="button"
              onClick={() => setOpenFile(selectedItem)}
              className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 transition"
            >
              <Eye className="h-4 w-4" />
              <span>{t('open_preview')}</span>
            </button>
            <a
              href={getFileUrl(selectedItem.path)}
              download={selectedItem.name}
              className="inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
            >
              <Download className="h-4 w-4" />
              <span>{t('download_file')}</span>
            </a>
          </>
        )}
      </div>
    </div>
  ) : (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center text-slate-400">
      <div className="rounded-full bg-slate-100 p-4 text-slate-400">
        <HardDrive className="h-8 w-8" />
      </div>
      <div>
        <strong className="block text-xs font-semibold text-slate-700">{t('no_selection')}</strong>
        <p className="text-[11px] text-slate-400 mt-1">
          {t('no_selection_hint')}
        </p>
      </div>
    </div>
  );

  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-slate-50">
      {fileInput}
      <OSAppLayout
        onFilesDrop={handleUploadFiles}
        isUploading={isUploading}
        uploadStatus={uploadStatus}
        uploadProgress={uploadProgress}
        dropLabel={t('drop_files')}
        dropHint={t('drop_files_hint')}
        sidebar={
          <OSSidebar
            title={t('smb_folders')}
            items={sidebarItems}
            activeId={activeSidebarId}
            onSelect={(id) => {
              setSubpath(id);
              setOpenFile(null);
            }}
            footer={sidebarFooter}
          />
        }
        content={
          <div className="flex h-full flex-col overflow-hidden">
            {/* Workspace action bar */}
            <header className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/80 bg-white px-4 py-2">
              <div className="flex items-center gap-2 min-w-0">
                {subpath && (
                  <button
                    type="button"
                    onClick={navigateUp}
                    title={t('up_folder')}
                    className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white p-1 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition"
                  >
                    <ArrowUp className="h-4 w-4" />
                  </button>
                )}
                <div className="min-w-0">
                  <span className="block truncate text-xs font-bold text-slate-800">
                    {subpath ? subpath.split('/').pop() : assistant.name}
                  </span>
                  {uncPath && (
                    <span className="block truncate text-[10px] font-mono text-slate-400" title={uncPath}>
                      {uncPath}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={openPicker}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
                  title={t('upload_file')}
                >
                  <UploadCloud className="h-3.5 w-3.5 text-blue-600" />
                  <span className="hidden sm:inline">{t('upload_file')}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setFolderModalOpen(true)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 transition"
                >
                  <FolderPlus className="h-3.5 w-3.5 text-blue-600" />
                  <span className="hidden sm:inline">{t('new_folder')}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    void loadOverview();
                    void loadFiles(subpath);
                  }}
                  title={t('refresh')}
                  className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white p-1 text-slate-600 hover:bg-slate-50 transition"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
                <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100 p-0.5">
                  <button
                    type="button"
                    onClick={() => setViewMode('grid')}
                    aria-pressed={viewMode === 'grid'}
                    title={t('grid_view')}
                    className={`rounded p-1 transition ${
                      viewMode === 'grid' ? 'bg-white text-blue-600 shadow-2xs' : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    <LayoutGrid className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('list')}
                    aria-pressed={viewMode === 'list'}
                    title={t('list_view')}
                    className={`rounded p-1 transition ${
                      viewMode === 'list' ? 'bg-white text-blue-600 shadow-2xs' : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    <List className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </header>

            {/* Folder creation inline modal */}
            {folderModalOpen && (
              <form
                onSubmit={handleCreateFolder}
                className="flex items-center gap-2 border-b border-blue-200 bg-blue-50/70 px-4 py-2.5 animate-fadeIn"
              >
                <FolderPlus className="h-4 w-4 text-blue-600 shrink-0" />
                <span className="text-xs font-semibold text-blue-900">{t('new_folder')}:</span>
                <input
                  type="text"
                  autoFocus
                  placeholder={t('folder_name_placeholder')}
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  className="flex-1 rounded border border-blue-300 bg-white px-2 py-1 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  disabled={creatingFolder || !newFolderName.trim()}
                  className="rounded bg-blue-600 px-3 py-1 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {creatingFolder ? '…' : t('create')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setFolderModalOpen(false);
                    setNewFolderName('');
                  }}
                  className="rounded border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  {t('cancel')}
                </button>
              </form>
            )}

            {/* Main content area */}
            <div className="flex-1 overflow-auto p-4">
              {loading && <Loading label={t('loading_contents')} />}
              {error && (
                <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-700">
                  {error}
                </div>
              )}
              {!loading && !error && filteredItems.length === 0 && (
                <Empty>
                  {searchQuery ? t('empty_search') : t('empty_folder')}
                </Empty>
              )}

              {!loading && !error && filteredItems.length > 0 && viewMode === 'grid' && (
                <div className="grid grid-cols-[repeat(auto-fill,minmax(110px,1fr))] gap-3">
                  {filteredItems.map((item) => {
                    const isSelected = selectedItem?.path === item.path;
                    return (
                      <div
                        key={item.path}
                        onClick={() => setSelectedItem(item)}
                        onDoubleClick={() => {
                          if (item.is_dir) {
                            setSubpath(item.path);
                          } else {
                            setOpenFile(item);
                          }
                        }}
                        className={`group flex flex-col items-center justify-center gap-2 rounded-xl border p-3 text-center cursor-pointer transition select-none ${
                          isSelected
                            ? 'border-blue-500 bg-blue-50/80 shadow-xs ring-1 ring-blue-500'
                            : 'border-slate-200/80 bg-white hover:border-slate-300 hover:bg-slate-50/80'
                        }`}
                      >
                        <div className="rounded-lg p-2 transition group-hover:scale-105">
                          {getFileIcon(item)}
                        </div>
                        <span
                          className="w-full truncate text-xs font-medium text-slate-700"
                          title={item.name}
                        >
                          {item.name}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          {item.is_dir ? t('shared_folder') : formatBytes(item.size)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {!loading && !error && filteredItems.length > 0 && viewMode === 'list' && (
                <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xs">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/70 text-[11px] font-bold uppercase text-slate-500">
                        <th className="px-3 py-2">{t('title')}</th>
                        <th className="px-3 py-2 w-28">{t('size')}</th>
                        <th className="px-3 py-2 w-40">{t('last_modified')}</th>
                        <th className="px-3 py-2 w-20 text-right">{t('open')}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredItems.map((item) => {
                        const isSelected = selectedItem?.path === item.path;
                        return (
                          <tr
                            key={item.path}
                            onClick={() => setSelectedItem(item)}
                            onDoubleClick={() => {
                              if (item.is_dir) {
                                setSubpath(item.path);
                              } else {
                                setOpenFile(item);
                              }
                            }}
                            className={`cursor-pointer transition select-none ${
                              isSelected ? 'bg-blue-50/80 text-blue-900 font-medium' : 'hover:bg-slate-50'
                            }`}
                          >
                            <td className="px-3 py-2">
                              <div className="flex items-center gap-2 truncate">
                                {getFileIcon(item)}
                                <span className="truncate">{item.name}</span>
                              </div>
                            </td>
                            <td className="px-3 py-2 font-mono text-slate-500">
                              {item.is_dir ? '—' : formatBytes(item.size)}
                            </td>
                            <td className="px-3 py-2 text-slate-400">
                              {item.mtime > 0 ? formatTime(item.mtime, lang) : '—'}
                            </td>
                            <td className="px-3 py-2 text-right">
                              {!item.is_dir && (
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setOpenFile(item);
                                  }}
                                  title={t('open')}
                                  className="inline-flex rounded p-1 text-slate-400 hover:text-blue-600 transition"
                                >
                                  <Eye className="h-3.5 w-3.5" />
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        }
        inspector={
          <OSInspector
            title={t('details_and_preview')}
            subtitle={selectedItem ? selectedItem.name : t('no_selection')}
            onClose={() => setSelectedItem(null)}
          >
            {inspectorContent}
          </OSInspector>
        }
        isInspectorOpen={true}
      />
    </div>
  );
};
