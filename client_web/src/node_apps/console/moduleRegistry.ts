import React from 'react';
import { ControlScope } from './data/nodeConsoleApi';
import {
  Activity,
  Bluetooth,
  Camera,
  Cpu,
  Edit3,
  LucideIcon,
  Mic,
  Monitor,
  Network,
  Printer,
  Smartphone,
  Volume2,
} from 'lucide-react';
import AudioView from '../audio';
import BluetoothView from '../bluetooth';
import BrainView from '../brain';
import CameraView from '../camera';
import ClientLinkView from '../client_link';
import ConnectionsView from '../connections';
import DisplayView from '../display';
import MicView from '../mic';
import PrintersView from '../printers';
import TaskManagerView from '../task_manager';
import WhiteboardView from '../whiteboard';

export interface NodeModule {
  readonly id: string;
  readonly icon: LucideIcon;
  readonly component: React.FC<{ nodeId?: string; scope?: ControlScope }>;
}

export const NODE_MODULES: readonly NodeModule[] = [
  { id: 'brain', icon: Cpu, component: BrainView },
  { id: 'task_manager', icon: Activity, component: TaskManagerView },
  { id: 'connections', icon: Network, component: ConnectionsView },
  { id: 'audio', icon: Volume2, component: AudioView },
  { id: 'mic', icon: Mic, component: MicView },
  { id: 'camera', icon: Camera, component: CameraView },
  { id: 'printers', icon: Printer, component: PrintersView },
  { id: 'bluetooth', icon: Bluetooth, component: BluetoothView },
  { id: 'display', icon: Monitor, component: DisplayView },
  { id: 'whiteboard', icon: Edit3, component: WhiteboardView },
  { id: 'client_link', icon: Smartphone, component: ClientLinkView },
];
