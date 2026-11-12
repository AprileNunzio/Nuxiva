import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

interface Props {
  readonly category: string;
  readonly value?: string;
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

const SUPPORTED = new Set(['capacitor', 'resistor', 'ic', 'microcontroller', 'opamp', 'regulator']);

/** Generic educational shapes only: no inferred dimensions or observed package claims. */
export const ComponentPreview3D: React.FC<Props> = ({ category, value, t }) => {
  const host = useRef<HTMLDivElement>(null);
  const [unavailable, setUnavailable] = useState(false);
  const supported = SUPPORTED.has(category);
  useEffect(() => {
    setUnavailable(false);
    if (!host.current || !supported) return;
    const container = host.current;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
    catch { setUnavailable(true); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(Math.max(container.clientWidth, 160), 150);
    container.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, Math.max(container.clientWidth, 160) / 150, 0.1, 30);
    camera.position.set(0, 1.5, 6);
    camera.lookAt(0, 0, 0);
    scene.add(new THREE.HemisphereLight(0xe0f2fe, 0x334155, 2.6));
    const light = new THREE.DirectionalLight(0xffffff, 3);
    light.position.set(3, 4, 5);
    scene.add(light);
    const component = new THREE.Group();
    const geometries: THREE.BufferGeometry[] = [];
    const materials: THREE.Material[] = [];
    const mesh = (geometry: THREE.BufferGeometry, color: number, x = 0, y = 0, z = 0) => {
      geometries.push(geometry);
      const material = new THREE.MeshStandardMaterial({ color, metalness: color === 0xaab7c4 ? 0.8 : 0.15, roughness: 0.4 });
      materials.push(material);
      const item = new THREE.Mesh(geometry, material);
      item.position.set(x, y, z);
      component.add(item);
      return item;
    };
    if (category === 'capacitor') {
      mesh(new THREE.CylinderGeometry(0.5, 0.5, 1.25, 32), 0x2563eb, 0, 0.25);
      mesh(new THREE.CylinderGeometry(0.46, 0.46, 0.03, 32), 0xaab7c4, 0, 0.89);
      [-0.24, 0.24].forEach((x) => mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.8, 8), 0xaab7c4, x, -0.75));
    } else if (category === 'resistor') {
      mesh(new THREE.CylinderGeometry(0.27, 0.27, 1.4, 24), 0xd8bd8a).rotation.z = Math.PI / 2;
      [-0.42, -0.16, 0.1, 0.42].forEach((x, i) => {
        mesh(new THREE.CylinderGeometry(0.278, 0.278, 0.08, 24), [0x895d36, 0x111111, 0xdc2626, 0xd4af37][i], x).rotation.z = Math.PI / 2;
      });
      [-1.05, 1.05].forEach((x) => { mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.8, 8), 0xaab7c4, x).rotation.z = Math.PI / 2; });
    } else {
      mesh(new THREE.BoxGeometry(1.5, 0.35, 0.85), 0x18202c);
      [-1, 1].forEach((side) => [-0.55, -0.18, 0.18, 0.55].forEach((x) => mesh(new THREE.BoxGeometry(0.07, 0.16, 0.45), 0xaab7c4, x, -0.15, side * 0.55)));
      mesh(new THREE.SphereGeometry(0.06, 12, 8), 0x94a3b8, -0.55, 0.18, 0.22);
    }
    component.rotation.set(0.2, 0.5, 0);
    scene.add(component);
    const render = () => renderer.render(scene, camera);
    render();
    let previous: { x: number; y: number } | undefined;
    const down = (event: PointerEvent) => {
      previous = { x: event.clientX, y: event.clientY };
      renderer.domElement.setPointerCapture(event.pointerId);
    };
    const move = (event: PointerEvent) => {
      if (!previous) return;
      component.rotation.y += (event.clientX - previous.x) * 0.015;
      component.rotation.x += (event.clientY - previous.y) * 0.015;
      previous = { x: event.clientX, y: event.clientY };
      render();
    };
    const up = () => { previous = undefined; };
    renderer.domElement.style.touchAction = 'none';
    renderer.domElement.addEventListener('pointerdown', down);
    renderer.domElement.addEventListener('pointermove', move);
    renderer.domElement.addEventListener('pointerup', up);
    renderer.domElement.addEventListener('pointercancel', up);
    const observer = new ResizeObserver(() => {
      const width = Math.max(container.clientWidth, 160);
      renderer.setSize(width, 150);
      camera.aspect = width / 150;
      camera.updateProjectionMatrix();
      render();
    });
    observer.observe(container);
    return () => {
      observer.disconnect();
      geometries.forEach((geometry) => geometry.dispose());
      materials.forEach((material) => material.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [category, supported]);

  return <figure className="mt-2 rounded-lg border border-slate-700 bg-slate-950 p-2">
    {supported && !unavailable ? <div ref={host} role="img" aria-label={t('component_3d_title')} className="h-[150px] w-full cursor-grab" /> :
      <p className="text-slate-400">{t('component_3d_unavailable')}</p>}
    <figcaption className="text-[10px] leading-relaxed text-slate-400">
      {value && <span className="block text-slate-200">{value}</span>}
      {t('component_3d_illustrative')}
      {supported && !unavailable && <span className="block">{t('component_3d_rotate')}</span>}
    </figcaption>
  </figure>;
};
