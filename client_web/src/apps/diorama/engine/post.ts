import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';

const TILT = {
  uniforms: { tDiffuse: { value: null as THREE.Texture | null }, direction: { value: new THREE.Vector2(1, 0) }, resolution: { value: new THREE.Vector2(1, 1) }, focus: { value: 0.5 }, band: { value: 0.2 }, strength: { value: 2 } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform vec2 direction; uniform vec2 resolution; uniform float focus; uniform float band; uniform float strength; varying vec2 vUv;
    void main(){
      float distanceFromFocus = abs(vUv.y - focus);
      float amount = smoothstep(band, band + 0.38, distanceFromFocus) * strength;
      vec2 step = direction / resolution * amount;
      vec4 sum = texture2D(tDiffuse, vUv) * 0.2270270270;
      sum += (texture2D(tDiffuse, vUv + step * 1.3846153846) + texture2D(tDiffuse, vUv - step * 1.3846153846)) * 0.3162162162;
      sum += (texture2D(tDiffuse, vUv + step * 3.2307692308) + texture2D(tDiffuse, vUv - step * 3.2307692308)) * 0.0702702703;
      sum += (texture2D(tDiffuse, vUv + step * 5.0) + texture2D(tDiffuse, vUv - step * 5.0)) * 0.0135135135;
      gl_FragColor = sum;
    }`,
};

const FINISH = {
  uniforms: { tDiffuse: { value: null as THREE.Texture | null }, time: { value: 0 }, vignette: { value: 0.32 }, grain: { value: 0.025 }, aberration: { value: 0.0014 }, warmth: { value: 0.0 }, saturation: { value: 1.08 } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: `
    uniform sampler2D tDiffuse; uniform float time; uniform float vignette; uniform float grain; uniform float aberration; uniform float warmth; uniform float saturation; varying vec2 vUv;
    float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + time) * 43758.5453); }
    void main(){
      vec2 c = vUv - 0.5;
      float edge = dot(c, c);
      vec2 shift = c * aberration * (1.0 + edge * 6.0);
      vec3 col = vec3(texture2D(tDiffuse, vUv + shift).r, texture2D(tDiffuse, vUv).g, texture2D(tDiffuse, vUv - shift).b);
      col *= 1.0 - vignette * smoothstep(0.1, 0.75, edge * 2.0);
      col += (hash(vUv * 1024.0) - 0.5) * grain;
      float luma = dot(col, vec3(0.2126, 0.7152, 0.0722));
      col = mix(vec3(luma), col, saturation);
      col *= vec3(1.0 + warmth * 0.06, 1.0, 1.0 - warmth * 0.08);
      gl_FragColor = vec4(col, 1.0);
    }`,
};

export interface Post {
  readonly composer: EffectComposer;
  readonly bloom: UnrealBloomPass;
  readonly tilt: readonly [ShaderPass, ShaderPass];
  readonly finish: ShaderPass;
  resize(width: number, height: number): void;
}

export function createPost(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera, width: number, height: number): Post {
  const target = new THREE.WebGLRenderTarget(width, height, { type: THREE.HalfFloatType, samples: 4 });
  const composer = new EffectComposer(renderer, target);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(width, height), 0.2, 0.6, 0.9);
  composer.addPass(bloom);
  const horizontal = new ShaderPass(TILT);
  const vertical = new ShaderPass({ ...TILT, uniforms: THREE.UniformsUtils.clone(TILT.uniforms) });
  vertical.uniforms.direction.value.set(0, 1);
  composer.addPass(horizontal);
  composer.addPass(vertical);
  const finish = new ShaderPass(FINISH);
  composer.addPass(finish);
  composer.addPass(new OutputPass());
  const resize = (w: number, h: number) => {
    composer.setSize(w, h);
    for (const pass of [horizontal, vertical]) pass.uniforms.resolution.value.set(w, h);
  };
  resize(width, height);
  return { composer, bloom, tilt: [horizontal, vertical], finish, resize };
}
