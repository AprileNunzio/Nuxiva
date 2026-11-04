import { asRecord, asString, requestJson } from '../../shared/data/http';

export const PRINTER_TYPES = ['laser_2d', 'inkjet_2d', '3d', 'engraver', 'virtual_pdf'] as const;
export type PrinterType = (typeof PRINTER_TYPES)[number];
export const PAPERS = ['A4', 'A3', 'A5', 'Letter', 'Legal'] as const;
export const ORIENTATIONS = ['portrait', 'landscape'] as const;
export const QUALITIES = ['draft', 'normal', 'high'] as const;

export interface PrinterOptions {
  readonly paper: string;
  readonly orientation: string;
  readonly quality: string;
  readonly color: boolean;
  readonly duplex: boolean;
  readonly copies: number;
  readonly laser_power: number;
  readonly laser_feed: number;
  readonly nozzle_temp: number;
  readonly bed_temp: number;
}

export interface Printer {
  readonly id: string;
  readonly name: string;
  readonly type: PrinterType;
  readonly connection: string;
  readonly address: string | null;
  readonly custom: boolean;
  readonly isDefault: boolean;
  readonly options: PrinterOptions;
}

export interface PrinterList {
  readonly printers: readonly Printer[];
  readonly canInstall: boolean;
}

export type ProbeState = 'ready' | 'busy' | 'offline' | 'unknown';

export interface DiscoveredDevice {
  readonly uri: string;
  readonly label: string;
  readonly source: string;
}

export interface NewPrinter {
  readonly name: string;
  readonly type: Exclude<PrinterType, 'virtual_pdf'>;
  readonly connection: 'network' | 'usb';
  readonly address: string;
  readonly port: number;
  readonly api_key: string;
}

const num = (value: unknown, fallback: number): number => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);
const ID = /^[A-Za-z0-9_.:-]{1,80}$/;

function parseOptions(value: unknown): PrinterOptions {
  const o = asRecord(value);
  return {
    paper: asString(o.paper, 10) ?? 'A4',
    orientation: asString(o.orientation, 12) ?? 'portrait',
    quality: asString(o.quality, 10) ?? 'normal',
    color: o.color !== false,
    duplex: o.duplex === true,
    copies: num(o.copies, 1),
    laser_power: num(o.laser_power, 400),
    laser_feed: num(o.laser_feed, 1200),
    nozzle_temp: num(o.nozzle_temp, 205),
    bed_temp: num(o.bed_temp, 60),
  };
}

function parsePrinter(value: unknown): Printer | null {
  const p = asRecord(value);
  const id = asString(p.id, 80);
  const type = PRINTER_TYPES.find((t) => t === p.type);
  if (!id || !ID.test(id) || !type) {
    return null;
  }
  return {
    id,
    name: asString(p.name, 80) ?? id,
    type,
    connection: asString(p.connection, 16) ?? 'system',
    address: asString(p.address, 200),
    custom: p.custom === true,
    isDefault: p.nuxiva_default === true,
    options: parseOptions(p.options),
  };
}

const path = (id: string, suffix: string): string => `/api/printers/${encodeURIComponent(id)}/${suffix}`;

export async function fetchPrinters(signal?: AbortSignal): Promise<PrinterList> {
  const raw = asRecord(await requestJson<unknown>('/api/printers/list', { signal }));
  return {
    printers: (Array.isArray(raw.printers) ? raw.printers : []).map(parsePrinter).filter((p): p is Printer => p !== null),
    canInstall: raw.can_install === true,
  };
}

export async function probePrinter(id: string): Promise<ProbeState> {
  const raw = asRecord(await requestJson<unknown>(path(id, 'probe'), { method: 'POST' }));
  return raw.state === 'ready' || raw.state === 'busy' || raw.state === 'offline' ? raw.state : 'unknown';
}

export async function saveOptions(id: string, options: PrinterOptions, makeDefault: boolean): Promise<void> {
  await requestJson(path(id, 'options'), { method: 'PUT', body: JSON.stringify({ ...options, nuxiva_default: makeDefault }) });
}

export async function printTestPage(id: string): Promise<string> {
  const raw = asRecord(await requestJson<unknown>(path(id, 'test'), { method: 'POST' }));
  return asString(raw.message, 200) ?? '';
}

export async function discoverPrinters(): Promise<DiscoveredDevice[]> {
  const raw = asRecord(await requestJson<unknown>('/api/printers/discover', { method: 'POST' }));
  return (Array.isArray(raw.devices) ? raw.devices : [])
    .map(asRecord)
    .map((d) => ({ uri: asString(d.uri, 300) ?? '', label: asString(d.label, 160) ?? '', source: asString(d.source, 10) ?? '' }))
    .filter((d) => d.uri.includes('://'));
}

export async function installPrinter(uri: string, queue: string): Promise<void> {
  await requestJson('/api/printers/install', { method: 'POST', body: JSON.stringify({ uri, queue }) });
}

export async function addPrinter(printer: NewPrinter): Promise<void> {
  await requestJson('/api/printers/add', { method: 'POST', body: JSON.stringify(printer) });
}

export async function removePrinter(id: string): Promise<void> {
  await requestJson('/api/printers/remove', { method: 'POST', body: JSON.stringify({ id }) });
}
