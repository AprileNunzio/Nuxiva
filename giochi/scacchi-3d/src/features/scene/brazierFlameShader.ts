import * as THREE from 'three';

export interface FlameConfig {
  baseColor: [number, number, number];
  midColor: [number, number, number];
  tipColor: [number, number, number];
  strength: number;
  opacity: number;
  zMin: number;
  zMax: number;
  layerSeed: number;
}

export class BrazierFlameShader {
  public static createSoftGlowTexture(): THREE.CanvasTexture {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(128, 128, 2, 128, 128, 128);
    grad.addColorStop(0.0, 'rgba(255, 226, 155, 0.88)');
    grad.addColorStop(0.18, 'rgba(255, 154, 52, 0.50)');
    grad.addColorStop(0.45, 'rgba(255, 92, 16, 0.18)');
    grad.addColorStop(0.75, 'rgba(210, 48, 4, 0.04)');
    grad.addColorStop(1.0, 'rgba(0, 0, 0, 0.0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 256, 256);
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    return tex;
  }

  public static stripIcosphereSparks(geometry: THREE.BufferGeometry): void {
    if (!geometry || !geometry.attributes || !geometry.attributes.position) return;
    const pos = geometry.attributes.position;
    if (geometry.index) {
      const idx = geometry.index.array;
      for (let i = 0; i < idx.length; i += 3) {
        const y0 = pos.getY(idx[i]);
        const y1 = pos.getY(idx[i + 1]);
        const y2 = pos.getY(idx[i + 2]);
        if (Math.min(y0, y1, y2) > 1.25) {
          idx[i] = 0;
          idx[i + 1] = 0;
          idx[i + 2] = 0;
        }
      }
      geometry.index.needsUpdate = true;
    }
  }

  public static createFlameMaterial(cfg: FlameConfig, uniformsTracker: Record<string, { value: unknown }>[]): THREE.ShaderMaterial {
    const uniforms = {
      uTime: { value: 0 },
      uZMin: { value: cfg.zMin },
      uZMax: { value: cfg.zMax },
      uLayerSeed: { value: cfg.layerSeed },
      uStrength: { value: cfg.strength },
      uOpacity: { value: cfg.opacity },
      uBaseColor: { value: new THREE.Color(...cfg.baseColor) },
      uMidColor: { value: new THREE.Color(...cfg.midColor) },
      uTipColor: { value: new THREE.Color(...cfg.tipColor) }
    };
    uniformsTracker.push(uniforms);

    return new THREE.ShaderMaterial({
      uniforms,
      vertexShader: `
        uniform float uTime;
        uniform float uZMin;
        uniform float uZMax;
        uniform float uLayerSeed;
        varying vec3 vLocalPos;
        varying vec3 vWorldPos;
        varying vec3 vWorldNormal;
        varying float vHeightNorm;

        void main() {
          vec3 pos = position;
          float h = clamp((pos.y - uZMin) / max(0.01, uZMax - uZMin), 0.0, 1.0);
          vHeightNorm = h;
          vec2 bCenter = vec2(sign(pos.x) * 3.65, 0.65);
          vec2 relXZ = vec2(pos.x, pos.z) - bCenter;
          float tonguePhase = relXZ.x * 14.0 + relXZ.y * 12.0 + uLayerSeed * 1.9;
          float sway = pow(h, 1.05);

          float waveX = sin(pos.y * 4.6 - uTime * 6.4 + tonguePhase) * 0.088
                      + cos(pos.y * 8.2 - uTime * 9.8 + tonguePhase * 1.35) * 0.048;
          float waveZ = cos(pos.y * 4.3 - uTime * 5.9 + tonguePhase * 1.15) * 0.088
                      + sin(pos.y * 7.8 - uTime * 9.1 + tonguePhase * 0.85) * 0.048;

          float twistAngle = sin(uTime * 4.2 + pos.y * 4.5 + uLayerSeed) * 0.30 * sway;
          float cA = cos(twistAngle);
          float sA = sin(twistAngle);
          vec2 twistedXZ = vec2(relXZ.x * cA - relXZ.y * sA, relXZ.x * sA + relXZ.y * cA);
          float radialPulse = 1.0 + sin(uTime * 5.2 - h * 4.0 + tonguePhase) * 0.14 * sway;

          pos.x = bCenter.x + twistedXZ.x * radialPulse + waveX * sway;
          pos.z = bCenter.y + twistedXZ.y * radialPulse + waveZ * sway;

          float lickStretch = 1.0 + (
            sin(uTime * 5.8 + tonguePhase * 1.3) * 0.22 +
            cos(uTime * 9.2 - tonguePhase * 0.9) * 0.12
          ) * smoothstep(0.05, 0.85, h);
          pos.y = uZMin + (pos.y - uZMin) * lickStretch;

          vLocalPos = pos;
          vec4 worldPosition = modelMatrix * vec4(pos, 1.0);
          vWorldPos = worldPosition.xyz;
          vWorldNormal = normalize(mat3(modelMatrix) * normal);
          gl_Position = projectionMatrix * viewMatrix * worldPosition;
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform float uStrength;
        uniform float uOpacity;
        uniform vec3 uBaseColor;
        uniform vec3 uMidColor;
        uniform vec3 uTipColor;
        varying vec3 vLocalPos;
        varying vec3 vWorldPos;
        varying vec3 vWorldNormal;
        varying float vHeightNorm;

        float hash3(vec3 p) {
          p = fract(p * vec3(443.897, 441.423, 437.195));
          p += dot(p, p.yzx + 19.19);
          return fract((p.x + p.y) * p.z);
        }

        float noise3(vec3 p) {
          vec3 i = floor(p);
          vec3 f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          return mix(
            mix(
              mix(hash3(i + vec3(0.0, 0.0, 0.0)), hash3(i + vec3(1.0, 0.0, 0.0)), f.x),
              mix(hash3(i + vec3(0.0, 1.0, 0.0)), hash3(i + vec3(1.0, 1.0, 0.0)), f.x),
              f.y
            ),
            mix(
              mix(hash3(i + vec3(0.0, 0.0, 1.0)), hash3(i + vec3(1.0, 0.0, 1.0)), f.x),
              mix(hash3(i + vec3(0.0, 1.0, 1.0)), hash3(i + vec3(1.0, 1.0, 1.0)), f.x),
              f.y
            ),
            f.z
          );
        }

        void main() {
          float h = clamp(vHeightNorm, 0.0, 1.0);
          vec3 V = normalize(cameraPosition - vWorldPos);
          vec3 N = normalize(vWorldNormal);
          float facing = clamp(abs(dot(N, V)), 0.0, 1.0);
          float powFacing = pow(facing, 2.25);

          float n1 = noise3(vec3(vLocalPos.x * 5.4, vLocalPos.y * 4.8 - uTime * 6.8, vLocalPos.z * 5.4));
          float n2 = noise3(vec3(vLocalPos.x * 10.2 + 1.9, vLocalPos.y * 8.5 - uTime * 10.5, vLocalPos.z * 10.2));
          float shimmer = mix(n1, n2, 0.45);
          float erodedH = clamp(h + (shimmer - 0.48) * 0.42 * smoothstep(0.08, 0.85, h), 0.0, 1.0);
          float heatCoord = clamp(erodedH + (1.0 - facing) * 0.36 + (shimmer - 0.5) * 0.22, 0.0, 1.0);
          vec3 col = mix(uBaseColor, uMidColor, smoothstep(0.0, 0.45, heatCoord));
          col = mix(col, uTipColor, smoothstep(0.45, 0.90, heatCoord));

          float zAlpha = mix(0.96, 0.72, smoothstep(0.0, 0.68, erodedH)) * (1.0 - smoothstep(0.64, 0.98, erodedH));
          float baseSoft = smoothstep(0.0, 0.06, h);
          float flickerPulse = 0.76 + 0.48 * shimmer;
          float alpha = clamp(zAlpha * baseSoft * powFacing * uOpacity * flickerPulse, 0.0, 1.0);
          if (alpha < 0.004) discard;
          gl_FragColor = vec4(col * uStrength, alpha);
        }
      `,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide
    });
  }
}
