import { Bluetooth, Gamepad2, Headphones, Headset, Joystick, Keyboard, Laptop, LucideIcon, Mic, Mouse, Smartphone, Speaker, Watch } from 'lucide-react';
import { DeviceKind } from './model';

const ICONS: Readonly<Record<DeviceKind, LucideIcon>> = {
  speaker: Speaker,
  headphones: Headphones,
  headset: Headset,
  microphone: Mic,
  keyboard: Keyboard,
  mouse: Mouse,
  gamepad: Gamepad2,
  joystick: Joystick,
  phone: Smartphone,
  computer: Laptop,
  wearable: Watch,
  other: Bluetooth,
};

export const kindIcon = (kind: DeviceKind): LucideIcon => ICONS[kind];
