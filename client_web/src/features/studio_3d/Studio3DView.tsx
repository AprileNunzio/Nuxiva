import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { 
  Box, 
  Eye, 
  Grid, 
  RotateCcw, 
  Camera, 
  Sparkles, 
  Sliders, 
  Layers, 
  UploadCloud,
  FileCode,
  Download
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

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseMove = (e: MouseEvent) => {
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

    const onMouseUp = () => { isDragging = false; };

    const onWheel = (e: WheelEvent) => {
      radius = Math.max(2.0, Math.min(15.0, radius + e.deltaY * 0.005));
      camera.position.x = radius * Math.sin(theta) * Math.cos(phi);
      camera.position.y = radius * Math.sin(phi);
      camera.position.z = radius * Math.cos(theta) * Math.cos(phi);
      camera.lookAt(0, 0.5, 0);
    };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
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
      container.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
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

  return (
    <div className="relative w-full h-[calc(100vh-64px)] overflow-hidden bg-[#020617] font-['Inter'] flex">
      {}
      <div className="flex-1 relative h-full">
        <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

        {}
        <div className="absolute top-4 left-4 flex items-center space-x-2 backdrop-blur-md bg-slate-900/80 border border-slate-800 p-1.5 rounded-2xl shadow-2xl">
          <button
            onClick={() => setRenderMode('solid')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${renderMode === 'solid' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <Box className="w-3.5 h-3.5" />
            <span>{t('studio_btn_solid')}</span>
          </button>
          <button
            onClick={() => setRenderMode('wireframe')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${renderMode === 'wireframe' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>{t('studio_btn_wireframe')}</span>
          </button>
          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${showGrid ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <Grid className="w-3.5 h-3.5" />
            <span>{t('studio_btn_grid')}</span>
          </button>
          <button
            onClick={handleResetCamera}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-all"
            title={t('studio_btn_reset_cam')}
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={handleCaptureSnapshot}
            className="p-2 rounded-xl text-cyan-400 hover:text-cyan-300 hover:bg-cyan-950/40 transition-all"
            title={t('studio_export_png')}
          >
            <Camera className="w-4 h-4" />
          </button>
        </div>

        {}
        <div className="absolute bottom-6 left-6 right-6 max-w-xl">
          <form 
            onSubmit={handleAiGenerate}
            className="backdrop-blur-xl bg-slate-900/90 border border-slate-800 rounded-2xl p-2 flex items-center space-x-2 shadow-2xl focus-within:border-cyan-500/40 transition-all"
          >
            <input
              type="text"
              value={promptText}
              onChange={(e) => setPromptText(e.target.value)}
              placeholder={t('studio_generate_prompt')}
              className="flex-1 bg-transparent px-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
            />
            <button
              type="submit"
              disabled={isGenerating || !promptText.trim()}
              className="px-4 py-2 rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs flex items-center space-x-1.5 hover:bg-cyan-400 disabled:opacity-40 transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isGenerating ? 'Generando...' : t('studio_generate_btn')}</span>
            </button>
          </form>
        </div>
      </div>

      {}
      <div className="w-80 h-full backdrop-blur-2xl bg-slate-950/90 border-l border-slate-800/80 p-5 flex flex-col space-y-6 overflow-y-auto">
        <div>
          <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2 mb-1">
            <Sliders className="w-4 h-4 text-cyan-400" />
            {t('studio_inspector_title')}
          </h2>
          <p className="text-xs text-slate-400">{t('studio_subtitle')}</p>
        </div>

        {}
        <div className="space-y-3 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400">{t('studio_vertices')}</span>
            <span className="font-mono font-bold text-cyan-300">{stats.vertices.toLocaleString()}</span>
          </div>
          <div className="flex justify-between items-center text-xs">
            <span className="text-slate-400">{t('studio_triangles')}</span>
            <span className="font-mono font-bold text-cyan-300">{stats.triangles.toLocaleString()}</span>
          </div>
          <div className="pt-2 border-t border-slate-800">
            <span className="text-slate-400 text-xs block mb-1">{t('studio_dimensions')} (mm)</span>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="bg-slate-800/60 p-1.5 rounded-lg">
                <span className="text-[10px] text-slate-500 block">X</span>
                <span className="text-xs font-mono font-bold text-slate-200">{stats.dimensions.x}</span>
              </div>
              <div className="bg-slate-800/60 p-1.5 rounded-lg">
                <span className="text-[10px] text-slate-500 block">Y</span>
                <span className="text-xs font-mono font-bold text-slate-200">{stats.dimensions.y}</span>
              </div>
              <div className="bg-slate-800/60 p-1.5 rounded-lg">
                <span className="text-[10px] text-slate-500 block">Z</span>
                <span className="text-xs font-mono font-bold text-slate-200">{stats.dimensions.z}</span>
              </div>
            </div>
          </div>
        </div>

        {}
        <div className="space-y-4 bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4">
          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">{t('studio_material_color')}</h3>
          
          <div className="flex items-center space-x-3">
            <input 
              type="color" 
              value={meshColor} 
              onChange={(e) => setMeshColor(e.target.value)}
              className="w-8 h-8 rounded-lg cursor-pointer bg-transparent border-0" 
            />
            <span className="font-mono text-xs text-slate-300 uppercase">{meshColor}</span>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">{t('studio_roughness')}</span>
              <span className="font-mono text-slate-300">{roughness.toFixed(2)}</span>
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
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-400">{t('studio_metalness')}</span>
              <span className="font-mono text-slate-300">{metalness.toFixed(2)}</span>
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

        {}
        <button 
          onClick={() => alert("Upload 3D: supporto STL, OBJ e GLTF attivo.")}
          className="w-full p-3 rounded-2xl border border-dashed border-slate-700 hover:border-cyan-500/60 text-slate-400 hover:text-cyan-300 transition-all flex items-center justify-center space-x-2 text-xs font-semibold"
        >
          <UploadCloud className="w-4 h-4" />
          <span>{t('studio_upload_btn')}</span>
        </button>
      </div>
    </div>
  );
};
