import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import type { Base, Item, Look, Recipe } from '../types';
import { buildBase } from './base';
import { buildItem } from './builders';
import type { BuildContext } from './builders/kit';
import { LENSES, LIGHTS } from './looks';
import { createPost, type Post } from './post';
import { bakeEnvironment, createSky, paintSky, sunDirection } from './sky';

const POP_MS = 720;
const MAX_LAMP_LIGHTS = 8;

interface Entry {
  readonly group: THREE.Group;
  readonly signature: string;
  readonly born: number;
  readonly scale: number;
  readonly baseY: number;
  readonly x: number;
  readonly z: number;
  readonly motion: Item['motion'];
  readonly phase: number;
  settled: boolean;
}

const easeOutBack = (t: number) => 1 + 2.70158 * Math.pow(t - 1, 3) + 1.70158 * Math.pow(t - 1, 2);

function release(object: THREE.Object3D): void {
  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh || child instanceof THREE.InstancedMesh)) return;
    child.geometry.dispose();
    const materials = Array.isArray(child.material) ? child.material : [child.material];
    for (const material of materials) {
      if (material.userData.shared) continue;
      (material as THREE.MeshStandardMaterial).map?.dispose();
      material.dispose();
    }
    if (child instanceof THREE.InstancedMesh) child.dispose();
  });
}

export class DioramaStage {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(30, 1, 0.1, 900);
  private readonly controls: OrbitControls;
  private readonly sky = createSky();
  private readonly sun = new THREE.DirectionalLight('#ffffff', 1);
  private readonly hemi = new THREE.HemisphereLight('#ffffff', '#444444', 1);
  private readonly world = new THREE.Group();
  private readonly entries = new Map<string, Entry>();
  private readonly post: Post;
  private readonly marker = new THREE.Box3Helper(new THREE.Box3(), new THREE.Color('#0ea5e9'));
  private readonly raycaster = new THREE.Raycaster();
  private baseGroup: THREE.Group | null = null;
  private environment: THREE.Texture | null = null;
  private frame = 0;
  private last = 0;
  private look: Look | null = null;
  private base: Base | null = null;
  private lensKey = '';
  private goal = { fov: 30, distance: 30 };
  private lamps: THREE.PointLight[] = [];
  private onPick: (id: string) => void = () => undefined;
  private readonly observer: ResizeObserver;

  private lite = false;
  private slow = 0;
  private frames = 0;

  constructor(private readonly container: HTMLElement, lite = false) {
    const { clientWidth: w, clientHeight: h } = container;
    this.renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance', preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(Math.max(1, w), Math.max(1, h));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(this.renderer.domElement);
    this.renderer.domElement.style.touchAction = 'none';
    this.scene.add(this.sky, this.world, this.sun, this.sun.target, this.hemi, this.marker);
    this.marker.visible = false;
    this.camera.position.set(14, 12, 20);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.07;
    this.controls.maxPolarAngle = THREE.MathUtils.degToRad(88);
    this.controls.minPolarAngle = THREE.MathUtils.degToRad(5);
    this.controls.autoRotateSpeed = 0.35;
    this.controls.target.set(0, 0.7, 0);
    this.post = createPost(this.renderer, this.scene, this.camera, Math.max(1, w), Math.max(1, h));
    this.renderer.domElement.addEventListener('pointerdown', this.down);
    this.renderer.domElement.addEventListener('pointerup', this.up);
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(container);
    this.resize();
    if (lite) this.degrade();
    this.loop(0);
  }

  private degrade(): void {
    if (this.lite) return;
    this.lite = true;
    this.renderer.setPixelRatio(1);
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.map?.dispose();
    this.sun.shadow.map = null;
    for (const target of [this.post.composer.renderTarget1, this.post.composer.renderTarget2]) {
      target.samples = 0;
      target.dispose();
    }
    this.resize();
  }

  setPickHandler(handler: (id: string) => void): void {
    this.onPick = handler;
  }

  private downAt = { x: 0, y: 0 };

  private down = (event: PointerEvent) => {
    this.downAt = { x: event.clientX, y: event.clientY };
  };

