import * as THREE from 'three';

export type WeatherType = 'CLEAR' | 'RAIN' | 'SNOW' | 'THUNDERSTORM' | 'NIGHT_NEON';

export class WeatherEffectsBuilder {
  private rainParticles: THREE.Points | null = null;
  private snowParticles: THREE.Points | null = null;
  private flashLight: THREE.PointLight | null = null;
  private rainCount = 1200;
  private snowCount = 600;

  
  constructor(private scene: THREE.Scene) {}

  public applyWeather(type: WeatherType): void {
    this.cleanup();

    if (type === 'RAIN' || type === 'THUNDERSTORM') {
      this.createRain(type === 'THUNDERSTORM');
    } else if (type === 'SNOW') {
      this.createSnow();
    }
  }

  private createRain(isThunder: boolean): void {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(this.rainCount * 3);

    for (let i = 0; i < this.rainCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 16;
      positions[i * 3 + 1] = Math.random() * 12 + 1;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 16;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const mat = new THREE.PointsMaterial({
      color: 0x38bdf8,
      size: 0.12,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending
    });

    this.rainParticles = new THREE.Points(geo, mat);
    this.rainParticles.name = "weather_rain";
    this.scene.add(this.rainParticles);

    if (isThunder) {
      this.flashLight = new THREE.PointLight(0xffffff, 0, 40);
      this.flashLight.position.set(0, 10, 0);
      this.scene.add(this.flashLight);
    }
  }

  private createSnow(): void {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(this.snowCount * 3);

    for (let i = 0; i < this.snowCount; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 18;
      positions[i * 3 + 1] = Math.random() * 10 + 1;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 18;
    }

    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const mat = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.18,
      transparent: true,
      opacity: 0.9
    });

    this.snowParticles = new THREE.Points(geo, mat);
    this.snowParticles.name = "weather_snow";
    this.scene.add(this.snowParticles);
  }

  public update(delta: number): void {
    if (this.rainParticles) {
      const positions = this.rainParticles.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < this.rainCount; i++) {
        positions[i * 3 + 1] -= delta * 18.0; 
        if (positions[i * 3 + 1] < 0) {
          positions[i * 3 + 1] = 12 + Math.random() * 2;
        }
      }
      this.rainParticles.geometry.attributes.position.needsUpdate = true;

      if (this.flashLight) {
        if (Math.random() < 0.015) {
          this.flashLight.intensity = 5.0 + Math.random() * 5.0;
        } else {
          this.flashLight.intensity = Math.max(0, this.flashLight.intensity - delta * 15.0);
        }
      }
    }

    if (this.snowParticles) {
      const positions = this.snowParticles.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < this.snowCount; i++) {
        positions[i * 3 + 1] -= delta * 2.0; 
        positions[i * 3] += Math.sin(positions[i * 3 + 1] * 0.5) * delta * 0.4; 
        if (positions[i * 3 + 1] < 0) {
          positions[i * 3 + 1] = 10;
        }
      }
      this.snowParticles.geometry.attributes.position.needsUpdate = true;
    }
  }

  public cleanup(): void {
    if (this.rainParticles) {
      this.scene.remove(this.rainParticles);
      this.rainParticles.geometry.dispose();
      this.rainParticles = null;
    }
    if (this.snowParticles) {
      this.scene.remove(this.snowParticles);
      this.snowParticles.geometry.dispose();
      this.snowParticles = null;
    }
    if (this.flashLight) {
      this.scene.remove(this.flashLight);
      this.flashLight = null;
    }
  }
}
