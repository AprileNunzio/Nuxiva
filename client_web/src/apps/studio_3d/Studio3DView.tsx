import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { 
  Box, 
  Grid, 
  RotateCcw, 
  Camera, 
  Sparkles, 
  Sliders, 
  Layers, 
  UploadCloud,
  X,
  Menu
} from 'lucide-react';
import { useI18n } from '../../shared/i18n/I18nContext';

export const Studio3DView: React.FC = () => {
  const { t } = useI18n();
  const mountRef = useRef<HTMLDivElement>(null);

  const [renderMode, setRenderMode] = useState<'solid' | 'wireframe' | 'points'>('solid');
  const [showGrid, setShowGrid] = useState(true);
  const [meshColor, setMeshColor] = useState('#0284c7');
  const [roughness, setRoughness] = useState(0.2);
  const [metalness, setMetalness] = useState(0.85);
  const [mobileInspectorOpen, setMobileInspectorOpen] = useState(false);

  const [stats, setStats] = useState({
    vertices: 0,
    triangles: 0,
    dimensions: { x: 0, y: 0, z: 0 }
  });

  const [promptText, setPromptText] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const currentMeshGroupRef = useRef<THREE.Group | null>(null);
  const gridHelperRef = useRef<THREE.GridHelper | null>(null);
  const axesHelperRef = useRef<THREE.AxesHelper | null>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x020617);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    cameraRef.current = camera;
    camera.position.set(4, 3, 5);
    camera.lookAt(0, 0.5, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    rendererRef.current = renderer;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
    scene.add(ambientLight);

    const mainLight = new THREE.DirectionalLight(0xffffff, 2.0);
    mainLight.position.set(5, 10, 7);
    mainLight.castShadow = true;
    scene.add(mainLight);

    const fillLight = new THREE.DirectionalLight(0x38bdf8, 1.5);
    fillLight.position.set(-5, 4, -5);
    scene.add(fillLight);

    const grid = new THREE.GridHelper(10, 20, 0x00f0ff, 0x334155);
    grid.position.y = -0.01;
    scene.add(grid);
    gridHelperRef.current = grid;

    const axes = new THREE.AxesHelper(2.5);
    scene.add(axes);
    axesHelperRef.current = axes;

    loadMechanicalFlange(scene);

    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    let theta = 0.8;
    let phi = 0.5;
    let radius = 6.0;

    const onPointerDown = (e: PointerEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onPointerMove = (e: PointerEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      const deltaY = e.clientY - prevMouseY;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;

      theta -= deltaX * 0.008;
      phi = Math.max(0.1, Math.min(Math.PI / 2 - 0.05, phi + deltaY * 0.008));

      camera.position.x = radius * Math.sin(theta) * Math.cos(phi);
      camera.position.y = radius * Math.sin(phi);
      camera.position.z = radius * Math.cos(theta) * Math.cos(phi);
      camera.lookAt(0, 0.5, 0);
    };

    const onPointerUp = () => { isDragging = false; };

    const onWheel = (e: WheelEvent) => {
      radius = Math.max(2.0, Math.min(15.0, radius + e.deltaY * 0.005));
      camera.position.x = radius * Math.sin(theta) * Math.cos(phi);
      camera.position.y = radius * Math.sin(phi);
      camera.position.z = radius * Math.cos(theta) * Math.cos(phi);
      camera.lookAt(0, 0.5, 0);
    };

    container.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    container.addEventListener('wheel', onWheel);

    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    const onResize = () => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(animId);
      container.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerup', onPointerUp);
      container.removeEventListener('wheel', onWheel);
      window.removeEventListener('resize', onResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  const loadMechanicalFlange = (scene: THREE.Scene) => {
    if (currentMeshGroupRef.current) {
      scene.remove(currentMeshGroupRef.current);
    }

    const group = new THREE.Group();
    group.name = "cad_component";

    const diskGeo = new THREE.CylinderGeometry(1.5, 1.5, 0.25, 48);
    const mat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(meshColor),
      roughness,
      metalness,
      wireframe: renderMode === 'wireframe'
    });
    const disk = new THREE.Mesh(diskGeo, mat);
    disk.position.y = 0.5;
    group.add(disk);

    const hubGeo = new THREE.CylinderGeometry(0.75, 0.75, 0.6, 48);
    const hub = new THREE.Mesh(hubGeo, mat);
    hub.position.y = 0.8;
    group.add(hub);

    for (let i = 0; i < 6; i++) {
      const angle = (i * Math.PI * 2) / 6;
      const holeGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.26, 16);
      const holeMat = new THREE.MeshStandardMaterial({ color: 0x090d16, metalness: 0.9, roughness: 0.1 });
      const hole = new THREE.Mesh(holeGeo, holeMat);
      hole.position.set(Math.cos(angle) * 1.1, 0.51, Math.sin(angle) * 1.1);
      group.add(hole);
    }

    scene.add(group);
    currentMeshGroupRef.current = group;

    const bbox = new THREE.Box3().setFromObject(group);
    const size = new THREE.Vector3();
    bbox.getSize(size);

    setStats({
      vertices: 1840,
      triangles: 3680,
      dimensions: {
        x: Math.round(size.x * 100), 
        y: Math.round(size.y * 100),
        z: Math.round(size.z * 100)
      }
    });
  };

  useEffect(() => {
    if (currentMeshGroupRef.current) {
      currentMeshGroupRef.current.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          if (child.material instanceof THREE.MeshStandardMaterial) {
            child.material.color.set(meshColor);
            child.material.roughness = roughness;
            child.material.metalness = metalness;
            child.material.wireframe = renderMode === 'wireframe';
          }
        }
      });
    }
  }, [meshColor, roughness, metalness, renderMode]);

  useEffect(() => {
    if (gridHelperRef.current) {
      gridHelperRef.current.visible = showGrid;
    }
    if (axesHelperRef.current) {
      axesHelperRef.current.visible = showGrid;
    }
  }, [showGrid]);

  const handleCaptureSnapshot = () => {
    if (!rendererRef.current) return;
    const dataUrl = rendererRef.current.domElement.toDataURL('image/png');
    const link = document.createElement('a');
    link.download = `nuxiva_cad_${Date.now()}.png`;
    link.href = dataUrl;
    link.click();
  };

  const handleResetCamera = () => {
    if (!cameraRef.current) return;
    cameraRef.current.position.set(4, 3, 5);
    cameraRef.current.lookAt(0, 0.5, 0);
  };

  const handleAiGenerate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptText.trim()) return;
    setIsGenerating(true);

    setTimeout(() => {
      if (sceneRef.current) {
        loadMechanicalFlange(sceneRef.current);
      }
      setIsGenerating(false);
      setPromptText('');
    }, 1200);
  };

  const renderInspectorContent = () => (
    <>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm 8k:text-xl font-bold text-slate-900 flex items-center gap-2 8k:gap-3 mb-1">
            <Sliders className="w-4 h-4 8k:w-7 8k:h-7 text-cyan-600" />
            {t('studio_inspector_title')}
          </h2>
          <p className="text-xs 8k:text-base text-slate-500">{t('studio_subtitle')}</p>
        </div>
        <button 
          onClick={() => setMobileInspectorOpen(false)}
          className="lg:hidden text-slate-500 hover:text-slate-900 p-1 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Mesh stats */}
      <div className="space-y-3 8k:space-y-5 bg-white/60 border border-slate-200/80 rounded-2xl 8k:rounded-3xl p-4 8k:p-6">
        <div className="flex justify-between items-center text-xs 8k:text-base">
          <span className="text-slate-500">{t('studio_vertices')}</span>
          <span className="font-mono font-bold text-cyan-700">{stats.vertices.toLocaleString()}</span>
        </div>
        <div className="flex justify-between items-center text-xs 8k:text-base">
          <span className="text-slate-500">{t('studio_triangles')}</span>
          <span className="font-mono font-bold text-cyan-700">{stats.triangles.toLocaleString()}</span>
        </div>
        <div className="pt-2 border-t border-slate-200">
          <span className="text-slate-500 text-xs 8k:text-sm block mb-1.5">{t('studio_dimensions')} (mm)</span>
          <div className="grid grid-cols-3 gap-2 8k:gap-4 text-center">
            <div className="bg-slate-100/60 p-1.5 8k:p-3 rounded-lg 8k:rounded-xl">
              <span className="text-[10px] 8k:text-sm text-slate-500 block">X</span>
              <span className="text-xs 8k:text-base font-mono font-bold text-slate-800">{stats.dimensions.x}</span>
            </div>
            <div className="bg-slate-100/60 p-1.5 8k:p-3 rounded-lg 8k:rounded-xl">
              <span className="text-[10px] 8k:text-sm text-slate-500 block">Y</span>
              <span className="text-xs 8k:text-base font-mono font-bold text-slate-800">{stats.dimensions.y}</span>
            </div>
            <div className="bg-slate-100/60 p-1.5 8k:p-3 rounded-lg 8k:rounded-xl">
              <span className="text-[10px] 8k:text-sm text-slate-500 block">Z</span>
              <span className="text-xs 8k:text-base font-mono font-bold text-slate-800">{stats.dimensions.z}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Materials */}
      <div className="space-y-4 8k:space-y-6 bg-white/60 border border-slate-200/80 rounded-2xl 8k:rounded-3xl p-4 8k:p-6">
        <h3 className="text-xs 8k:text-base font-bold text-slate-800 uppercase tracking-wider">{t('studio_material_color')}</h3>
        
        <div className="flex items-center space-x-3 8k:space-x-5">
          <input 
            type="color" 
            value={meshColor} 
            onChange={(e) => setMeshColor(e.target.value)}
            className="w-8 h-8 8k:w-14 8k:h-14 rounded-lg 8k:rounded-xl cursor-pointer bg-transparent border-0" 
          />
          <span className="font-mono text-xs 8k:text-base text-slate-600 uppercase">{meshColor}</span>
        </div>

        <div>
          <div className="flex justify-between text-xs 8k:text-base mb-1">
            <span className="text-slate-500">{t('studio_roughness')}</span>
            <span className="font-mono text-slate-600">{roughness.toFixed(2)}</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.05" 
            value={roughness}
            onChange={(e) => setRoughness(parseFloat(e.target.value))}
            className="w-full accent-cyan-400" 
          />
        </div>

        <div>
          <div className="flex justify-between text-xs 8k:text-base mb-1">
            <span className="text-slate-500">{t('studio_metalness')}</span>
            <span className="font-mono text-slate-600">{metalness.toFixed(2)}</span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.05" 
            value={metalness}
            onChange={(e) => setMetalness(parseFloat(e.target.value))}
            className="w-full accent-cyan-400" 
          />
        </div>
      </div>

      {/* Upload button */}
      <button 
        onClick={() => alert(t('studio_upload_alert'))}
        className="w-full p-3 8k:p-5 rounded-2xl 8k:rounded-3xl border border-dashed border-slate-300 hover:border-cyan-500/60 text-slate-500 hover:text-cyan-700 transition-all flex items-center justify-center space-x-2 8k:space-x-3 text-xs 8k:text-base font-semibold"
      >
        <UploadCloud className="w-4 h-4 8k:w-7 8k:h-7" />
        <span>{t('studio_upload_btn')}</span>
      </button>
    </>
  );

  return (
    <div className="relative w-full h-[calc(100vh-4.5rem)] 8k:h-[calc(100vh-8rem)] overflow-hidden bg-[#020617] font-['Inter'] flex">
      {/* 3D Canvas Area */}
      <div className="flex-1 relative h-full">
        <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {/* Viewport Control Bar */}
        <div className="absolute top-3 sm:top-4 8k:top-8 left-3 sm:left-4 8k:left-8 flex flex-wrap items-center gap-1.5 sm:gap-2 8k:gap-4 backdrop-blur-md bg-white/85 border border-slate-200 p-1.5 8k:p-3 rounded-2xl 8k:rounded-3xl shadow-2xl z-20">
          <button
            onClick={() => setRenderMode('solid')}
            className={`px-2.5 sm:px-3 8k:px-5 py-1.5 8k:py-3 rounded-xl 8k:rounded-2xl text-xs 8k:text-base font-semibold flex items-center gap-1.5 8k:gap-2.5 transition-all ${renderMode === 'solid' ? 'bg-cyan-500/20 text-cyan-700 border border-cyan-500/40 shadow-md' : 'text-slate-500 hover:text-slate-800'}`}
          >
            <Box className="w-3.5 h-3.5 8k:w-6 8k:h-6" />
            <span className="hidden xs:inline">{t('studio_btn_solid')}</span>
          </button>
          <button
            onClick={() => setRenderMode('wireframe')}
            className={`px-2.5 sm:px-3 8k:px-5 py-1.5 8k:py-3 rounded-xl 8k:rounded-2xl text-xs 8k:text-base font-semibold flex items-center gap-1.5 8k:gap-2.5 transition-all ${renderMode === 'wireframe' ? 'bg-cyan-500/20 text-cyan-700 border border-cyan-500/40 shadow-md' : 'text-slate-500 hover:text-slate-800'}`}
          >
            <Layers className="w-3.5 h-3.5 8k:w-6 8k:h-6" />
            <span className="hidden xs:inline">{t('studio_btn_wireframe')}</span>
          </button>
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`px-2.5 sm:px-3 8k:px-5 py-1.5 8k:py-3 rounded-xl 8k:rounded-2xl text-xs 8k:text-base font-semibold flex items-center gap-1.5 8k:gap-2.5 transition-all ${showGrid ? 'bg-cyan-500/20 text-cyan-700 border border-cyan-500/40 shadow-md' : 'text-slate-500 hover:text-slate-800'}`}
          >
            <Grid className="w-3.5 h-3.5 8k:w-6 8k:h-6" />
            <span className="hidden xs:inline">{t('studio_btn_grid')}</span>
          </button>
          <button
            onClick={handleResetCamera}
            className="p-1.5 sm:p-2 8k:p-3 rounded-xl 8k:rounded-2xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-all"
            title={t('studio_btn_reset_cam')}
            aria-label={t('studio_btn_reset_cam')}
          >
            <RotateCcw className="w-4 h-4 8k:w-6 8k:h-6" />
          </button>
          <button
            onClick={handleCaptureSnapshot}
            className="p-1.5 sm:p-2 8k:p-3 rounded-xl 8k:rounded-2xl text-cyan-600 hover:text-cyan-700 hover:bg-cyan-950/40 transition-all"
            title={t('studio_export_png')}
            aria-label={t('studio_export_png')}
          >
            <Camera className="w-4 h-4 8k:w-6 8k:h-6" />
          </button>

          {/* Mobile Inspector Toggle */}
          <button
            onClick={() => setMobileInspectorOpen(true)}
            className="lg:hidden p-1.5 sm:p-2 rounded-xl text-cyan-600 hover:bg-slate-100 transition-all"
            title={t('studio_toggle_inspector')}
            aria-label={t('studio_toggle_inspector')}
          >
            <Sliders className="w-4 h-4" />
          </button>
        </div>

        {/* AI Prompt Generator Form */}
        <div className="absolute bottom-4 sm:bottom-6 8k:bottom-12 left-3 sm:left-6 8k:left-12 right-3 sm:right-6 8k:right-12 max-w-xl 4xl:max-w-2xl 8k:max-w-4xl z-20">
          <form 
            onSubmit={handleAiGenerate}
            className="backdrop-blur-xl bg-white/90 border border-slate-200 rounded-2xl 8k:rounded-3xl p-1.5 sm:p-2 8k:p-4 flex items-center space-x-2 8k:space-x-4 shadow-2xl focus-within:border-cyan-500/40 transition-all"
          >
            <input
              type="text"
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              placeholder={t('studio_generate_prompt')}
              className="flex-1 bg-transparent px-3 sm:px-4 8k:px-6 py-1.5 sm:py-2 8k:py-4 text-xs sm:text-sm 8k:text-xl text-slate-900 placeholder-slate-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={isGenerating || !promptText.trim()}
              className="px-3 sm:px-4 8k:px-7 py-2 8k:py-3.5 rounded-xl 8k:rounded-2xl bg-cyan-500 text-slate-950 font-bold text-xs sm:text-sm 8k:text-xl flex items-center space-x-1.5 8k:space-x-3 hover:bg-cyan-400 disabled:opacity-40 transition-all shrink-0"
            >
              <Sparkles className="w-3.5 h-3.5 8k:w-6 8k:h-6" />
              <span>{isGenerating ? t('studio_generating') : t('studio_generate_btn')}</span>
            </button>
          </form>
        </div>
      </div>

      {/* Desktop & 8K Docked Inspector Panel */}
      <div className="hidden lg:flex w-80 3xl:w-96 8k:w-[540px] h-full backdrop-blur-2xl bg-slate-50/90 border-l border-slate-200/80 p-5 8k:p-8 flex-col space-y-6 8k:space-y-8 overflow-y-auto">
        {renderInspectorContent()}
      </div>

      {/* Mobile Modal/Drawer Inspector */}
      {mobileInspectorOpen && (
        <div className="lg:hidden fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex justify-end animate-fadeIn">
          <div className="w-[85vw] max-w-[360px] h-full bg-slate-50 border-l border-slate-200 p-5 flex flex-col space-y-5 overflow-y-auto shadow-2xl">
            {renderInspectorContent()}
          </div>
        </div>
      )}
    </div>
  );
};
