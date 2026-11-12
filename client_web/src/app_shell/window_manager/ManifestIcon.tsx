import React from 'react';
import { Circle, Download, RefreshCw, Plus, Power, Layers, Activity, Lock, Network, Settings2, FileText, ShieldAlert, Search, Trash2, Save, Upload } from 'lucide-react';
const icons:Record<string,React.ElementType>={download:Download,'refresh-cw':RefreshCw,plus:Plus,power:Power,layers:Layers,activity:Activity,lock:Lock,network:Network,settings:Settings2,'file-text':FileText,'shield-alert':ShieldAlert,search:Search,trash:Trash2,save:Save,upload:Upload};
export function ManifestIcon({name}:{name?:string}) { const Icon=name?icons[name]||Circle:Circle;return <Icon aria-hidden="true"/>; }