  private up = (event: PointerEvent) => {
    if (Math.hypot(event.clientX - this.downAt.x, event.clientY - this.downAt.y) > 4) return;
    const rect = this.renderer.domElement.getBoundingClientRect();
    const pointer = new THREE.Vector2(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
    this.raycaster.setFromCamera(pointer, this.camera);
    const hits = this.raycaster.intersectObjects(this.world.children, true);
    for (const hit of hits) {
      let node: THREE.Object3D | null = hit.object;
      while (node && !node.userData.itemId) node = node.parent;
      if (node) {
        this.onPick(node.userData.itemId as string);
        return;
      }
    }
    this.onPick('');
  };

  select(id: string): void {
    const entry = this.entries.get(id);
    if (!entry) {
      this.marker.visible = false;
      return;
    }
    this.marker.box.setFromObject(entry.group);
    this.marker.visible = true;
  }

  setBase(base: Base): void {
    if (this.base && JSON.stringify(this.base) === JSON.stringify(base)) return;
    this.base = base;
    if (this.baseGroup) {
      this.world.remove(this.baseGroup);
      release(this.baseGroup);
    }
    this.baseGroup = buildBase(base, LIGHTS[this.look?.light ?? 'golden_hour'].table);
    this.world.add(this.baseGroup);
    this.fitSun();
    this.lensKey = '';
    if (this.look) this.setLook(this.look);
  }

  private fitSun(): void {
    if (!this.base) return;
    const reach = Math.max(this.base.w, this.base.d) * 0.78;
    const cam = this.sun.shadow.camera;
    cam.left = -reach;
    cam.right = reach;
    cam.top = reach;
    cam.bottom = -reach;
    cam.near = 1;
    cam.far = reach * 6;
    cam.updateProjectionMatrix();
  }

  setLook(look: Look): void {
    const previous = this.look;
    this.look = look;
    const preset = LIGHTS[look.light];
    if (!previous || previous.light !== look.light) {
      paintSky(this.sky, preset);
      this.environment = bakeEnvironment(this.renderer, this.sky, this.environment);
      this.scene.add(this.sky);
      this.scene.environment = this.environment;
      this.sun.color.set(preset.sun);
      this.sun.intensity = preset.sunPower;
      this.sun.castShadow = true;
      this.sun.shadow.mapSize.set(this.lite ? 2048 : 4096, this.lite ? 2048 : 4096);
      this.sun.shadow.bias = -0.0004;
      this.sun.shadow.normalBias = 0.03;
      this.sun.shadow.radius = 3.5;
      this.sun.position.copy(sunDirection(preset).multiplyScalar(Math.max(24, (this.base?.w ?? 22) * 1.4)));
      this.fitSun();
      this.hemi.color.set(preset.hemiSky);
      this.hemi.groundColor.set(preset.hemiGround);
      this.hemi.intensity = preset.hemiPower;
      this.renderer.toneMappingExposure = preset.exposure;
      this.post.bloom.strength = preset.bloom;
      const table = this.baseGroup?.getObjectByName('table') as THREE.Mesh | undefined;
      (table?.material as THREE.MeshStandardMaterial | undefined)?.color.set(preset.table);
      for (const lamp of this.lamps) lamp.intensity = preset.lamps ? (lamp.userData.night as number) : 0;
    }
    this.scene.fog = new THREE.FogExp2(preset.fog, 0.0035 + look.mist * 0.018);
    const lens = LENSES[look.lens];
    const strength = lens.blur * (0.25 + look.blur * 1.2);
    for (const pass of this.post.tilt) {
      pass.uniforms.band.value = lens.band * (1.25 - look.blur * 0.5);
      pass.uniforms.strength.value = strength;
    }
    this.post.finish.uniforms.warmth.value = look.light === 'golden_hour' ? 1 : look.light === 'blue_hour' ? -0.6 : 0;
    const key = `${look.lens}|${look.angle}|${this.base?.w}|${this.base?.d}|${this.camera.aspect.toFixed(1)}`;
    if (key !== this.lensKey) {
      this.lensKey = key;
      const span = Math.max(this.base?.w ?? 22, (this.base?.d ?? 15) * 1.25);
      this.goal = { fov: lens.fov, distance: ((span * lens.fit) / Math.tan(THREE.MathUtils.degToRad(lens.fov / 2))) * Math.max(1, 1.6 / this.camera.aspect) };
      const polar = THREE.MathUtils.degToRad(90 - look.angle);
      const azimuth = THREE.MathUtils.degToRad(previous ? this.controls.getAzimuthalAngle() * 57.3 : 22);
      const d = this.camera.position.distanceTo(this.controls.target) || this.goal.distance;
      this.camera.position.set(Math.sin(polar) * Math.sin(azimuth) * d, Math.cos(polar) * d + 0.7, Math.sin(polar) * Math.cos(azimuth) * d);
    }
    this.controls.autoRotate = look.orbit;
  }

  sync(items: readonly Item[], animate: boolean, recipes: Readonly<Record<string, Recipe>> = {}): void {
    const seen = new Set<string>();
    const ctx: BuildContext = { lamps: { left: MAX_LAMP_LIGHTS } };
    const now = performance.now();
    for (const item of items) {
      seen.add(item.id);
      const signature = JSON.stringify(item);
      const existing = this.entries.get(item.id);
      if (existing?.signature === signature) continue;
      if (existing) {
        this.world.remove(existing.group);
        release(existing.group);
      }
      const group = buildItem(item, ctx, recipes);
      const born = existing || !animate ? now - POP_MS : now;
      const settled = born !== now;
      this.entries.set(item.id, { group, signature, born, scale: item.scale, baseY: item.y, x: item.x, z: item.z, motion: item.motion, phase: item.motion ? Math.abs(item.x * 7.3 + item.z * 3.1) % item.motion.span : 0, settled });
      this.world.add(group);
      if (!settled) group.scale.setScalar(0.001);
    }
    for (const [id, entry] of this.entries) {
      if (seen.has(id)) continue;
      this.world.remove(entry.group);
      release(entry.group);
      this.entries.delete(id);
    }
    this.collectLamps();
  }

  private collectLamps(): void {
    this.lamps = [];
    this.world.traverse((o) => {
      if (o instanceof THREE.PointLight) this.lamps.push(o);
    });
    const on = this.look ? LIGHTS[this.look.light].lamps : 0;
    for (const lamp of this.lamps) lamp.intensity = on ? (lamp.userData.night as number) : 0;
  }

  snapshot(): string {
    this.post.composer.render();
    return this.renderer.domElement.toDataURL('image/png');
  }

  private resize(): void {
    const w = Math.max(1, this.container.clientWidth);
    const h = Math.max(1, this.container.clientHeight);
    this.renderer.setSize(w, h);
    this.post.resize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    if (this.look) this.setLook(this.look);
  }

  private loop = (time: number) => {
    this.frame = requestAnimationFrame(this.loop);
    const raw = (time - this.last) / 1000;
    const dt = Math.min(0.05, raw);
    this.last = time;
    if (!this.lite && this.frames > 6) {
      this.slow = this.slow * 0.92 + raw * 0.08;
      if (this.frames > 50 && this.slow > 0.05) this.degrade();
    }
    this.frames += 1;
    const now = performance.now();
    for (const entry of this.entries.values()) {
      if (entry.motion && entry.settled) {
        const { axis, speed, span } = entry.motion;
        const travelled = (((now / 1000) * speed + entry.phase) % span + span) % span - span / 2;
        if (axis === 'x') entry.group.position.x = entry.x + travelled;
        else entry.group.position.z = entry.z + travelled;
        continue;
      }
      if (entry.settled) continue;
      const t = Math.min(1, (now - entry.born) / POP_MS);
      const e = easeOutBack(t);
      entry.group.scale.setScalar(Math.max(0.001, entry.scale * e));
      entry.group.position.y = entry.baseY + (1 - Math.min(1, e)) * 1.4;
      if (t >= 1) {
        entry.group.position.y = entry.baseY;
        entry.settled = true;
      }
    }
    this.camera.fov += (this.goal.fov - this.camera.fov) * Math.min(1, dt * 4);
    this.camera.updateProjectionMatrix();
    const offset = this.camera.position.clone().sub(this.controls.target);
    const length = offset.length();
    if (Math.abs(length - this.goal.distance) > 0.01 && this.look) {
      offset.setLength(length + (this.goal.distance - length) * Math.min(1, dt * 3));
      this.camera.position.copy(this.controls.target).add(offset);
    }
    this.controls.update();
    this.post.finish.uniforms.time.value = (time % 1000) / 1000;
    this.post.composer.render(dt);
  };

  dispose(): void {
    cancelAnimationFrame(this.frame);
    this.observer.disconnect();
    this.renderer.domElement.removeEventListener('pointerdown', this.down);
    this.renderer.domElement.removeEventListener('pointerup', this.up);
    this.controls.dispose();
    for (const entry of this.entries.values()) release(entry.group);
    if (this.baseGroup) release(this.baseGroup);
    this.environment?.dispose();
    this.post.composer.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
