# 11 · Display immersivi e visione biomolecolare

Roadmap futura. L'architettura delle fasi precedenti viene progettata fin da subito per accogliere questi display senza riscritture.

## 1. Astrazione del display: `surface-core`

Ogni dispositivo che mostra contenuti è uno **schermo** con un descrittore di capacità. Il planner non sa se sta parlando con un monitor, un visore o un proiettore: legge il descrittore.

```rust
pub struct SurfaceDescriptor {
    pub kind: SurfaceKind,
    pub pixels: Size,
    pub refresh_hz: u16,
    pub stereo: bool,
    pub field_of_view_deg: Option<f32>,
    pub views: u16,
    pub input: InputCaps,
    pub gpu: GpuCaps,
    pub placement: Option<RoomPose>,
}

pub enum SurfaceKind {
    Monitor,
    XrHeadset,
    HoloQuilt,
    HoloPyramid,
    HoloFan,
    Cast,
}
```

| Tipo | Esempi | Come si collega |
|------|--------|-----------------|
| `Monitor` | Pagina 80, `/screen` | Browser kiosk, come oggi |
| `XrHeadset` | Meta Quest 3 e successivi | Browser del visore su `/xr`, WebXR `immersive-vr` o `immersive-ar` |
| `HoloQuilt` | Display light field multivista | Pagina `/screen?kind=quilt`, rendering multivista in un'unica texture «quilt» |
| `HoloPyramid` | Piramidi a effetto Pepper's ghost | Rendering di 4 viste ruotate a 90° |
| `HoloFan` | Ventole olografiche LED | Uscita video circolare su sfondo nero, contenuti senza sfondo |
| `Cast` | TV e proiettori comuni | Stream del canvas, sola visione |

La scelta di widget senza sfondo e senza bordi è già ideale per i display olografici: il nero è trasparente.

## 2. Meta Quest come schermo

### 2.1 Accoppiamento

1. Dal pannello admin si sceglie «Aggiungi visore»: compare un QR sul nucleo della pagina 80.
2. Il visore apre l'indirizzo del QR nel browser, che contiene un codice di accoppiamento monouso a 5 minuti.
3. Il server rilascia un token di schermo firmato con `token-core`, tipo `XrHeadset`, legato all'ID dispositivo e alla persona che ha approvato.
4. Accesso solo in rete locale o tramite la VPN di Nuxiva; TLS obbligatorio perché WebXR lo richiede.

### 2.2 Esperienza

- Il nucleo diventa una presenza volumetrica nello spazio, con le stesse forme (`CoreHero`, `FloatingOrb`, `AmbientStream`, `WhisperPill`).
- I widget sono pannelli fluttuanti senza cornice disposti su un arco davanti all'utente; il planner usa una griglia cilindrica invece di una piana.
- Input: mani del visore (WebXR Hand Input) mappate sullo stesso vocabolario di gesti di 09, tramite `gesture-core` in WASM; controller come alternativa.
- Modalità passthrough: i widget si ancorano a superfici reali (un modello 3D appoggiato sul tavolo).

### 2.3 Prestazioni

- Rendering stereo a 72-90 Hz con foveazione fissa del visore attiva.
- Budget: il visore riceve dal daemon un budget più severo (memoria e draw call) e il planner riduce i widget simultanei.
- Contenuti pesanti (molecole, progetti 3D grandi) preparati dal server in LOD e stream progressivo (§3.3).

## 3. Visione biomolecolare immersiva

### 3.1 Obiettivo

Visualizzare strutture biomolecolari (proteine, acidi nucleici, complessi, ligandi) in modo dettagliato e immersivo, su monitor, ologrammi e visori, con interazione a due mani.

### 3.2 Crate `molecule-core`

| Modulo | Responsabilità |
|--------|----------------|
| `parse/pdb.rs`, `parse/mmcif.rs` | Parsing robusto di PDB e mmCIF con limiti di dimensione e validazione stretta |
| `model/` | Atomi, residui, catene, legami, metadati |
| `secondary/` | Strutture secondarie (eliche, foglietti) da DSSP semplificato se assenti nel file |
| `surface/` | Superficie molecolare (SES) con griglia distanze e marching cubes |
| `lod/` | Livelli di dettaglio: atomi completi, scheletro, cartoon, superficie semplificata |
| `export/` | Mesh compresse (glTF con meshopt) e buffer di impostori per il browser |

Calcoli pesanti nel daemon o in un worker di sistema con `rayon`, mai nel browser.

### 3.3 Rendering

- **Impostori**: sfere e cilindri disegnati come quad con ray casting nel fragment shader. Milioni di atomi con memoria minima perché ogni atomo è un punto con raggio e colore.
- **Cartoon e superfici**: mesh pre-calcolate a più LOD, caricate in modo progressivo.
- **Effetti**: occlusione ambientale in screen space, profondità di campo leggera, bordo luminoso per la selezione; tutto regolato dal tier di qualità di 03 §4.3.
- WebGPU dove disponibile per compute shader (occlusione, selezione), WebGL2 come base.

### 3.4 Interazione

| Gesto | Azione |
|-------|--------|
| Due mani: allarga, ruota, trasla | Zoom, rotazione, pan della molecola |
| Indice puntato e pizzico | Seleziona residuo o atomo, mostra etichetta senza sfondo |
| Voce | «Mostra la superficie», «colora per idrofobicità», «isola il sito attivo», «confronta con la struttura X» |
| Lancio verso un altro schermo | Porta la vista sul proiettore olografico o sul visore |

### 3.5 Sicurezza

- File caricati solo da cartelle condivise dell'utente o da fonti pubbliche configurate (per esempio archivi di strutture pubbliche) tramite il proxy di egress esistente (`egress`, `netguard`).
- Parser fuzzato in CI (`cargo fuzz`) prima di accettare file esterni.

## 4. Ologrammi a più viste

- Il renderer condiviso (03 §5) espone una **camera multivista**: per `HoloQuilt` disegna N viste in una texture a quilt in un solo passaggio con istanziazione; per `HoloPyramid` quattro viewport ruotati.
- Le scene sono le stesse dei widget 3D: un modello visto sul monitor si «lancia» sul proiettore senza conversioni.
- Il descrittore indica numero di viste e calibrazione del dispositivo, letta dal file fornito dal produttore e validata.

## 5. Che cosa preparare già nelle prime fasi

| Requisito futuro | Scelta da fare subito |
|------------------|-----------------------|
| Display diversi dai monitor | `surface-core` e descrittori di capacità nel `hello` del protocollo (04 §4) |
| Griglie non piane | Il planner lavora su una griglia astratta con metrica fornita dal descrittore |
| Input diversi | Gli eventi di input sono semantici (`select`, `move`, `scale`), non legati al mouse |
| Contenuti 3D pesanti | Renderer condiviso con scene, LOD e caricamento progressivo |
| Accoppiamento di dispositivi | Token di schermo firmati fin dalla Fase 1 |

## 6. Rischi specifici

| Rischio | Mitigazione |
|---------|-------------|
| Supporto WebXR diverso tra versioni del browser del visore | Rilevamento capacità e degrado a pannello 2D |
| Calore e batteria del visore | Budget dedicato e qualità adattiva |
| Esposizione di dati personali nel visore condiviso | Il visore segue le stesse regole di pubblico: senza persona autorizzata riconosciuta al visore, solo nucleo |
| Formati olografici proprietari | Supporto tramite descrittori, nessuna dipendenza da SDK chiusi nel nucleo del sistema |
