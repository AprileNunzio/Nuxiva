export type ControlScope = 'local' | 'paired' | 'mesh';
export type NodeCommand = 'identify' | 'adapt' | 'restart' | 'update' | 'reboot' | 'setup';

export const KNOWN_COMMANDS: readonly NodeCommand[] = ['identify', 'adapt', 'update', 'setup', 'restart', 'reboot'];
export const DESTRUCTIVE_COMMANDS: ReadonlySet<NodeCommand> = new Set(['restart', 'update', 'reboot', 'setup']);

export interface NodeControl {
  readonly scope: ControlScope;
  readonly commands: readonly NodeCommand[];
  readonly unsupportedModules: readonly string[];
}

export class NodeConsoleError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
  ) {
    super(code);
    this.name = 'NodeConsoleError';
  }
}

const JSON_HEADERS = { Accept: 'application/json', 'Content-Type': 'application/json' };

function nodePath(nodeId: string, suffix: string): string {
  return `/api/v5/nodes/${encodeURIComponent(nodeId)}/${suffix}`;
}

async function detail(response: Response): Promise<string> {
  const payload: unknown = await response.json().catch(() => null);
  const value = typeof payload === 'object' && payload !== null ? (payload as { detail?: unknown }).detail : null;
  return typeof value === 'string' ? value : 'request_failed';
}

export async function fetchNodeControl(nodeId: string, signal: AbortSignal): Promise<NodeControl> {
  const response = await fetch(nodePath(nodeId, 'control'), { headers: { Accept: 'application/json' }, signal });
  if (!response.ok) {
    throw new NodeConsoleError(await detail(response), response.status);
  }
  const payload = (await response.json()) as { scope?: unknown; commands?: unknown; unsupported_modules?: unknown };
  const scope: ControlScope = payload.scope === 'local' || payload.scope === 'paired' ? payload.scope : 'mesh';
  const commands = Array.isArray(payload.commands)
    ? payload.commands.filter((c): c is NodeCommand => KNOWN_COMMANDS.includes(c as NodeCommand))
    : [];
  const unsupportedModules = Array.isArray(payload.unsupported_modules)
    ? payload.unsupported_modules.filter((m): m is string => typeof m === 'string')
    : [];
  return { scope, commands, unsupportedModules };
}

export async function sendNodeCommand(nodeId: string, command: NodeCommand): Promise<'executing' | 'queued'> {
  const response = await fetch(nodePath(nodeId, `commands/${command}`), {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ confirm: DESTRUCTIVE_COMMANDS.has(command) }),
  });
  if (!response.ok) {
    throw new NodeConsoleError(await detail(response), response.status);
  }
  const payload = (await response.json()) as { status?: unknown };
  return payload.status === 'executing' ? 'executing' : 'queued';
}

export async function renameNode(nodeId: string, name: string): Promise<string> {
  const response = await fetch(nodePath(nodeId, 'name'), {
    method: 'PATCH',
    headers: JSON_HEADERS,
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    throw new NodeConsoleError(await detail(response), response.status);
  }
  const payload = (await response.json()) as { name?: unknown };
  return typeof payload.name === 'string' ? payload.name : name;
}
