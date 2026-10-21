const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const ts = require('typescript');

function load(file, dependencies, globals = {}) {
  const module = { exports: {} };
  vm.runInNewContext(ts.transpileModule(readFileSync(resolve(__dirname, '../src/apps/repair_workbench', file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.React },
  }).outputText, {
    module, exports: module.exports, require: name => {
      if (!(name in dependencies)) throw new Error(`Missing test dependency: ${name}`);
      return dependencies[name];
    }, ...globals,
  });
  return module.exports;
}

function hooks() {
  const slots = [], cleanups = [];
  let cursor = 0, pending = [];
  const react = {
    createElement(type, props, ...children) { return { type, props: props || {}, children: children.flat() }; },
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = typeof initial === 'function' ? initial() : initial;
      return [slots[index], value => { slots[index] = typeof value === 'function' ? value(slots[index]) : value; }];
    },
    useRef(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = { current: initial };
      return slots[index];
    },
    useCallback(fn) { cursor++; return fn; },
    useEffect(fn, deps) {
      const index = cursor++;
      const previous = slots[index];
      if (!previous || deps.some((value, i) => value !== previous[i])) {
        slots[index] = deps;
        pending.push(() => { cleanups[index]?.(); cleanups[index] = fn(); });
      }
    },
  };
  react.default = react;
  return { react, render(fn) { cursor = 0; return fn(); },
    effects() { const list = pending; pending = []; list.forEach(fn => fn()); },
    dispose() { cleanups.forEach(fn => fn?.()); },
  };
}

function find(tree, type) {
  if (!tree || typeof tree !== 'object') return undefined;
  if (tree.type === type) return tree;
  for (const child of tree.children || []) { const match = find(child, type); if (match) return match; }
}
const flush = () => new Promise(resolve => setImmediate(resolve));

(async () => {
  const { containRect } = load('videoGeometry.ts', {});
  const landscape = containRect(1000, 1000, 1920, 1080);
  assert.equal(landscape.top, 218.75);
  assert.equal(landscape.height, 562.5);
  const portrait = containRect(1200, 600, 600, 1200);
  assert.equal(portrait.left, 450);
  assert.equal(portrait.width, 300);
  assert.equal(containRect(100, 100, 0, 0).width, 0);

  const mediaHooks = hooks();
  let constraints, stopped = 0;
  const stream = { getTracks: () => [{ stop: () => stopped++ }] };
  const { ARVideoStage } = load('components/ARVideoStage.tsx', {
    react: mediaHooks.react, 'lucide-react': {},
    '../../../shared/http/basePath': { adminPath: url => url },
    '../../../shared/errors/errorBus': { reportError: () => {} },
    '../videoGeometry': { containRect },
  }, {
    navigator: { mediaDevices: { getUserMedia: async input => { constraints = input; return stream; } } },
    window: { setInterval: () => 1, clearInterval: () => {} }, document: { hidden: false },
    ResizeObserver: class { observe() {} disconnect() {} },
  });
  const props = { t: key => key, cameras: [], selectedCameraId: 'usb:bench-camera', cameraName: 'Banco',
    sceneState: 'warmup', popups: [], sessionActive: false, busy: false,
    onSelectCamera: () => {}, onFrameCaptured: () => {}, onTeachComponent: async () => {} };
  const tree = mediaHooks.render(() => ARVideoStage(props));
  const video = find(tree, 'video');
  assert.ok(video, 'the video must exist before webcam permission resolves');
  const element = { srcObject: null };
  video.props.ref.current = element;
  mediaHooks.effects();
  await flush();
  assert.equal(element.srcObject, stream);
  assert.equal(constraints.video.deviceId.exact, 'bench-camera');
  mediaHooks.dispose();
  assert.equal(stopped, 1, 'unmount releases the camera');

  const launchHooks = hooks();
  let tick;
  const opened = [];
  const { useWorkbenchAutoLaunch } = load('hooks/useWorkbenchAutoLaunch.ts', {
    react: launchHooks.react,
    '../../../app_shell/window_manager/WindowStore': { windowStore: { closeAll() {}, openWindow: value => opened.push(value) } },
    '../../../shared/errors/errorBus': { reportError: () => {} },
    '../api': { fetchPendingWorkbenchLaunches: async () => [{ launch_id: 'launch', project_id: 'project', created_at: Date.now() / 1000 }] },
  }, { window: { setInterval: fn => { tick = fn; return 1; }, clearInterval() {} } });
  launchHooks.render(() => useWorkbenchAutoLaunch(true));
  launchHooks.effects();
  tick(); await flush(); tick(); await flush();
  assert.equal(opened.length, 1);
  assert.equal(opened[0].initialPayload.takeover, true);
  assert.equal(opened[0].initialPayload.projectId, 'project');
  launchHooks.dispose();

  const sessionHooks = hooks();
  let analyses = 0, finish;
  const session = { session_id: 'session', project_id: 'project' };
  const { useWorkbenchSession } = load('hooks/useWorkbenchSession.ts', {
    react: sessionHooks.react,
    '../../../shared/errors/errorBus': { reportError: () => {} },
    '../api': {
      fetchCamerasList: async () => [], fetchProjectsList: async () => [],
      startWorkbenchSession: async () => session,
      analyzeWorkbenchFrame: () => { analyses++; return new Promise(resolve => { finish = resolve; }); },
    },
  }, { navigator: {} });
  let state = sessionHooks.render(() => useWorkbenchSession('it', 'Banco', 'Riparazione', 'project'));
  await state.startOrEnsureSession();
  state = sessionHooks.render(() => useWorkbenchSession('it', 'Banco', 'Riparazione', 'project'));
  const first = state.submitFrame('frame', []);
  await state.submitFrame('second-frame', []);
  assert.equal(analyses, 1, 'slow analysis cannot accumulate overlapping frames');
  finish({ session }); await first;
  state.setSelectedCameraId('usb:other-camera');
  state = sessionHooks.render(() => useWorkbenchSession('it', 'Banco', 'Riparazione', 'project'));
  assert.equal(state.session, null, 'camera changes require a new session');
  console.log('Repair workbench: webcam lifecycle, device selection, AR geometry, automatic takeover, launch deduplication and inference backpressure passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
