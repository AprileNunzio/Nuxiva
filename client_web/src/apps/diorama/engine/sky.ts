import * as THREE from 'three';
import type { LightPreset } from './looks';

const VERTEX = 'varying vec3 vDir; void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }';
const FRAGMENT = `
varying vec3 vDir;
uniform vec3 top; uniform vec3 horizon; uniform vec3 ground; uniform vec3 sunColor; uniform vec3 sunDir;
void main(){
  float h = vDir.y;
  vec3 sky = mix(horizon, top, pow(clamp(h, 0.0, 1.0), 0.55));
  vec3 low = mix(horizon, ground, pow(clamp(-h, 0.0, 1.0), 0.45));
  vec3 base = h >= 0.0 ? sky : low;
  float glowCore = pow(max(dot(normalize(vDir), sunDir), 0.0), 220.0) * 6.0;
  float glowHalo = pow(max(dot(normalize(vDir), sunDir), 0.0), 7.0) * 0.1;
  gl_FragColor = vec4(base + sunColor * (glowCore + glowHalo), 1.0);
}`;

export function sunDirection(preset: LightPreset): THREE.Vector3 {
  const el = THREE.MathUtils.degToRad(preset.elevation);
  const az = THREE.MathUtils.degToRad(preset.azimuth);
  return new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), Math.cos(az) * Math.cos(el)).normalize();
}

export function createSky(): THREE.Mesh<THREE.SphereGeometry, THREE.ShaderMaterial> {
  const material = new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false, vertexShader: VERTEX, fragmentShader: FRAGMENT,
    uniforms: { top: { value: new THREE.Color() }, horizon: { value: new THREE.Color() }, ground: { value: new THREE.Color() }, sunColor: { value: new THREE.Color() }, sunDir: { value: new THREE.Vector3(0, 1, 0) } },
  });
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(400, 32, 16), material);
  mesh.frustumCulled = false;
  return mesh;
}

export function paintSky(sky: THREE.Mesh<THREE.SphereGeometry, THREE.ShaderMaterial>, preset: LightPreset): void {
  const u = sky.material.uniforms;
  u.top.value.set(preset.skyTop);
  u.horizon.value.set(preset.skyHorizon);
  u.ground.value.set(preset.skyGround);
  u.sunColor.value.set(preset.sun);
  u.sunDir.value.copy(sunDirection(preset));
}

export function bakeEnvironment(renderer: THREE.WebGLRenderer, sky: THREE.Mesh, previous: THREE.Texture | null): THREE.Texture {
  const generator = new THREE.PMREMGenerator(renderer);
  const probe = new THREE.Scene();
  probe.add(sky);
  const target = generator.fromScene(probe, 0, 0.1, 1000);
  probe.remove(sky);
  generator.dispose();
  previous?.dispose();
  return target.texture;
}
