import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { useStudioI18n } from '../scope';
import type { Workpiece3DData } from '../types';

interface Workpiece3DModalProps {
  isOpen: boolean;
  onClose: () => void;
  workpiece?: Workpiece3DData | null;
}

export const Workpiece3DModal: React.FC<Workpiece3DModalProps> = ({
  isOpen,
  onClose,
  workpiece,
}) => {
  const { t } = useStudioI18n();
  const containerRef = useRef<HTMLDivElement>(null);
  const [wireframe, setWireframe] = useState(false);
  const [showAxes, setShowAxes] = useState(true);
  const [isRotating, setIsRotating] = useState(true);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const meshRef = useRef<THREE.Mesh | null>(null);
  const axesRef = useRef<THREE.AxesHelper | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);

  const title = workpiece?.title || t('work3d_default');
  const dimensions = workpiece?.dimensions_mm || [60, 90, 30];
  const material = workpiece?.material || t('w3d_material_default');
  const tolerance = workpiece?.tolerance_mm ?? 0.15;
  const kerf = workpiece?.kerf_mm ?? 0.14;

  useEffect(() => {
    if (!isOpen || !containerRef.current) return;

    const container = containerRef.current;
    let animationFrameId: number;

    const width = container.clientWidth || 640;
    const height = container.clientHeight || 420;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x020617);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(120, 100, 150);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      return;
    }
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    container.replaceChildren();
    container.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 1.8);
    dirLight1.position.set(100, 120, 80);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xa855f7, 1.2);
    dirLight2.position.set(-80, -60, -80);
    scene.add(dirLight2);

    const grid = new THREE.GridHelper(200, 20, 0x0284c7, 0x1e293b);
    grid.position.y = -dimensions[2] / 2;
    scene.add(grid);

    const axes = new THREE.AxesHelper(60);
    axesRef.current = axes;
    scene.add(axes);

    const group = new THREE.Group();
    const [w, l, h] = dimensions;
    const geometry = new THREE.BoxGeometry(w, h, l, 4, 4, 4);
    const mat = new THREE.MeshStandardMaterial({
      color: 0x06b6d4,
      metalness: 0.35,
      roughness: 0.25,
      wireframe,
    });
    const mainMesh = new THREE.Mesh(geometry, mat);
    group.add(mainMesh);

    const cutoutGeom = new THREE.CylinderGeometry(w / 4, w / 4, h + 2, 32);
    const cutoutMat = new THREE.MeshStandardMaterial({
      color: 0x3b82f6,
      metalness: 0.8,
      roughness: 0.2,
      wireframe,
    });
    const cylinderMesh = new THREE.Mesh(cutoutGeom, cutoutMat);
    group.add(cylinderMesh);

    scene.add(group);
    meshRef.current = mainMesh;

    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      const deltaY = e.clientY - prevMouseY;
      group.rotation.y += deltaX * 0.01;
      group.rotation.x += deltaY * 0.01;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      camera.position.multiplyScalar(e.deltaY > 0 ? 1.05 : 0.95);
      camera.position.clampLength(40, 400);
    };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    container.addEventListener('wheel', onWheel, { passive: false });

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      if (isRotating && !isDragging) {
        group.rotation.y += 0.005;
      }
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      if (!containerRef.current) return;
      const nw = containerRef.current.clientWidth;
      const nh = containerRef.current.clientHeight;
      camera.aspect = nw / nh;
      camera.updateProjectionMatrix();
      renderer.setSize(nw, nh);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', onResize);
      container.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      container.removeEventListener('wheel', onWheel);
      renderer.dispose();
      geometry.dispose();
      cutoutGeom.dispose();
      mat.dispose();
      cutoutMat.dispose();
    };
  }, [isOpen, dimensions, wireframe, isRotating]);

  useEffect(() => {
    if (axesRef.current) {
      axesRef.current.visible = showAxes;
    }
  }, [showAxes]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="w-full max-w-4xl h-[90vh] max-h-[720px] rounded-2xl bg-slate-950 border border-slate-700 shadow-2xl flex flex-col overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="p-1.5 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-400 text-sm">
              🧊
            </span>
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide truncate max-w-md">
                {title}
              </h2>
              <span className="text-[11px] text-cyan-400 font-mono">
                {t('w3d_subtitle')}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setWireframe(!wireframe)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                wireframe
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50'
                  : 'bg-slate-800 text-slate-300 border-slate-700 hover:text-white'
              }`}
            >
              {wireframe ? t('w3d_solid') : t('w3d_wire')}
            </button>
            <button
              type="button"
              onClick={() => setShowAxes(!showAxes)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors ${
                showAxes
                  ? 'bg-purple-500/20 text-purple-300 border-purple-500/50'
                  : 'bg-slate-800 text-slate-300 border-slate-700 hover:text-white'
              }`}
            >
              {t('w3d_axes')}
            </button>
            <button
              type="button"
              onClick={() => setIsRotating(!isRotating)}
              className="px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:text-white transition-colors"
            >
              {isRotating ? t('w3d_pause') : t('w3d_rotate')}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white text-sm transition-colors ml-1"
              title={t('close')}
            >
              ✕
            </button>
          </div>
        </div>

        <div className="flex-1 flex flex-col md:flex-row min-h-0 relative">
          <div
            ref={containerRef}
            className="flex-1 h-full min-h-[300px] cursor-grab active:cursor-grabbing relative overflow-hidden"
          />

          <div className="w-full md:w-72 bg-slate-900/90 border-t md:border-t-0 md:border-l border-slate-800 p-4 flex flex-col gap-3.5 text-xs text-slate-200 overflow-y-auto">
            <div>
              <span className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
                {t('w3d_params')}
              </span>
              <div className="mt-2 flex flex-col gap-1.5">
                <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
                  <span className="text-slate-400">{t('w3d_dims')}</span>
                  <span className="font-mono text-cyan-300">
                    {dimensions[0]} × {dimensions[1]} × {dimensions[2]} mm
                  </span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
                  <span className="text-slate-400">{t('w3d_material')}</span>
                  <span className="font-medium text-slate-200">{material}</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
                  <span className="text-slate-400">{t('w3d_tolerance')}</span>
                  <span className="font-mono text-purple-300">±{tolerance} mm</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-slate-800/60">
                  <span className="text-slate-400">{t('w3d_kerf')}</span>
                  <span className="font-mono text-emerald-300">{kerf} mm</span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
              <span className="text-[10px] font-semibold text-cyan-400 uppercase tracking-wider block mb-1">
                {t('w3d_controls')}
              </span>
              <ul className="text-[11px] text-slate-400 flex flex-col gap-1">
                <li>• {t('w3d_ctl_drag')}</li>
                <li>• {t('w3d_ctl_wheel')}</li>
                <li>• {t('w3d_ctl_wire')}</li>
              </ul>
            </div>

            <div className="mt-auto pt-2 flex flex-col gap-2">
              <button
                type="button"
                onClick={() => {
                  const blob = new Blob([workpiece?.code || 'solid piece'], { type: 'text/plain' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${title.toLowerCase().replace(/\s+/g, '_')}.scad`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="w-full py-2 px-3 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-cyan-950 transition-all"
              >
                <span>💾</span>
                <span>{t('w3d_export')}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
