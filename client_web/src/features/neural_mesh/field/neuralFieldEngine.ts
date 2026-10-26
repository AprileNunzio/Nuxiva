import { quadraticPoint } from '../domain/geometry';
import { CORE_COLOR, KIND_COLORS, withAlpha } from '../domain/palette';
import { Point, SynapsePath } from '../domain/types';

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  phase: number;
}

interface Pulse {
  readonly path: SynapsePath;
  readonly speed: number;
  readonly inbound: boolean;
  readonly color: string;
  t: number;
}

const LINK_DISTANCE = 120;
const MAX_PULSES = 140;
const TRAIL_STEPS = 5;

export class NeuralFieldEngine {
  private readonly ctx: CanvasRenderingContext2D;
  private width = 0;
  private height = 0;
  private particles: Particle[] = [];
  private synapses: readonly SynapsePath[] = [];
  private pulses: Pulse[] = [];
  private budget = new Map<string, number>();
  private core: { center: Point; radius: number } = { center: { x: 0, y: 0 }, radius: 0 };
  private frame: number | null = null;
  private lastTime = 0;

  constructor(
    private readonly canvas: HTMLCanvasElement,
    private reducedMotion: boolean,
  ) {
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) {
      throw new Error('canvas_2d_unavailable');
    }
    this.ctx = ctx;
  }

  resize(width: number, height: number, dpr: number): void {
    this.width = width;
    this.height = height;
    this.canvas.width = Math.round(width * dpr);
    this.canvas.height = Math.round(height * dpr);
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.seedParticles();
    this.renderStaticIfIdle();
  }

  setScene(synapses: readonly SynapsePath[], center: Point, coreRadius: number): void {
    this.synapses = synapses;
    this.core = { center, radius: coreRadius };
    const valid = new Set(synapses.map((s) => s.id));
    this.pulses = this.pulses.filter((p) => valid.has(p.path.id));
    this.renderStaticIfIdle();
  }

  setReducedMotion(reduced: boolean): void {
    this.reducedMotion = reduced;
    if (reduced) {
      this.stop();
      this.pulses = [];
      this.draw(0);
    }
  }

  start(): void {
    if (this.reducedMotion || this.frame !== null) {
      this.draw(0);
      return;
    }
    this.lastTime = performance.now();
    this.frame = requestAnimationFrame(this.tick);
  }

  stop(): void {
    if (this.frame !== null) {
      cancelAnimationFrame(this.frame);
      this.frame = null;
    }
  }

  private renderStaticIfIdle(): void {
    if (this.frame === null) {
      this.draw(0);
    }
  }

  private seedParticles(): void {
    const count = Math.round(Math.min(150, Math.max(28, (this.width * this.height) / 11000)));
    this.particles = Array.from({ length: count }, () => ({
      x: Math.random() * this.width,
      y: Math.random() * this.height,
      vx: (Math.random() - 0.5) * 9,
      vy: (Math.random() - 0.5) * 9,
      radius: 0.6 + Math.random() * 1.4,
      phase: Math.random() * Math.PI * 2,
    }));
  }

  private readonly tick = (time: number): void => {
    const dt = Math.min(0.05, (time - this.lastTime) / 1000);
    this.lastTime = time;
    this.advanceParticles(dt);
    this.advancePulses(dt);
    this.draw(time / 1000);
    this.frame = requestAnimationFrame(this.tick);
  };

  private advanceParticles(dt: number): void {
    for (const p of this.particles) {
      p.x = (p.x + p.vx * dt + this.width) % this.width;
      p.y = (p.y + p.vy * dt + this.height) % this.height;
    }
  }

  private advancePulses(dt: number): void {
    for (const path of this.synapses) {
      const accrued = (this.budget.get(path.id) ?? Math.random()) + dt * (0.35 + path.intensity * 1.3);
      if (accrued >= 1 && this.pulses.length < MAX_PULSES) {
        this.pulses.push({
          path,
          speed: 0.45 + path.intensity * 0.45,
          inbound: Math.random() < 0.5,
          color: KIND_COLORS[path.kind],
          t: 0,
        });
        this.budget.set(path.id, accrued - 1);
      } else {
        this.budget.set(path.id, Math.min(accrued, 1));
      }
    }
    for (const pulse of this.pulses) {
      pulse.t += pulse.speed * dt;
    }
    this.pulses = this.pulses.filter((p) => p.t < 1);
  }

  private draw(seconds: number): void {
    const { ctx } = this;
    ctx.clearRect(0, 0, this.width, this.height);
    this.drawCoreAura(seconds);
    this.drawPlexus();
    this.drawParticles(seconds);
    this.drawPulses();
  }

  private drawCoreAura(seconds: number): void {
    const { center, radius } = this.core;
    if (radius <= 0) {
      return;
    }
    const breathe = 1 + Math.sin(seconds * 1.4) * 0.06;
    const gradient = this.ctx.createRadialGradient(center.x, center.y, radius * 0.4, center.x, center.y, radius * 4 * breathe);
    gradient.addColorStop(0, withAlpha(CORE_COLOR, 0.22));
    gradient.addColorStop(0.45, withAlpha('#3b82f6', 0.07));
    gradient.addColorStop(1, 'rgba(0,0,0,0)');
    this.ctx.fillStyle = gradient;
    this.ctx.fillRect(0, 0, this.width, this.height);
  }

  private drawPlexus(): void {
    const { ctx, particles } = this;
    ctx.lineWidth = 0.6;
    for (let i = 0; i < particles.length; i += 1) {
      for (let j = i + 1; j < particles.length; j += 1) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d = Math.hypot(dx, dy);
        if (d < LINK_DISTANCE) {
          ctx.strokeStyle = withAlpha('#38bdf8', (1 - d / LINK_DISTANCE) * 0.11);
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }
  }

  private drawParticles(seconds: number): void {
    const { ctx } = this;
    for (const p of this.particles) {
      ctx.fillStyle = withAlpha('#a5f3fc', 0.25 + 0.35 * (0.5 + 0.5 * Math.sin(seconds * 1.7 + p.phase)));
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  private drawPulses(): void {
    const { ctx } = this;
    for (const pulse of this.pulses) {
      for (let step = TRAIL_STEPS; step >= 0; step -= 1) {
        const t = Math.max(0, pulse.t - step * 0.018);
        const point = quadraticPoint(pulse.path, pulse.inbound ? 1 - t : t);
        const fade = 1 - step / (TRAIL_STEPS + 1);
        const radius = step === 0 ? 3.2 : 2.2 * fade;
        ctx.fillStyle = withAlpha(pulse.color, step === 0 ? 0.95 : 0.45 * fade);
        ctx.beginPath();
        ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }
      const head = quadraticPoint(pulse.path, pulse.inbound ? 1 - pulse.t : pulse.t);
      const glow = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 14);
      glow.addColorStop(0, withAlpha(pulse.color, 0.45));
      glow.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(head.x, head.y, 14, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
