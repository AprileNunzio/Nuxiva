import React, { useEffect, useRef } from 'react';
import { MeshLayout } from '../domain/types';
import { NeuralFieldEngine } from './neuralFieldEngine';

interface NeuralFieldProps {
  readonly width: number;
  readonly height: number;
  readonly layout: MeshLayout;
  readonly reducedMotion: boolean;
}

export const NeuralField: React.FC<NeuralFieldProps> = ({ width, height, layout, reducedMotion }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<NeuralFieldEngine | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }
    const engine = new NeuralFieldEngine(canvas, reducedMotion);
    engineRef.current = engine;
    const onVisibility = () => (document.hidden ? engine.stop() : engine.start());
    document.addEventListener('visibilitychange', onVisibility);
    engine.start();
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      engine.stop();
      engineRef.current = null;
    };
  }, []);

  useEffect(() => {
    engineRef.current?.setReducedMotion(reducedMotion);
    if (!reducedMotion && !document.hidden) {
      engineRef.current?.start();
    }
  }, [reducedMotion]);

  useEffect(() => {
    if (width > 0 && height > 0) {
      engineRef.current?.resize(width, height, Math.min(2, window.devicePixelRatio || 1));
    }
  }, [width, height]);

  useEffect(() => {
    engineRef.current?.setScene(layout.synapses, layout.center, layout.coreRadius);
  }, [layout]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0"
      style={{ width, height }}
    />
  );
};
