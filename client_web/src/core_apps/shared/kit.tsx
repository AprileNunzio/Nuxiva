import React from 'react';
import { Loader2, RefreshCw, WifiOff, X, UploadCloud } from 'lucide-react';
import { PAGE_CLASS } from '../../shared/ui/layout';
import { MD3Switch } from '../../shared/components/MD3Switch';

export type Tone = 'cyan' | 'emerald' | 'amber' | 'rose' | 'purple' | 'slate';

const TONES: Record<Tone, string> = {
  cyan: 'border-transparent bg-primary-container text-on-primary-container',
  emerald: 'border-transparent bg-success-container text-on-success-container',
  amber: 'border-transparent bg-warning-container text-on-warning-container',
  rose: 'border-transparent bg-error-container text-on-error-container',
  purple: 'border-transparent bg-tertiary-container text-on-tertiary-container',
  slate: 'border-transparent bg-surface-container-high text-on-surface',
};

const INK: Record<Tone, string> = {
  cyan: 'text-primary',
  emerald: 'text-success',
  amber: 'text-warning',
  rose: 'text-error',
  purple: 'text-tertiary',
  slate: 'text-on-surface',
};

export const panelClass = 'md-enter rounded-3xl bg-surface-container-low p-4 text-on-surface sm:p-5';
export const inputClass =
  'w-full rounded-xl border border-outline bg-surface-container-lowest px-3 py-2 text-sm text-on-surface placeholder:text-on-surface-variant transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30';
export const gridClass = 'grid gap-4 lg:grid-cols-2 3xl:grid-cols-3';

interface FrameProps {
  readonly title: string;
  readonly description: string;
  readonly onReload?: () => void;
  readonly actions?: React.ReactNode;
  readonly children: React.ReactNode;
}

