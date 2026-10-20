import React from 'react';
import { Loader2 } from 'lucide-react';
import { useMeshI18n } from '../i18nScope';

interface EmptyMeshNoticeProps {
  readonly loading: boolean;
}

export const EmptyMeshNotice: React.FC<EmptyMeshNoticeProps> = ({ loading }) => {
  const { t } = useMeshI18n();
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-8 z-20 flex justify-center px-4">
      <p className="nm-glass flex items-center gap-2 rounded-full border border-slate-700/60 px-4 py-2 text-xs text-slate-300">
        {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-cyan-300" aria-hidden="true" />}
        {t(loading ? 'mesh_loading' : 'mesh_empty')}
      </p>
    </div>
  );
};
