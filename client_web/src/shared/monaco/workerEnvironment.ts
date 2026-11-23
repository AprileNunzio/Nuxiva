import editorWorker from 'monaco-editor/editor/editor.worker.js?worker&url';
import cssWorker from 'monaco-editor/languages/features/css/css.worker.js?worker&url';
import htmlWorker from 'monaco-editor/languages/features/html/html.worker.js?worker&url';
import jsonWorker from 'monaco-editor/languages/features/json/json.worker.js?worker&url';
import tsWorker from 'monaco-editor/languages/features/typescript/ts.worker.js?worker&url';
import { sameOriginScriptUrl } from './scriptUrl';

export const MONACO_WORKER_POLICY = 'nuxivaMonacoWorker';

const WORKERS: Readonly<Record<string, string>> = Object.freeze({
  css: cssWorker,
  scss: cssWorker,
  less: cssWorker,
  html: htmlWorker,
  handlebars: htmlWorker,
  razor: htmlWorker,
  json: jsonWorker,
  typescript: tsWorker,
  javascript: tsWorker,
});

interface ScriptUrlPolicy {
  createScriptURL(value: string): unknown;
}

interface TrustedTypesHost {
  trustedTypes?: {
    createPolicy(name: string, rules: { createScriptURL(value: string): string }): ScriptUrlPolicy;
  };
}

function createPolicy(): ScriptUrlPolicy | null {
  const factory = (globalThis as TrustedTypesHost).trustedTypes;
  if (!factory) {
    return null;
  }
  return factory.createPolicy(MONACO_WORKER_POLICY, {
    createScriptURL: (value) => sameOriginScriptUrl(value, window.location.origin, window.location.href),
  });
}

let installed = false;

export function installMonacoWorkers(): void {
  if (installed) {
    return;
  }
  installed = true;
  const policy = createPolicy();
  (globalThis as { MonacoEnvironment?: unknown }).MonacoEnvironment = {
    getWorker(_moduleId: string, label: string): Worker {
      const url = WORKERS[label] ?? editorWorker;
      const script = policy ? policy.createScriptURL(url) : sameOriginScriptUrl(url, window.location.origin, window.location.href);
      return new Worker(script as string, { name: label, type: 'module' });
    },
  };
}
