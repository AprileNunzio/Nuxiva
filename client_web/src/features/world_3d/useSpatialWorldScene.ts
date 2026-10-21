import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { WorldEnvironmentState, SpatialAsset } from '../../shared/types';
import { NuxivaAvatarBuilder } from '../spatial_assets/builders/character_avatar';
import { WeatherEffectsBuilder, WeatherType } from '../spatial_assets/builders/weather_effects';
import { Props3DBuilder } from '../spatial_assets/builders/props_builder';
import { SPATIAL_ASSETS_REGISTRY } from '../spatial_assets/asset_catalog';
import { useI18n } from '../../shared/i18n/I18nContext';

export interface UseSpatialWorldReturn {
  mountRef: React.RefObject<HTMLDivElement>;
  worldState: WorldEnvironmentState;
  speechText: string;
  isProcessing: boolean;
  spawnedProps: string[];
  handleWeatherChange: (weather: WeatherType) => void;
  equipItem: (itemId: string) => void;
  unequipItem: () => void;
  spawnAssetInWorld: (asset: SpatialAsset) => void;
  clearAllProps: () => void;
  handleCommandDispatch: (query: string) => void;
}

export const useSpatialWorldScene = (): UseSpatialWorldReturn => {
  const { t } = useI18n();
  const mountRef = useRef<HTMLDivElement>(null);

  const [worldState, setWorldState] = useState<WorldEnvironmentState>({
    weather: 'CLEAR',
    sceneTheme: 'CYBER_LAB',
    equippedItem: null,
    ambientLightColor: '#00f0ff',
    rainIntensity: 0
  });

  const [speechText, setSpeechText] = useState<string>(t('world_speech_waiting'));
  const [isProcessing, setIsProcessing] = useState(false);
  const [spawnedProps, setSpawnedProps] = useState<string[]>([]);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const weatherSystemRef = useRef<WeatherEffectsBuilder | null>(null);
  const avatarSlotRef = useRef<THREE.Group | null>(null);
  const activeEquippedMeshRef = useRef<THREE.Object3D | null>(null);
  const spawnedObjectsRef = useRef<Map<string, THREE.Object3D>>(new Map());
  const updateAvatarAnimRef = useRef<((delta: number, isSpeaking: boolean, isThinking: boolean) => void) | null>(null);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x030712);
    scene.fog = new THREE.FogExp2(0x030712, 0.04);

    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    camera.position.set(0, 2.5, 6.5);
    camera.lookAt(0, 1.8, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    rendererRef.current = renderer;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0x1e293b, 1.5);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0x38bdf8, 2.5);
    keyLight.position.set(4, 8, 4);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x00f0ff, 1.8);
    rimLight.position.set(-4, 6, -4);
    scene.add(rimLight);

    const floorGeo = new THREE.PlaneGeometry(30, 30);
    floorGeo.rotateX(-Math.PI / 2);
    const floorMat = new THREE.MeshStandardMaterial({
      color: 0x090d16,
      roughness: 0.2,
      metalness: 0.8
    });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.receiveShadow = true;
    scene.add(floor);

    const grid = new THREE.GridHelper(30, 60, 0x00f0ff, 0x1e293b);
    grid.position.y = 0.01;
    scene.add(grid);

    const avatar = NuxivaAvatarBuilder.buildAvatar();
    avatar.rootGroup.position.set(0, 0, 0);
    scene.add(avatar.rootGroup);
    avatarSlotRef.current = avatar.rightHandSlot;
    updateAvatarAnimRef.current = avatar.updateAnimation;

    const weatherEffects = new WeatherEffectsBuilder(scene);
    weatherSystemRef.current = weatherEffects;

    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    let theta = 0;
    let radius = 6.5;

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;

      theta -= deltaX * 0.006;
      camera.position.x = Math.sin(theta) * radius;
      camera.position.z = Math.cos(theta) * radius;
      camera.lookAt(0, 1.8, 0);
    };

    const onMouseUp = () => { isDragging = false; };

    const onWheel = (e: WheelEvent) => {
      radius = Math.max(3.0, Math.min(12.0, radius + e.deltaY * 0.005));
      camera.position.x = Math.sin(theta) * radius;
      camera.position.z = Math.cos(theta) * radius;
      camera.lookAt(0, 1.8, 0);
    };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    container.addEventListener('wheel', onWheel);

    let lastTime = performance.now();
    let animId: number;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const now = performance.now();
      const delta = (now - lastTime) / 1000;
      lastTime = now;

      if (updateAvatarAnimRef.current) {
        updateAvatarAnimRef.current(delta, false, isProcessing);
      }
      if (weatherSystemRef.current) {
        weatherSystemRef.current.update(delta);
      }

      const cadFlange = scene.getObjectByName("cad_floating_flange");
      if (cadFlange) {
        cadFlange.rotation.y += delta * 1.5;
        cadFlange.position.y = 1.6 + Math.sin(now * 0.003) * 0.08;
      }

      const drone = scene.getObjectByName("veh_surveillance_drone");
      if (drone) {
        drone.rotation.y += delta * 0.8;
        drone.position.y = 2.8 + Math.sin(now * 0.002) * 0.2;
        drone.position.x = Math.cos(now * 0.001) * 2.5;
        drone.position.z = Math.sin(now * 0.001) * 2.5;
      }

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
      weatherEffects.cleanup();
    };
  }, []);

  const handleWeatherChange = (weather: WeatherType) => {
    setWorldState(prev => ({ ...prev, weather }));
    if (weatherSystemRef.current) {
      weatherSystemRef.current.applyWeather(weather);
    }

    if (weather === 'RAIN' || weather === 'THUNDERSTORM') {
      equipItem('prop_umbrella');
      setSpeechText(t('world_speech_rain'));
    } else if (weather === 'CLEAR') {
      unequipItem();
      setSpeechText(t('world_speech_sun'));
    } else if (weather === 'SNOW') {
      unequipItem();
      setSpeechText(t('world_speech_snow'));
    }
  };

  const equipItem = (itemId: string) => {
    if (!avatarSlotRef.current) return;
    unequipItem();

    let newMesh: THREE.Object3D | null = null;
    if (itemId === 'prop_umbrella') {
      newMesh = Props3DBuilder.buildUmbrella();
    } else if (itemId === 'tool_hologram_tablet') {
      newMesh = Props3DBuilder.buildHologramTablet();
      newMesh.position.set(0, 0, 0.2);
    }

    if (newMesh) {
      avatarSlotRef.current.add(newMesh);
      activeEquippedMeshRef.current = newMesh;
      setWorldState(prev => ({ ...prev, equippedItem: itemId }));
    }
  };

  const unequipItem = () => {
    if (avatarSlotRef.current && activeEquippedMeshRef.current) {
      avatarSlotRef.current.remove(activeEquippedMeshRef.current);
      activeEquippedMeshRef.current = null;
      setWorldState(prev => ({ ...prev, equippedItem: null }));
    }
  };

  const spawnAssetInWorld = (asset: SpatialAsset) => {
    if (!sceneRef.current) return;
    const scene = sceneRef.current;

    if (spawnedObjectsRef.current.has(asset.id)) {
      const old = spawnedObjectsRef.current.get(asset.id)!;
      scene.remove(old);
      spawnedObjectsRef.current.delete(asset.id);
      setSpawnedProps(prev => prev.filter(id => id !== asset.id));
      return;
    }

    let obj: THREE.Object3D | null = null;
    if (asset.id === 'tool_cad_workbench') {
      obj = Props3DBuilder.buildCadWorkbench();
      obj.position.set(-2.2, 0, -1.0);
      setSpeechText(t('world_speech_cad'));
    } else if (asset.id === 'device_server_rack') {
      obj = Props3DBuilder.buildServerRack();
      obj.position.set(2.4, 0, -1.5);
      setSpeechText(t('world_speech_server'));
    } else if (asset.id === 'veh_surveillance_drone') {
      obj = Props3DBuilder.buildDrone();
      obj.position.set(0, 2.5, 2.0);
      setSpeechText(t('world_speech_drone'));
    } else if (asset.id === 'device_smart_light') {
      obj = Props3DBuilder.buildSmartLight(true);
      obj.position.set(-1.8, 0, 1.2);
    } else if (asset.id === 'prop_umbrella') {
      equipItem('prop_umbrella');
      return;
    }

    if (obj) {
      scene.add(obj);
      spawnedObjectsRef.current.set(asset.id, obj);
      setSpawnedProps(prev => [...prev, asset.id]);
    }
  };

  const clearAllProps = () => {
    if (!sceneRef.current) return;
    const scene = sceneRef.current;
    spawnedObjectsRef.current.forEach((obj) => {
      scene.remove(obj);
    });
    spawnedObjectsRef.current.clear();
    setSpawnedProps([]);
    unequipItem();
  };

  const handleCommandDispatch = (query: string) => {
    const text = query.trim();
    if (!text) return;
    setIsProcessing(true);

    const lower = text.toLowerCase();
    if (lower.includes('pioggia') || lower.includes('piove') || lower.includes('temporale') || lower.includes('meteo')) {
      handleWeatherChange('RAIN');
      setSpeechText(t('world_speech_rain'));
    } else if (lower.includes('sole') || lower.includes('bel tempo') || lower.includes('sereno')) {
      handleWeatherChange('CLEAR');
      setSpeechText(t('world_speech_sun'));
    } else if (lower.includes('neve') || lower.includes('nevica') || lower.includes('freddo')) {
      handleWeatherChange('SNOW');
      setSpeechText(t('world_speech_snow'));
    } else if (lower.includes('cad') || lower.includes('flangia') || lower.includes('meccanica') || lower.includes('disegno')) {
      const cadAsset = SPATIAL_ASSETS_REGISTRY.find(a => a.id === 'tool_cad_workbench');
      if (cadAsset) spawnAssetInWorld(cadAsset);
    } else if (lower.includes('server') || lower.includes('proxmox') || lower.includes('cluster') || lower.includes('datacenter')) {
      const srvAsset = SPATIAL_ASSETS_REGISTRY.find(a => a.id === 'device_server_rack');
      if (srvAsset) spawnAssetInWorld(srvAsset);
    } else if (lower.includes('drone') || lower.includes('sorveglianza') || lower.includes('telecamera')) {
      const droneAsset = SPATIAL_ASSETS_REGISTRY.find(a => a.id === 'veh_surveillance_drone');
      if (droneAsset) spawnAssetInWorld(droneAsset);
    } else if (lower.includes('luce') || lower.includes('accendi') || lower.includes('lampada')) {
      const lightAsset = SPATIAL_ASSETS_REGISTRY.find(a => a.id === 'device_smart_light');
      if (lightAsset) spawnAssetInWorld(lightAsset);
    } else {
      setSpeechText(`Ricevuto: "${text}". Ho sintonizzato lo spazio 3D e instradato la richiesta.`);
    }

    setIsProcessing(false);
  };

  return {
    mountRef,
    worldState,
    speechText,
    isProcessing,
    spawnedProps,
    handleWeatherChange,
    equipItem,
    unequipItem,
    spawnAssetInWorld,
    clearAllProps,
    handleCommandDispatch
  };
};
