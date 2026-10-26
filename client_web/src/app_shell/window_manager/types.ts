export type WindowMode = 'floating' | 'maximized' | 'snapped-left' | 'snapped-right' | 'quarter-tl' | 'quarter-tr' | 'quarter-bl' | 'quarter-br';
export interface OSWindowOpenRequest {
  appId: string;
  instanceKey?: string;
  targetNodeId?: string;
  initialPayload?: Record<string, unknown>;
  windowMode?: WindowMode;
}
export interface OSWindow extends OSWindowOpenRequest {
  activeSection?: string;
  title?: string;
  layoutVersion?: number;
  id: string;
  x: number; y: number; width: number; height: number;
  minimized: boolean; pinned: boolean; z: number;
}
export interface ToolbarItem {
  id: string;
  type: 'button' | 'action' | 'search' | 'segmented';
  labelKey?: string; placeholderKey?: string; icon3d?: string;
  options?: string[]; variant?: string; shortcut?: string;
  icon?: string; confirmKey?: string; permissions?: string[];
}
export type ZeroTrustCapability = 'network' | 'filesystem' | 'audio' | 'camera' | 'notifications' | 'system_settings' | (string & {});
export interface WindowConfig {
  defaultWidth?:number;defaultHeight?:number;minWidth?:number;minHeight?:number;
  resizable?:boolean;maximizable?:boolean;singleton?:boolean;mobileMode?:'fullscreen'|'drawer';units?:'px'|'legacy';
}
export interface UIRequirements {
  searchable?:boolean;searchPlaceholderKey?:string;
  tabs?:{id:string;labelKey:string;icon?:string}[];
  actions?:{id:string;labelKey:string;icon?:string;variant?:string;confirmKey?:string;permissions?:string[]}[];
  statusBar?:{showConnectionState?:boolean;showItemCount?:boolean};
}
export interface BreadcrumbItem {
  readonly id: string;
  readonly label: string;
  readonly onClick?: () => void;
}
export interface OSAppContextValue {
  windowId: string; appId: string; nodeId?: string; instanceKey?: string; activeTab?: string; searchQuery: string;
  setActiveTab: (id: string) => void; setNodeId: (id: string) => void; setTitle: (title: string) => void;
  setSearchQuery: (query: string) => void; setStatus: (status: { itemCount?: number; connected?: boolean; details?: string }) => void;
  status: { itemCount?: number; connected?: boolean; details?: string }; openApp: (request: OSWindowOpenRequest) => string;
  breadcrumbs?: readonly BreadcrumbItem[]; setBreadcrumbs?: (crumbs: readonly BreadcrumbItem[]) => void;
  inspectorOpen?: boolean; setInspectorOpen?: (open: boolean | ((prev: boolean) => boolean)) => void;
  selectedId?: string; setSelectedId?: (id: string | undefined) => void;
}
export interface AppManifest {
  id: string; name: string; scope: string; icon3d?: string;
  category?: string; version?: string;
  kind?: 'app' | 'feature' | 'system';
  desktop?: { order?: number };
  launcher?: boolean;
  featureIds?: string[];
  capabilities?:ZeroTrustCapability[];i18nScope?:string;ui?:UIRequirements;
  navigation?: { id: string; labelKey: string; icon?: string }[];
  target?: 'global' | 'node' | 'universal';
  window?: WindowConfig;
  toolbars?: { id: string; items: ToolbarItem[] }[];
}