export const AppFrame: React.FC<FrameProps> = ({ title, description, onReload, actions, children }) => (
  <div className={PAGE_CLASS}>
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-xl font-bold tracking-tight text-on-surface">{title}</h1>
        <p className="mt-1 max-w-3xl text-sm text-on-surface-variant">{description}</p>
      </div>
      <div className="flex items-center gap-2">
        {actions}
        {onReload ? (
          <button
            type="button"
            onClick={onReload}
            aria-label="refresh"
            className="md-state rounded-full border-0 bg-surface-container-high p-2 text-on-surface-variant"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </header>
    {children}
  </div>
);

interface PanelProps {
  readonly title: string;
  readonly icon?: React.ReactNode;
  readonly actions?: React.ReactNode;
  readonly className?: string;
  readonly children: React.ReactNode;
}

export const Panel: React.FC<PanelProps> = ({ title, icon, actions, className = '', children }) => (
  <section className={`${panelClass} ${className} min-w-0`}>
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-on-surface-variant">
        {icon}
        {title}
      </h2>
      {actions}
    </div>
    {children}
  </section>
);

export const Stat: React.FC<{ readonly label: string; readonly value: React.ReactNode; readonly tone?: Tone }> = ({ label, value, tone = 'cyan' }) => (
  <div className="md-lift rounded-2xl bg-surface-container px-3 py-2.5 transition-transform">
    <div className="text-[10px] font-semibold uppercase tracking-widest text-on-surface-variant">{label}</div>
    <div className={`mt-0.5 truncate font-mono text-lg font-bold ${INK[tone]}`}>{value}</div>
  </div>
);

export const StatRow: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => (
  <div className="md-stagger grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4 3xl:grid-cols-6">{children}</div>
);

export const Pill: React.FC<{ readonly tone?: Tone; readonly children: React.ReactNode }> = ({ tone = 'slate', children }) => (
  <span className={`inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${TONES[tone]}`}>{children}</span>
);

interface BtnProps {
  readonly onClick?: () => void;
  readonly busy?: boolean;
  readonly disabled?: boolean;
  readonly tone?: Tone;
  readonly type?: 'button' | 'submit';
  readonly title?: string;
  readonly children: React.ReactNode;
}

export const Btn: React.FC<BtnProps> = ({ onClick, busy = false, disabled = false, tone = 'cyan', type = 'button', title, children }) => (
  <button
    type={type}
    title={title}
    onClick={onClick}
    disabled={busy || disabled}
    className={`md-state inline-flex items-center justify-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-semibold disabled:opacity-50 ${TONES[tone]}`}
  >
    {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : null}
    {children}
  </button>
);

export const Row: React.FC<{ readonly children: React.ReactNode; readonly actions?: React.ReactNode }> = ({ children, actions }) => (
  <li className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-surface-container px-3 py-2">
    <div className="min-w-0 flex-1 text-sm text-on-surface">{children}</div>
    {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
  </li>
);

export const List: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => <ul className="md-stagger flex flex-col gap-2">{children}</ul>;

export const Empty: React.FC<{ readonly children: React.ReactNode }> = ({ children }) => (
  <p className="rounded-2xl border border-dashed border-outline px-3 py-6 text-center text-sm text-on-surface-variant">{children}</p>
);

export const Loading: React.FC<{ readonly label: string }> = ({ label }) => (
  <div className="md-fade flex min-h-[40vh] flex-col items-center justify-center gap-3 text-sm text-on-surface-variant" role="status">
    <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
    {label}
  </div>
);

export const Unreachable: React.FC<{ readonly label: string }> = ({ label }) => (
  <div className="md-fade flex min-h-[40vh] flex-col items-center justify-center gap-3 text-sm text-on-surface-variant" role="alert">
    <span className="md-glyph md-pop h-12 w-12" style={{ '--md-glyph-ink': 'var(--md-sys-color-error)' } as React.CSSProperties}>
      <WifiOff aria-hidden="true" />
    </span>
    {label}
  </div>
);

export const Field: React.FC<{ readonly label: string; readonly children: React.ReactNode }> = ({ label, children }) => (
  <label className="flex flex-col gap-1 text-xs font-semibold text-on-surface-variant">
    {label}
    {children}
  </label>
);

export const Toggle: React.FC<{ readonly checked: boolean; readonly onChange: (value: boolean) => void; readonly label: string; readonly disabled?: boolean }> = ({
  checked,
  onChange,
  label,
  disabled = false,
}) => (
  <MD3Switch checked={checked} onChange={onChange} ariaLabel={label} disabled={disabled} />
);

export function formatTime(seconds: unknown, locale: string): string {
  if (typeof seconds !== 'number' || !seconds) {
    return '—';
  }
  return new Intl.DateTimeFormat(locale, { dateStyle: 'short', timeStyle: 'short' }).format(new Date(seconds * 1000));
}

export function formatBytes(value: unknown): string {
  const size = typeof value === 'number' ? value : 0;
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let n = size;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i += 1;
  }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export const OSSectionHeader: React.FC<{
  readonly title: string;
  readonly eyebrow?: string;
  readonly description?: string;
  readonly badge?: React.ReactNode;
  readonly actions?: React.ReactNode;
}> = ({ title, eyebrow, description, badge, actions }) => (
  <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-outline-variant pb-3">
    <div>
      {eyebrow && <span className="block text-[10px] font-bold uppercase tracking-wider text-primary">{eyebrow}</span>}
      <div className="flex items-center gap-2">
        <h1 className="text-base font-bold text-on-surface">{title}</h1>
        {badge}
      </div>
      {description && <p className="mt-0.5 text-xs text-on-surface-variant">{description}</p>}
    </div>
    {actions && <div className="flex items-center gap-2">{actions}</div>}
  </div>
);

export interface FilterTabOption {
  readonly id: string;
  readonly label: string;
  readonly count?: number;
}

export const OSFilterTabs: React.FC<{
  readonly options: readonly FilterTabOption[];
  readonly selected: string;
  readonly onSelect: (id: string) => void;
  readonly ariaLabel?: string;
}> = ({ options, selected, onSelect, ariaLabel }) => (
  <nav className="flex flex-wrap items-center gap-1.5 mb-4" aria-label={ariaLabel}>
    {options.map((option) => (
      <button
        key={option.id}
        type="button"
        aria-pressed={selected === option.id}
        onClick={() => onSelect(option.id)}
        className={`md-state inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1 text-xs font-medium ${
          selected === option.id
            ? 'border-transparent bg-secondary-container font-semibold text-on-secondary-container'
            : 'border-outline bg-transparent text-on-surface-variant'
        }`}
      >
        <span>{option.label}</span>
        {option.count !== undefined && (
          <span
            className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
              selected === option.id ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant'
            }`}
          >
            {option.count}
          </span>
        )}
      </button>
    ))}
  </nav>
);

export const OSEnergyBar: React.FC<{
  readonly label: string;
  readonly sublabel?: string;
  readonly watts: number;
  readonly maxWatts: number;
  readonly formattedValue: string;
}> = ({ label, sublabel, watts, maxWatts, formattedValue }) => {
  const percent = maxWatts > 0 ? Math.min(100, Math.max(0, (watts / maxWatts) * 100)) : 0;
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-slate-200/80 bg-white p-3 shadow-xs">
      <div className="flex items-center justify-between text-xs">
        <div className="font-semibold text-slate-800 truncate mr-2">{label}</div>
        <div className="font-mono font-bold text-blue-700 shrink-0">{formattedValue}</div>
      </div>
      {sublabel && <div className="text-[11px] text-slate-600">{sublabel}</div>}
      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden mt-1">
        <div
          className="bg-blue-600 h-full rounded-full transition-all duration-300"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
};

export interface OSSidebarItem {
  readonly id: string;
  readonly label: string;
  readonly icon?: React.ReactNode;
  readonly count?: number;
}

export const OSSidebar: React.FC<{
  readonly title?: string;
  readonly items: readonly OSSidebarItem[];
  readonly activeId: string;
  readonly onSelect: (id: string) => void;
  readonly footer?: React.ReactNode;
}> = ({ title, items, activeId, onSelect, footer }) => (
  <nav className="flex h-full flex-col gap-1 overflow-y-auto p-2" aria-label={title}>
    {title && <span className="px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-600">{title}</span>}
    <div className="flex flex-col gap-0.5 flex-1">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          aria-pressed={activeId === item.id}
          onClick={() => onSelect(item.id)}
          className={`md-state flex items-center justify-between gap-2 rounded-full border-0 px-3 py-1.5 text-xs font-medium ${
            activeId === item.id
              ? 'bg-secondary-container font-semibold text-on-secondary-container'
              : 'bg-transparent text-on-surface-variant'
          }`}
        >
          <span className="flex items-center gap-2 truncate">
            {item.icon}
            <span className="truncate">{item.label}</span>
          </span>
          {item.count !== undefined && (
            <span
              className={`rounded-full px-1.5 py-0.2 text-[10px] font-mono ${
                activeId === item.id ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface-variant'
              }`}
            >
              {item.count}
            </span>
          )}
        </button>
      ))}
    </div>
    {footer && <div className="mt-auto pt-2 border-t border-slate-200/70">{footer}</div>}
  </nav>
);

export const OSInspector: React.FC<{
  readonly title: string;
  readonly subtitle?: string;
  readonly onClose?: () => void;
  readonly children: React.ReactNode;
  readonly actions?: React.ReactNode;
}> = ({ title, subtitle, onClose, children, actions }) => (
  <section className="flex h-full flex-col overflow-hidden bg-white" aria-label={title}>
    <header className="flex items-center justify-between border-b border-slate-200/80 px-4 py-2.5">
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-xs font-bold text-slate-800">{title}</h3>
        {subtitle && <p className="truncate text-[11px] text-slate-600">{subtitle}</p>}
      </div>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          aria-label="Chiudi riquadro dettagli"
          className="rounded-md p-1 text-slate-600 hover:bg-slate-100 hover:text-slate-600"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </header>
    <div className="flex-1 overflow-y-auto p-4">{children}</div>
    {actions && <footer className="border-t border-slate-200/80 bg-slate-50/50 p-3">{actions}</footer>}
  </section>
);

export interface OSAppLayoutProps {
  readonly sidebar?: React.ReactNode;
  readonly content: React.ReactNode;
  readonly inspector?: React.ReactNode;
  readonly isInspectorOpen?: boolean;
  readonly onFilesDrop?: (files: File[]) => void | Promise<void>;
  readonly dropLabel?: string;
  readonly dropHint?: string;
  readonly isUploading?: boolean;
  readonly uploadStatus?: string | null;
  readonly uploadProgress?: number | null;
}

export const OSAppLayout: React.FC<OSAppLayoutProps> = ({
  sidebar,
  content,
  inspector,
  isInspectorOpen = true,
  onFilesDrop,
  dropLabel = 'Rilascia qui uno o più file',
  dropHint = 'Trascina e rilascia file per caricarli direttamente in questa finestra',
  isUploading = false,
  uploadStatus,
  uploadProgress,
}) => {
  const [isDragging, setIsDragging] = React.useState(false);

  const handleDragOver = React.useCallback(
    (e: React.DragEvent) => {
      if (!onFilesDrop) return;
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(true);
    },
    [onFilesDrop]
  );

  const handleDragLeave = React.useCallback(
    (e: React.DragEvent) => {
      if (!onFilesDrop) return;
      e.preventDefault();
      e.stopPropagation();
      if (e.currentTarget.contains(e.relatedTarget as Node)) return;
      setIsDragging(false);
    },
    [onFilesDrop]
  );

  const handleDrop = React.useCallback(
    (e: React.DragEvent) => {
      if (!onFilesDrop) return;
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        void onFilesDrop(files);
      }
    },
    [onFilesDrop]
  );

  return (
    <div
      className="os-app-layout relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {sidebar && <aside className="os-app-sidebar">{sidebar}</aside>}
      <main className="os-app-workspace relative">
        {content}

        {isDragging && onFilesDrop && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-blue-900/85 p-8 text-center text-slate-950 backdrop-blur-xs animate-fadeIn">
            <div className="rounded-full bg-slate-100 p-5 ring-4 ring-white/20">
              <UploadCloud className="h-12 w-12 text-slate-950 animate-bounce" />
            </div>
            <strong className="text-base font-bold">{dropLabel}</strong>
            <p className="max-w-md text-xs text-blue-900">{dropHint}</p>
          </div>
        )}

        {(isUploading || uploadStatus) && (
          <div className="absolute bottom-4 right-4 z-40 flex items-center gap-2.5 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-xs text-slate-950 shadow-2xl backdrop-blur-md animate-fadeIn">
            <Loader2 className="h-4 w-4 animate-spin text-blue-600 shrink-0" />
            <div className="flex flex-col gap-1 min-w-[140px]">
              <span className="font-semibold text-slate-900">{uploadStatus || 'Caricamento file…'}</span>
              {uploadProgress !== null && uploadProgress !== undefined && (
                <div className="h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full transition-all duration-200"
                    style={{ width: `${Math.min(100, Math.max(0, uploadProgress))}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </main>
      {inspector && isInspectorOpen && <aside className="os-app-inspector">{inspector}</aside>}
    </div>
  );
};

export function useOSFileUpload(
  onUpload: (files: File[]) => void | Promise<void>,
  options?: { accept?: string; multiple?: boolean }
) {
  const inputRef = React.useRef<HTMLInputElement | null>(null);

  const openPicker = React.useCallback(() => {
    if (inputRef.current) {
      inputRef.current.value = '';
      inputRef.current.click();
    }
  }, []);

  const fileInput = (
    <input
      key="os-file-upload-input"
      ref={inputRef}
      type="file"
      multiple={options?.multiple ?? true}
      accept={options?.accept}
      style={{ display: 'none' }}
      onChange={(e) => {
        const files = Array.from(e.target.files || []);
        if (files.length > 0) {
          void onUpload(files);
        }
      }}
    />
  );

  return { openPicker, fileInput };
}

export { AppViewFrame } from '../../app_shell/window_manager/AppViewFrame';
export { DataGrid as OSDataGrid } from '../../app_shell/window_manager/DataGrid';
export { ApplicationCatalog as OSApplicationCatalog } from '../../app_shell/window_manager/ApplicationCatalog';
export { MetricCard as OSMetricCard } from './MetricCard';
export { useOSApp, useWindowToolbar } from '../../app_shell/window_manager/WindowContext';
