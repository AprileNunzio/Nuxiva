import React, { useEffect, useRef, useState } from 'react';
import { DioramaStage } from '../engine/stage';
import type { Diorama } from '../types';

interface ViewportProps {
  readonly diorama: Diorama;
  readonly animate: boolean;
  readonly selected: string;
  readonly onPick: (id: string) => void;
  readonly onSnapshot: (take: () => string) => void;
  readonly unsupported: string;
  readonly lite?: boolean;
}

export const Viewport: React.FC<ViewportProps> = ({ diorama, animate, selected, onPick, onSnapshot, unsupported, lite = false }) => {
  const host = useRef<HTMLDivElement>(null);
  const stage = useRef<DioramaStage | null>(null);
  const [failed, setFailed] = useState(false);
  const pickRef = useRef(onPick);
  pickRef.current = onPick;

  useEffect(() => {
    const element = host.current;
    if (!element) return undefined;
    try {
      const created = new DioramaStage(element, lite);
      created.setPickHandler((id) => pickRef.current(id));
      stage.current = created;
      onSnapshot(() => created.snapshot());
    } catch {
      setFailed(true);
      return undefined;
    }
    return () => {
      stage.current?.dispose();
      stage.current = null;
    };
  }, [onSnapshot, lite]);

  useEffect(() => {
    const current = stage.current;
    if (!current) return;
    current.setBase(diorama.base);
    current.setLook(diorama.look);
    current.sync(diorama.items, animate, diorama.recipes);
  }, [diorama.look, diorama.base, diorama.items, diorama.recipes, animate]);

  useEffect(() => {
    stage.current?.select(selected);
  }, [selected, diorama.items]);

  if (failed) return <div className="flex h-full items-center justify-center bg-slate-100 p-6 text-center text-sm text-slate-600">{unsupported}</div>;
  return <div ref={host} className="h-full w-full cursor-grab overflow-hidden bg-slate-100 active:cursor-grabbing" />;
};
