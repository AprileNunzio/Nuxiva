import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { Mic, Send, Volume2, Shield, Activity, Zap, BrainCircuit, X, Info } from 'lucide-react';
import { KnowledgeNode } from '../../shared/types';
import { useI18n } from '../../shared/i18n/I18nContext';

interface NeuralCoreCanvasProps {
  onSendCommand: (command: string) => Promise<string>;
  activeNodes: KnowledgeNode[];
}

export const NeuralCoreCanvas: React.FC<NeuralCoreCanvasProps> = ({ onSendCommand, activeNodes }) => {
  const { t } = useI18n();
  const mountRef = useRef<HTMLDivElement>(null);
  const [inputText, setInputText] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [lastSpeechOutput, setLastSpeechOutput] = useState<string>('');
  const [selectedMemory, setSelectedMemory] = useState<KnowledgeNode | null>(null);
  const [showLegend, setShowLegend] = useState(false);

  useEffect(() => {
    if (!lastSpeechOutput) {
      setLastSpeechOutput(t('core_speech_default'));
    }
  }, [t, lastSpeechOutput]);

  useEffect(() => {
    const currentMount = mountRef.current;
    if (!currentMount) return;

    const width = currentMount.clientWidth;
    const height = currentMount.clientHeight;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.z = 10;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    currentMount.appendChild(renderer.domElement);

    const nodesCount = Math.max(activeNodes.length, 100);
    const positions = new Float32Array(nodesCount * 3);
    const colors = new Float32Array(nodesCount * 3);
    
    for (let i = 0; i < nodesCount; i++) {
        positions[i*3] = (Math.random() - 0.5) * 15;
        positions[i*3+1] = (Math.random() - 0.5) * 15;
        positions[i*3+2] = (Math.random() - 0.5) * 15;

        let r = 0.1, g = 0.2, b = 0.3;

        if (i < activeNodes.length) {
            const type = (activeNodes[i].node_type || '').toUpperCase();
            if (type === 'PERSISTENT' || type === 'LONG_TERM') {
                r = 1.0; g = 0.84; b = 0.0;
            } else if (type === 'ACTIVE' || type === 'RECENT') {
                r = 0.0; g = 1.0; b = 0.2;
            } else if (type === 'ERROR' || type === 'CORRECTION') {
                r = 1.0; g = 0.0; b = 0.2;
            } else {
                r = 0.0; g = 0.8; b = 1.0;
            }
        }

        colors[i*3] = r;
        colors[i*3+1] = g;
        colors[i*3+2] = b;
    }
    
    const nodesGeo = new THREE.BufferGeometry();
    nodesGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    nodesGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    
    const nodesMat = new THREE.PointsMaterial({
        size: 0.25,
        vertexColors: true,
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending
    });
    
    const nodesMesh = new THREE.Points(nodesGeo, nodesMat);
    scene.add(nodesMesh);

    const linesGeo = new THREE.BufferGeometry();
    const linesPositions = [];
    const linesColors = [];
    for (let i = 0; i < nodesCount; i++) {
        for (let j = i + 1; j < nodesCount; j++) {
            const dx = positions[i*3] - positions[j*3];
            const dy = positions[i*3+1] - positions[j*3+1];
            const dz = positions[i*3+2] - positions[j*3+2];
            const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);
            if (dist < 3.0) {
                linesPositions.push(
                    positions[i*3], positions[i*3+1], positions[i*3+2],
                    positions[j*3], positions[j*3+1], positions[j*3+2]
                );
                linesColors.push(
                    colors[i*3], colors[i*3+1], colors[i*3+2],
                    colors[j*3], colors[j*3+1], colors[j*3+2]
                );
            }
        }
    }
    linesGeo.setAttribute('position', new THREE.Float32BufferAttribute(linesPositions, 3));
    linesGeo.setAttribute('color', new THREE.Float32BufferAttribute(linesColors, 3));
    const linesMat = new THREE.LineBasicMaterial({
        vertexColors: true,
        transparent: true,
        opacity: 0.3,
        blending: THREE.AdditiveBlending
    });
    const linesMesh = new THREE.LineSegments(linesGeo, linesMat);
    scene.add(linesMesh);

    const coreGeo = new THREE.IcosahedronGeometry(2, 2);
    const coreMat = new THREE.MeshBasicMaterial({
        color: 0x0055ff,
        wireframe: true,
        transparent: true,
        opacity: 0.5,
        blending: THREE.AdditiveBlending
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    scene.add(coreMesh);

    const raycaster = new THREE.Raycaster();
    raycaster.params.Points.threshold = 0.3;
    const mouse = new THREE.Vector2();

    const onPointerDown = (event: PointerEvent) => {
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObject(nodesMesh);
        
        if (intersects.length > 0) {
            const index = intersects[0].index;
            if (index !== undefined) {
                if (index < activeNodes.length) {
                    setSelectedMemory(activeNodes[index]);
                } else {
                    setSelectedMemory({
                        id: `sys-node-${index}`,
                        label: t('core_latent_label'),
                        node_type: "LATENT",
                        properties: { info: t('core_latent_info') },
                        created_at: Date.now(),
                        updated_at: Date.now()
                    });
                }
            }
        }
    };

    const canvasElement = renderer.domElement;
    canvasElement.addEventListener('pointerdown', onPointerDown);

    let animationFrameId: number;
    let clock = new THREE.Clock();
    const posAttr = nodesGeo.attributes.position as THREE.BufferAttribute;

    const animate = () => {
      const elapsedTime = clock.getElapsedTime();
      
      coreMesh.rotation.y = elapsedTime * 0.2;
      coreMesh.rotation.x = elapsedTime * 0.1;
      const pulse = 1 + Math.sin(elapsedTime * 4) * 0.05;
      coreMesh.scale.set(pulse, pulse, pulse);

      nodesMesh.rotation.y = elapsedTime * 0.05;
      linesMesh.rotation.y = elapsedTime * 0.05;
      nodesMesh.rotation.x = elapsedTime * 0.02;
      linesMesh.rotation.x = elapsedTime * 0.02;

      for (let i = 0; i < nodesCount; i++) {
          posAttr.setY(i, positions[i*3+1] + Math.sin(elapsedTime * 2 + positions[i*3]) * 0.5);
      }
      posAttr.needsUpdate = true;

      renderer.render(scene, camera);
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();

    const handleResize = () => {
      if (!currentMount) return;
      const newWidth = currentMount.clientWidth;
      const newHeight = currentMount.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      canvasElement.removeEventListener('pointerdown', onPointerDown);
      cancelAnimationFrame(animationFrameId);
      if (currentMount.contains(renderer.domElement)) {
        currentMount.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [activeNodes, t]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isProcessing) return;

    const query = inputText.trim();
    setInputText('');
    setIsProcessing(true);

    const speech = await onSendCommand(query);
    setLastSpeechOutput(speech);
    setIsProcessing(false);
  };

  const toggleVoiceListen = () => {
    setIsListening(prev => !prev);
    if (!isListening) {
      setLastSpeechOutput(t('core_speech_listening'));
    }
  };

  return (
    <div className="relative w-full h-[calc(100vh-4.5rem)] 8k:h-[calc(100vh-8rem)] flex flex-col justify-between overflow-hidden bg-radial-gradient">
      <div ref={mountRef} className="absolute inset-0 z-0 cursor-crosshair" />

      {/* Neuron Inspector Modal/Panel */}
      {selectedMemory && (
        <div className="absolute top-16 md:top-20 right-3 sm:right-6 md:right-8 z-30 bg-slate-950/95 border border-cyan-400/50 backdrop-blur-2xl p-4 sm:p-6 8k:p-10 rounded-2xl 8k:rounded-3xl w-[92%] sm:w-80 md:w-96 8k:w-[500px] shadow-[0_0_40px_rgba(0,255,255,0.2)] pointer-events-auto transform transition-all animate-fadeIn">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2.5">
              <BrainCircuit className="w-5 h-5 8k:w-8 8k:h-8 text-cyan-400" />
              <h3 className="text-xs sm:text-sm 8k:text-xl font-mono text-cyan-400 uppercase tracking-widest font-bold">
                {t('core_inspect_title')}
              </h3>
            </div>
            <button 
              onClick={() => setSelectedMemory(null)}
              className="text-slate-400 hover:text-white p-1 rounded-lg"
              aria-label={t('close')}
            >
              <X className="w-4 h-4 8k:w-6 8k:h-6" />
            </button>
          </div>

          <div className="space-y-3 8k:space-y-5">
            <div>
              <div className="text-[10px] 8k:text-sm text-slate-500 uppercase tracking-widest font-mono">{t('core_inspect_id')}</div>
              <div className="text-xs 8k:text-base text-slate-300 font-mono truncate">{selectedMemory.id}</div>
            </div>
            <div>
              <div className="text-[10px] 8k:text-sm text-slate-500 uppercase tracking-widest font-mono">{t('core_inspect_label')}</div>
              <div className="text-xs sm:text-sm 8k:text-lg text-white font-semibold">{selectedMemory.label}</div>
            </div>
            <div>
              <div className="text-[10px] 8k:text-sm text-slate-500 uppercase tracking-widest font-mono">{t('core_inspect_type')}</div>
              <div className="text-xs 8k:text-base font-mono px-2 py-0.5 rounded-md inline-block mt-1 bg-slate-800 text-slate-300">
                {selectedMemory.node_type}
              </div>
            </div>
            {selectedMemory.properties && Object.keys(selectedMemory.properties).length > 0 && (
              <div>
                <div className="text-[10px] 8k:text-sm text-slate-500 uppercase tracking-widest font-mono">{t('core_inspect_attrs')}</div>
                <pre className="text-[10px] 8k:text-sm text-cyan-200 mt-1 bg-black/60 p-2 8k:p-4 rounded-xl border border-slate-800 overflow-x-auto max-h-32 8k:max-h-56 overflow-y-auto font-mono">
                  {JSON.stringify(selectedMemory.properties, null, 2)}
                </pre>
              </div>
            )}
          </div>

          <button 
            onClick={() => setSelectedMemory(null)}
            className="mt-4 sm:mt-5 w-full py-2 sm:py-2.5 8k:py-4 bg-slate-800 hover:bg-cyan-900/40 border border-slate-700 hover:border-cyan-400 text-xs 8k:text-base font-semibold text-white rounded-xl transition-colors uppercase tracking-wider"
          >
            {t('core_inspect_close')}
          </button>
        </div>
      )}

      {/* Neural Legend */}
      <div className="absolute bottom-28 sm:bottom-32 left-3 sm:left-6 md:left-8 z-20 pointer-events-auto">
        <button
          onClick={() => setShowLegend(!showLegend)}
          className="sm:hidden mb-2 p-2 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-300 text-xs flex items-center gap-1.5 shadow-lg"
        >
          <Info className="w-3.5 h-3.5 text-cyan-400" />
          <span>{t('core_legend_title')}</span>
        </button>

        <div className={`${showLegend ? 'block' : 'hidden sm:block'} bg-slate-950/85 border border-slate-800 backdrop-blur-md p-3 sm:p-4 8k:p-6 rounded-2xl shadow-xl transition-all`}>
          <h4 className="text-[10px] 8k:text-sm font-mono uppercase tracking-widest text-slate-500 mb-2 8k:mb-3">
            {t('core_legend_title')}
          </h4>
          <div className="space-y-1.5 sm:space-y-2 8k:space-y-3 font-mono text-[11px] sm:text-xs 8k:text-base">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 8k:w-3.5 8k:h-3.5 rounded-full bg-[#00ff33] shadow-[0_0_8px_#00ff33]"></div>
              <span className="text-slate-300">{t('core_legend_active')}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 8k:w-3.5 8k:h-3.5 rounded-full bg-[#ffd700] shadow-[0_0_8px_#ffd700]"></div>
              <span className="text-slate-300">{t('core_legend_persistent')}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 8k:w-3.5 8k:h-3.5 rounded-full bg-[#00ccff] shadow-[0_0_8px_#00ccff]"></div>
              <span className="text-slate-300">{t('core_legend_standard')}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 8k:w-3.5 8k:h-3.5 rounded-full bg-[#ff0033] shadow-[0_0_8px_#ff0033]"></div>
              <span className="text-slate-300">{t('core_legend_error')}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 8k:w-3.5 8k:h-3.5 rounded-full bg-[#1a334d]"></div>
              <span className="text-slate-500">{t('core_legend_latent')}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Top HUD Cards */}
      <div className="relative z-10 p-3 sm:p-4 lg:p-8 8k:p-14 flex flex-wrap justify-between items-start gap-2 pointer-events-none">
        <div className="bg-slate-950/80 border border-cyan-900/50 backdrop-blur-md p-3.5 sm:p-4 8k:p-8 rounded-2xl 8k:rounded-3xl max-w-sm 8k:max-w-lg pointer-events-auto shadow-2xl">
          <div className="flex items-center space-x-2 text-cyan-400 mb-1.5 sm:mb-2">
            <Activity className="w-4 h-4 8k:w-7 8k:h-7 animate-spin" />
            <h2 className="text-xs 8k:text-base font-mono uppercase tracking-widest font-semibold">
              {t('core_status_title')}
            </h2>
          </div>
          <p className="text-xs sm:text-sm 8k:text-xl font-['Rajdhani'] text-slate-200">
            {t('core_active_nodes')}: <span className="font-bold text-cyan-400 font-mono">{activeNodes.length}</span>
          </p>
          <p className="text-[10px] 8k:text-sm text-cyan-500/80 uppercase mt-1 tracking-wider">
            {t('core_click_hint')}
          </p>
          <div className="flex items-center space-x-2 mt-2 pt-2 border-t border-slate-800 text-[10px] sm:text-[11px] 8k:text-sm text-slate-400">
            <Shield className="w-3.5 h-3.5 8k:w-5 8k:h-5 text-emerald-400" />
            <span>{t('core_biometry_verified')}</span>
          </div>
        </div>

        <div className="hidden md:flex flex-col space-y-2 pointer-events-auto">
          <div className="bg-slate-950/80 border border-slate-800 backdrop-blur-md px-3 py-2 8k:px-6 8k:py-3.5 rounded-xl 8k:rounded-2xl text-xs 8k:text-lg font-mono text-slate-300 flex items-center space-x-2">
            <Zap className="w-3.5 h-3.5 8k:w-6 8k:h-6 text-amber-400" />
            <span>{t('core_routing_mode')}</span>
          </div>
        </div>
      </div>

      {/* Bottom Command Center */}
      <div className="relative z-10 w-full max-w-3xl 4xl:max-w-4xl 8k:max-w-6xl mx-auto px-3 sm:px-4 pb-4 sm:pb-6 8k:pb-12 flex flex-col items-center pointer-events-auto">
        <div className="w-full mb-3 sm:mb-4 bg-slate-950/85 border border-cyan-500/30 backdrop-blur-xl rounded-2xl 8k:rounded-3xl p-3 sm:p-4 8k:p-7 shadow-[0_0_30px_rgba(0,240,255,0.12)]">
          <div className="flex items-start space-x-3 8k:space-x-5">
            <div className="mt-0.5 sm:mt-1 flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 8k:w-14 8k:h-14 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 shrink-0">
              <Volume2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 8k:w-7 8k:h-7" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] 8k:text-sm font-mono uppercase tracking-wider text-cyan-400">
                {t('core_speech_title')}
              </div>
              <p className="text-xs sm:text-sm md:text-base 8k:text-2xl text-slate-200 font-['Rajdhani'] font-medium tracking-wide mt-1">
                "{lastSpeechOutput}"
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="w-full relative flex items-center">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={t('core_input_placeholder')}
            className="w-full bg-slate-900/90 border border-cyan-950 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 rounded-2xl 8k:rounded-3xl py-3 sm:py-3.5 8k:py-6 pl-3.5 sm:pl-4 8k:pl-8 pr-24 sm:pr-28 8k:pr-40 text-xs sm:text-sm 8k:text-xl text-slate-100 placeholder:text-slate-500 backdrop-blur-md outline-none transition-all shadow-xl"
          />
          <div className="absolute right-1.5 sm:right-2 flex items-center space-x-1 sm:space-x-1.5 8k:space-x-3">
            <button
              type="button"
              onClick={toggleVoiceListen}
              className={`p-2 sm:p-2.5 8k:p-4 rounded-xl 8k:rounded-2xl border transition-all ${
                isListening
                  ? 'bg-rose-500/20 border-rose-500 text-rose-400 animate-pulse'
                  : 'bg-slate-800/80 hover:bg-cyan-500/20 border-slate-700 hover:border-cyan-500/50 text-slate-300 hover:text-cyan-400'
              }`}
              title={t('core_mic_tooltip')}
              aria-label={t('core_mic_tooltip')}
            >
              <Mic className="w-4 h-4 8k:w-7 8k:h-7" />
            </button>
            <button
              type="submit"
              disabled={isProcessing || !inputText.trim()}
              className="p-2 sm:p-2.5 8k:p-4 rounded-xl 8k:rounded-2xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-40 text-black font-semibold transition-all shadow-md"
              title={t('core_send_tooltip')}
              aria-label={t('core_send_tooltip')}
            >
              <Send className="w-4 h-4 8k:w-7 8k:h-7" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
