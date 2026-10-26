import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { EnvironmentBuilder } from './features/scene/environment';
import { CathedralSetup } from './features/scene/cathedralSetup';
import { BoardGrid } from './features/scene/boardGrid';
import { AssetLoader } from './features/rendering/assetLoader';
import { ShatterPhysics } from './features/rendering/shatterPhysics';
import { BoardHighlights } from './features/rendering/boardHighlights';
import { PieceRenderer } from './features/rendering/pieceRenderer';
import { CameraPresets } from './features/cinematics/cameraPresets';
import { MoveAnimator } from './features/cinematics/moveAnimator';
import { InputManager } from './features/controls/inputManager';
import { GameController } from './features/game/gameController';
import { ChessRules } from './features/game/chessRules';
import { gameState } from './features/game/gameState';
import { i18n } from './features/i18n/i18nService';
import { initHostBridge } from './features/bridge/hostBridge';

export async function initWizardChess() {
  const container = document.getElementById('canvas-container');
  if (!container) return;
  container.innerHTML = '';

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    powerPreference: 'high-performance'
  });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.24;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x070a12);
  scene.fog = new THREE.FogExp2(0x080b14, 0.015);
  scene.environment = EnvironmentBuilder.createCathedralPMREM(renderer);

  const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 0.22, 65);
  camera.position.set(0, 2.22, 2.72);

  const orbitControls = new OrbitControls(camera, renderer.domElement);
  orbitControls.enableDamping = true;
  orbitControls.dampingFactor = 0.16;
  orbitControls.maxPolarAngle = Math.PI * 0.88;
  orbitControls.minPolarAngle = 0.05;
  orbitControls.minDistance = 0.95;
  orbitControls.maxDistance = 36.0;
  orbitControls.target.set(0, 0.85, -0.15);
  orbitControls.update();

  const { brazierLights } = EnvironmentBuilder.setupCathedralLighting(scene);

  const boardGroup = new THREE.Group();
  scene.add(boardGroup);
  const boardSquareMeshes = [];
  BoardGrid.buildGrid(boardGroup, boardSquareMeshes);

  const highlights = new BoardHighlights(scene);
  const shatter = new ShatterPhysics(scene);
  const pieceRenderer = new PieceRenderer();
  const animator = new MoveAnimator();
  const cameraPresets = new CameraPresets(camera, orbitControls);

  const loaderBar = document.getElementById('loader-bar');
  const loadingOverlay = document.getElementById('loading-overlay');

  const flameUniforms = [];
  const modelsToLoad = ['option8_cathedral', 'pawn_white', 'rook_white', 'knight_white', 'bishop_white', 'queen_white', 'king_white'];
  let loaded = 0;

  for (const name of modelsToLoad) {
    try {
      const gltf = await AssetLoader.loadModel(name);
      if (name === 'option8_cathedral') {
        CathedralSetup.configureCathedral(gltf.scene, scene, flameUniforms);
      } else {
        pieceRenderer.registerTemplate(name, gltf.scene);
      }
    } catch (err) {
      console.warn(`Model loading issue: ${name}`, err);
    }
    loaded++;
    if (loaderBar) loaderBar.style.width = `${Math.round((loaded / modelsToLoad.length) * 100)}%`;
  }

  if (loadingOverlay) {
    loadingOverlay.classList.add('hidden');
    setTimeout(() => {
      loadingOverlay.style.display = 'none';
    }, 450);
  }

  const gameController = new GameController(
    scene,
    highlights,
    shatter,
    pieceRenderer,
    animator
  );

  const inputManager = new InputManager(
    camera,
    renderer.domElement,
    orbitControls,
    (row, col) => gameController.handleSquareClick(row, col)
  );

  const btnSideToggle = document.getElementById('btn-side-toggle');
  if (btnSideToggle) {
    btnSideToggle.addEventListener('click', () => {
      const cur = gameState.getPlayerColor();
      const next = cur === 'white' ? 'black' : 'white';
      gameState.setPlayerColor(next);
      const badge = document.getElementById('mode-badge');
      if (badge) {
        const dict = i18n.getDictionary();
        badge.textContent = next === 'white' ? dict.turn.playingAsWhite : dict.turn.playingAsBlack;
      }
    });
  }

  const btnAiMove = document.getElementById('btn-ai-move');
  if (btnAiMove) {
    btnAiMove.addEventListener('click', () => {
      gameController.triggerAiMove();
    });
  }

  const btnReset = document.getElementById('btn-reset');
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      gameController.resetGame();
    });
  }

  const camButtons = [
    { id: 'btn-cam-player', preset: 'player' },
    { id: 'btn-cam-top', preset: 'top' },
    { id: 'btn-cam-side', preset: 'side' },
    { id: 'btn-cam-wide', preset: 'wide' }
  ];

  camButtons.forEach(({ id, preset }) => {
    const btn = document.getElementById(id);
    if (btn) {
      btn.addEventListener('click', () => {
        cameraPresets.setPreset(preset);
        camButtons.forEach((b) => {
          document.getElementById(b.id)?.classList.toggle('active', b.id === id);
        });
      });
    }
  });

  const toggleUI = (force) => {
    const isHidden = typeof force === 'boolean'
      ? force
      : document.body.classList.toggle('cinematic-ui-hidden');
    if (typeof force === 'boolean') {
      document.body.classList.toggle('cinematic-ui-hidden', isHidden);
    }
    const btnHide = document.getElementById('btn-hide-ui');
    if (btnHide) {
      const dict = i18n.getDictionary();
      btnHide.textContent = isHidden ? dict.controls.showUi : dict.controls.hideUi;
    }
  };

  const btnHideUi = document.getElementById('btn-hide-ui');
  if (btnHideUi) {
    btnHideUi.addEventListener('click', () => toggleUI());
  }

  window.addEventListener('keydown', (e) => {
    if (e.key.toLowerCase() === 'h') {
      toggleUI();
    }
  });

  const btnCheckmateReplay = document.getElementById('btn-checkmate-replay');
  if (btnCheckmateReplay) {
    btnCheckmateReplay.addEventListener('click', () => {
      const turn = gameState.getTurn();
      const kingPos = ChessRules.findKing(gameState.getBoard(), turn);
      if (kingPos) {
        const piece = gameState.getBoard()[kingPos.row][kingPos.col];
        if (piece) {
          const m = pieceRenderer.getMesh(piece.id);
          if (m) {
            m.rotation.z = 0;
            animator.startKingFall(m);
          }
        }
      }
    });
  }

  const btnCheckmateNewgame = document.getElementById('btn-checkmate-newgame');
  if (btnCheckmateNewgame) {
    btnCheckmateNewgame.addEventListener('click', () => {
      gameController.resetGame();
    });
  }

  const btnCheckmateDismiss = document.getElementById('btn-checkmate-dismiss');
  if (btnCheckmateDismiss) {
    btnCheckmateDismiss.addEventListener('click', () => {
      document.getElementById('checkmate-overlay')?.classList.remove('visible');
    });
  }

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  window.wizardChess = {
    toggleUI,
    getState: () => gameState.getSnapshot(),
    reset: () => gameController.resetGame(),
    aiMove: () => gameController.triggerAiMove()
  };

  initHostBridge(gameController);

  const clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);
    const delta = clock.getDelta();

    for (const u of flameUniforms) {
      if (u.uTime) {
        u.uTime.value += delta;
      }
    }

    for (const pl of brazierLights) {
      const base = pl.userData.baseIntensity || 4.35;
      pl.intensity = base + (Math.random() - 0.5) * 0.65;
    }

    orbitControls.update();
    cameraPresets.update(delta);
    animator.update(delta);
    shatter.update(delta);
    inputManager.update(delta);
    renderer.render(scene, camera);
  }

  animate();
}
