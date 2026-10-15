import { Gamepad2, Headphones, Keyboard, Laptop, LucideIcon, Mic, Mouse, Smartphone, Speaker, Bluetooth } from 'lucide-react';
import { useScopedI18n } from '../../shared/i18n/useScopedI18n';

export function useBluetoothI18n() {
  return useScopedI18n('node_apps/bluetooth');
}

const ICONS: Readonly<Record<string, LucideIcon>> = {
  'audio-headset': Headphones,
  'audio-headphones': Headphones,
  'audio-card': Speaker,
  'input-microphone': Mic,
  phone: Smartphone,
  computer: Laptop,
  'input-keyboard': Keyboard,
  'input-mouse': Mouse,
  'input-gaming': Gamepad2,
};

export const iconFor = (icon: string): LucideIcon => ICONS[icon] ?? Bluetooth;
export const kindKey = (icon: string): string => (icon in ICONS ? `kind_${icon.replace('-', '_')}` : 'kind_device');

export const fieldClass =
  'rounded-xl border border-slate-700 bg-slate-950/70 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400/70 focus-visible:ring-2 focus-visible:ring-cyan-400/40';
