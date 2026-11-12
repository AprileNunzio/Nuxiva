# Scacchi 3D / Wizard Chess 3D - Nuxiva Games Framework

[🇬🇧 English](#english) | [🇮🇹 Italiano](#italiano)

---

<a name="italiano"></a>
## 🇮🇹 Italiano

### Panoramica
**Scacchi 3D (Wizard Chess 3D)** è l'applicazione di scacchi immersiva nativa integrata nel framework giochi autonomo di **Nuxiva OS** (`giochi/scacchi-3d/`). L'applicazione combina un motore scacchistico completo con rendering WebGL tridimensionale ad alte prestazioni, ambientazione in cattedrale gotica, audio posizionale ed interazione sia tattile/mouse che vocale guidata dall'assistente cognitivo.

### Architettura e Stack Tecnologico
- **Frontend & Rendering**: React 19, TypeScript, Three.js, Vite.
- **Ambiente 3D**: Scena cattedrale gotica con illuminazione dinamica, ombre proiettate, candelabri, particelle volumetriche e modelli GLB ottimizzati per i pezzi.
- **Motore Scacchistico**: `wizardChessEngine.js` con validazione rigorosa dei movimenti, catture, scacco, scacco matto, patta e arrocco.
- **Integrazione Nuxiva OS**:
  - Rilevamento automatico tramite `GamesScanner` (`installer_wizard/features/games/games_scanner.py`).
  - Modalità doppio rendering: applicazione a finestra intera nel desktop WebOS o widget dedicato dockable nel layout anticolisione di `desk.js`.
  - Ridimensionamento automatico dell'assistente: all'apertura del gioco, l'orb olografico e l'assistente si comprimono per lasciare priorità visiva alla scacchiera.
  - Manifest dichiarativo (`manifest.json`) con comandi vocali multilingua registrati nell'intent router di Nuxiva.

### Struttura Directory
```text
giochi/scacchi-3d/
├── assets/                  # Modelli 3D GLB dei pezzi e texture
├── dist/                    # Bundle di produzione compilato da Vite
├── public/                  # Asset statici, icone e audio FX
├── src/
│   ├── features/            # Componenti modulari (cattedrale, pezzi, controlli)
│   ├── App.tsx              # Componente radice dell'applicazione
│   ├── main.tsx             # Entry point React
│   ├── styles.css           # Stili responsive HUD
│   └── wizardChessEngine.js # Motore logico di gioco
├── manifest.json            # Contratto autonomo Nuxiva Games
└── vite.config.ts           # Configurazione bundler
```

### Esecuzione e Sviluppo Locale
1. Installazione dipendenze:
   ```bash
   npm install
   ```
2. Avvio ambiente di sviluppo:
   ```bash
   npm run dev
   ```
3. Compilazione bundle per produzione:
   ```bash
   npm run build
   ```

---

<a name="english"></a>
## 🇬🇧 English

### Overview
**Scacchi 3D (Wizard Chess 3D)** is the native immersive chess application integrated within the autonomous **Nuxiva OS** games framework (`giochi/scacchi-3d/`). It delivers a high-performance 3D WebGL experience set inside a gothic cathedral, featuring positional audio, mouse/touch controls, and voice-commanded moves orchestrated by the Nuxiva cognitive assistant.

### Architecture & Technology Stack
- **Frontend & 3D Engine**: React 19, TypeScript, Three.js, Vite.
- **Gothic Cathedral Environment**: Real-time directional lighting, soft shadow mapping, chandeliers, atmospheric dust particles, and optimized GLB piece models.
- **Game Engine**: `wizardChessEngine.js` delivering move validation, en-passant, castling, promotion, check, checkmate, and stalemate states.
- **Nuxiva OS Integration**:
  - Autonomous discovery via `GamesScanner` (`installer_wizard/features/games/games_scanner.py`).
  - Dual presentation mode: full-screen WebOS window or dedicated desktop widget managed by `desk.js` anti-collision layout solver.
  - Assistant auto-minimization: launching the game triggers the assistant to compress, yielding primary focus to the board.
  - Declarative contract (`manifest.json`) exposing multilingual voice triggers directly to Nuxiva's intent pipeline.

### Directory Structure
```text
giochi/scacchi-3d/
├── assets/                  # 3D GLB piece models and PBR textures
├── dist/                    # Compiled production assets
├── public/                  # Audio FX, board textures, icons
├── src/
│   ├── features/            # Modular scene components (lighting, board, pieces)
│   ├── App.tsx              # Root application container
│   ├── main.tsx             # React bootstrap entrypoint
│   ├── styles.css           # Responsive HUD styling
│   └── wizardChessEngine.js # Core game logic and state engine
├── manifest.json            # Autonomous game contract for Nuxiva OS
└── vite.config.ts           # Vite build pipeline configuration
```

### Local Development & Build
1. Install dependencies:
   ```bash
   npm install
   ```
2. Start development server:
   ```bash
   npm run dev
   ```
3. Build production bundle:
   ```bash
   npm run build
   ```
