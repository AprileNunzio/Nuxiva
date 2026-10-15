import React, { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { ReportedError, subscribeErrors } from './errorBus';
import { useScopedI18n } from '../i18n/useScopedI18n';

const VISIBLE_LIMIT = 3;
const AUTO_DISMISS_MS = 8000;
const KNOWN_CODES = new Set([
  'topology_unavailable',
  'telemetry_frame_rejected',
  'bind_failed',
  'render_failure',
  'unhandled_exception',
  'unhandled_rejection',
  'session_check_failed',
  'login_failed',
  'logout_failed',
  'node_control_unavailable',
  'node_command_failed',
  'node_rename_failed',
  'updater_unreachable',
  'updater_check_failed',
  'updater_apply_failed',
  'updater_policy_failed',
  'updater_nodes_failed',
  'updater_collaudo_failed',
  'updater_history_failed',
  'identity_unavailable',
  'node_settings_unavailable',
  'node_settings_save_failed',
  'node_inventory_unavailable',
  'node_audio_unavailable',
  'node_audio_update_failed',
  'node_sounds_unavailable',
  'node_sound_play_failed',
  'node_cameras_unavailable',
  'node_camera_photo_failed',
  'node_camera_controls_failed',
  'node_camera_options_failed',
  'node_camera_photos_failed',
  'node_printers_unavailable',
  'node_printer_test_failed',
  'node_printer_remove_failed',
  'node_printer_options_failed',
  'node_printer_discover_failed',
  'node_printer_install_failed',
  'node_printer_add_failed',
  'node_bluetooth_unavailable',
  'node_bluetooth_power_failed',
  'node_bluetooth_scan_failed',
  'node_bluetooth_pair_failed',
  'node_bluetooth_connect_failed',
  'node_bluetooth_disconnect_failed',
  'node_bluetooth_forget_failed',
  'node_bluetooth_prefs_failed',
  'node_display_unavailable',
  'node_avatars_unavailable',
  'node_avatar_upload_failed',
  'node_avatar_activate_failed',
  'node_avatar_remove_failed',
  'node_links_unavailable',
  'node_pairing_code_failed',
  'node_request_approve_failed',
  'node_request_reject_failed',
  'node_unpair_failed',
  'i18n_remote_unavailable',
  'node_board_unavailable',
  'node_board_stroke_failed',
  'node_board_text_failed',
  'node_board_action_failed',
  'node_board_saves_failed',
  'node_board_save_failed',
  'node_board_load_failed',
  'node_board_delete_failed',
  'node_board_printers_failed',
  'node_board_print_failed',
  'node_board_ask_failed',
]);

export const ErrorToastHost: React.FC = () => {
  const { t } = useScopedI18n('shared/errors');
  const [errors, setErrors] = useState<readonly ReportedError[]>([]);

  useEffect(
    () =>
      subscribeErrors((entry) => {
        setErrors((current) => [...current, entry].slice(-VISIBLE_LIMIT));
        window.setTimeout(() => {
          setErrors((current) => current.filter((e) => e.id !== entry.id));
        }, AUTO_DISMISS_MS);
      }),
    [],
  );

  const dismiss = (id: number) => setErrors((current) => current.filter((e) => e.id !== id));

  return (
    <div
      aria-live="assertive"
      className="pointer-events-none fixed inset-x-4 bottom-4 z-[100] flex flex-col items-center gap-2 sm:inset-x-auto sm:right-4 sm:items-end"
    >
      {errors.map((entry) => (
        <div
          key={entry.id}
          role="alert"
          className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border bg-slate-950/95 p-3 text-sm shadow-xl backdrop-blur-xl ${
            entry.severity === 'critical' ? 'border-rose-500/50 text-rose-100' : 'border-amber-400/40 text-amber-50'
          }`}
        >
          <AlertTriangle
            className={`mt-0.5 h-4 w-4 shrink-0 ${entry.severity === 'critical' ? 'text-rose-400' : 'text-amber-300'}`}
            aria-hidden="true"
          />
          <p className="flex-1 leading-snug">{t(KNOWN_CODES.has(entry.code) ? `error_${entry.code}` : 'error_generic')}</p>
          <button
            type="button"
            onClick={() => dismiss(entry.id)}
            aria-label={t('dismiss')}
            className="rounded-md p-1 text-slate-400 transition hover:bg-slate-800 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      ))}
    </div>
  );
};
