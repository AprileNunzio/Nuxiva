import { adminPath } from '../../../shared/http/basePath';
import { asRecord, asString, requestJson } from '../../shared/data/http';
import { Item } from '../render/primitives';

export interface BoardView {
  readonly rev: number;
  readonly items: readonly Item[];
  readonly page: number;
  readonly pages: number;
  readonly aiEnabled: boolean;
  readonly says: string;
}

export interface BoardPrinter {
  readonly id: string;
  readonly name: string;
  readonly type: string;
}

export const SAVE_NAME = /^[\p{L}\p{N} _-]{1,50}$/u;
const MAX_ITEMS = 3000;
const int = (value: unknown, fallback = 0): number => (typeof value === 'number' && Number.isInteger(value) ? value : fallback);

export async function fetchBoard(rev: number, signal?: AbortSignal): Promise<BoardView | null> {
  const raw = asRecord(await requestJson<unknown>(`/api/board?rev=${Math.max(0, Math.floor(rev))}`, { signal }));
  if (raw.same === true) {
    return null;
  }
  return {
    rev: int(raw.rev),
    items: (Array.isArray(raw.items) ? raw.items : [])
      .slice(0, MAX_ITEMS)
      .filter((item): item is Item => typeof item === 'object' && item !== null && !Array.isArray(item)),
    page: Math.max(0, int(raw.page)),
    pages: Math.max(1, int(raw.pages, 1)),
    aiEnabled: raw.ai_enabled !== false,
    says: asString(raw.says, 400) ?? '',
  };
}

const post = (path: string, body: Record<string, unknown> = {}) => requestJson<unknown>(path, { method: 'POST', body: JSON.stringify(body) });

export const sendStroke = (points: readonly (readonly [number, number])[], color: string, width: number, eraser: boolean) =>
  post('/api/board/stroke', { points, color, width, tool: eraser ? 'eraser' : 'pen' });
export const sendText = (text: string, x: number, y: number, color: string) => post('/api/board/text', { text, x, y, size: 40, color });
export const undo = () => post('/api/board/undo');
export const clearBoard = () => post('/api/board/clear');
export const newPage = () => post('/api/board/page/new');
export const switchPage = (page: number) => post('/api/board/page/switch', { page });
export const deletePage = (page: number) => post('/api/board/page/delete', { page });
export const setAi = (enabled: boolean) => post('/api/board/ai/toggle', { enabled });
export const askBoard = (question: string) => post('/api/board/ask', { question });
export const saveBoard = (name: string) => post('/api/board/save', { name });
export const loadBoard = (name: string) => post('/api/board/load', { name });

export async function listSaves(signal?: AbortSignal): Promise<string[]> {
  const raw = asRecord(await requestJson<unknown>('/api/board/list', { signal }));
  return (Array.isArray(raw.boards) ? raw.boards : []).filter((b): b is string => typeof b === 'string' && SAVE_NAME.test(b)).slice(0, 100);
}

export async function deleteSave(name: string): Promise<string[]> {
  const raw = asRecord(await post('/api/board/delete_save', { name }));
  return (Array.isArray(raw.boards) ? raw.boards : []).filter((b): b is string => typeof b === 'string' && SAVE_NAME.test(b));
}

export async function listBoardPrinters(signal?: AbortSignal): Promise<{ printers: BoardPrinter[]; fallback: string }> {
  const raw = asRecord(await requestJson<unknown>('/api/board/printers', { signal }));
  const printers = (Array.isArray(raw.printers) ? raw.printers : []).map(asRecord).flatMap((p) => {
    const id = asString(p.id, 80);
    return id && /^[A-Za-z0-9_.:-]{1,80}$/.test(id) ? [{ id, name: asString(p.name, 80) ?? id, type: asString(p.type, 20) ?? '' }] : [];
  });
  return { printers, fallback: asString(raw.default, 80) ?? printers[0]?.id ?? '' };
}

export const printBoard = (printerId: string) => post('/api/board/print', { printer_id: printerId });
export const PDF_URL = adminPath('/api/board/pdf');
