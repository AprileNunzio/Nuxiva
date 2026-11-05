# 03 · Scheduler dei processi e dei widget

Obiettivo: più widget live contemporaneamente, aggiornati in tempo reale, con memoria che cresce poco al crescere dei widget e degli schermi, senza togliere effetti grafici.

## 1. Due scheduler, un solo modello

| Scheduler | Dove | Cosa schedula |
|-----------|------|---------------|
| `display-scheduler` | Daemon Rust | Aggiornamenti dei dati, cadenze delle sorgenti, transizioni di ciclo di vita, contabilità del budget per schermo |
| `kernel` | Browser | Frame di rendering per corsia, montaggio e smontaggio DOM, risorse GPU, ibernazione |

Entrambi condividono gli stessi stati e gli stessi identificatori, definiti in `display-domain`.

## 2. Ciclo di vita del widget

```
            ┌──────────┐ candidato scelto ┌────────┐ superficie visibile ┌────────┐
 manifest ─▶│ Dormant  │─────────────────▶│  Warm  │────────────────────▶│  Live  │
            └──────────┘                  └────────┘                     └────────┘
                 ▲    scaduto o escluso     │    ▲        fuori vista       │   ▲
                 └──────────────────────────┘    │      o pagina diversa   ▼   │ torna in vista
                                                 │                     ┌────────┐
                                                 └─────────────────────│ Frozen │
                                                   memoria sotto soglia └────────┘
                                                                            │ inattivo oltre T
                                                                            ▼
                                                                      ┌────────────┐
                                                                      │ Hibernated │
                                                                      └────────────┘
```

| Stato | Memoria tenuta | Aggiornamenti | Rendering |
|-------|----------------|---------------|-----------|
| Dormant | Solo manifest nel daemon | Nessuno | Nessuno |
| Warm | Ultimo dato nel daemon, nessun DOM | Alla cadenza ridotta della sorgente | Nessuno |
| Live | DOM, risorse GPU nel renderer condiviso | Cadenza piena | Corsia assegnata |
| Frozen | DOM e risorse, timer fermi | Accumulati e coalesciati, applicati al ritorno | Fermo, ultimo frame mantenuto |
| Hibernated | Bitmap del frame (`ImageBitmap` ridotto), DOM rilasciato, risorse GPU rilasciate | Come Warm | Solo la bitmap, ripristino con transizione |

Transizioni guidate da: piano di scena, visibilità reale (IntersectionObserver e pagina corrente di `/screen`), pressione di memoria, pubblico (vedi 07). Con pubblico `Empty` o `GuestOnly` tutti i widget personali passano a Dormant dopo il periodo di grazia, così memoria e privacy sono protette insieme.

## 3. Cadenze di aggiornamento

### 3.1 Classi di cadenza

| Classe | Esempi | Cadenza Live | Cadenza Warm |
|--------|--------|--------------|--------------|
| `realtime` | spettro audio, gesti, telecamera | Flusso continuo, frame del browser | Sospeso |
| `live` | musica in riproduzione, sport live, risorse di sistema | 1 s | 10 s |
| `fresh` | Home Assistant, sincronizzazione connettori, attività | 5 s o su evento | 60 s |
| `slow` | meteo, notizie, calendario | Su evento o `refresh` del manifest | Su evento |
| `static` | documento, modello 3D, lavagna | Solo su modifica | Nessuno |

La classe si deduce da `refresh` e `ttl` del `widget.json` esistente e può essere dichiarata esplicitamente con un nuovo campo `cadence`.

### 3.2 Coalescenza e deduplica

- Una sola sottoscrizione per sorgente nel daemon, condivisa da tutti gli schermi e da tutti i widget che la usano. Il meteo su due schermi interroga la sorgente una volta.
- Gli aggiornamenti ravvicinati della stessa sorgente vengono fusi nella finestra della classe (per `fresh` 250 ms), così una raffica di stati Home Assistant produce un solo delta.
- Uno stesso dato non cambiato non genera delta (confronto per hash xxh3 del valore normalizzato).

### 3.3 Timer

Nel daemon una sola ruota temporale gerarchica (hierarchical timing wheel) gestisce tutte le scadenze: costo O(1) per inserimento e scatto, nessun thread per widget. Nel browser i widget non usano `setInterval`: chiedono al kernel una cadenza e ricevono callback allineate al frame o alla classe.

## 4. Budget di risorse per schermo

### 4.1 Misure reali

| Misura | Fonte |
|--------|-------|
| Memoria JS | `performance.measureUserAgentSpecificMemory()` quando l'isolamento cross-origin è attivo, altrimenti `performance.memory` dove esiste, altrimenti stima |
| Memoria GPU | Contabilità del renderer condiviso: somma di buffer, texture e render target allocati per scena |
| Tempo di frame per widget | `performance.now()` intorno alla callback della corsia, istogramma per widget |
| CPU e RAM del server | Governatore esistente (`features/governor`) |
| Memoria del daemon | RSS dal proprio processo, esposta in `/api/governor` |

Le misure vengono inviate al daemon ogni 5 s in forma aggregata. Il daemon aggiorna il costo appreso di ogni widget (media mobile esponenziale) e lo usa nel planner al posto del solo `cost` dichiarato.

### 4.2 Calcolo del budget

```
budget_gpu   = min(memoria_gpu_stimata × 0,6, tetto_impostazioni)
budget_js    = min(memoria_dispositivo × 0,25, tetto_impostazioni)
budget_frame = 1000 / refresh_display × 0,75
```

Il planner non supera mai il budget per i widget non forzati. Urgenze, allarmi e takeover restano forzati come oggi (`forced` in `governor.js`).

### 4.3 Qualità invece di rinuncia

Il tier del governatore oggi aggiunge la classe `lite` che toglie sfocature ed effetti. Il nuovo modello abbassa la qualità per gradi prima di togliere qualcosa:

| Leva | Pieno | Ridotto | Minimo |
|------|-------|---------|--------|
| Scala di risoluzione del render 3D | 1,0 × DPR | 0,75 | 0,5 con upscaling |
| Particelle del nucleo | 100 % | 50 % | 20 % |
| Ombre e post-processing | Attivi | Ombre statiche, bloom ridotto | Bloom solo sul nucleo |
| Frequenza dei widget non in focus | 60 fps | 30 fps | 15 fps |
| LOD dei modelli | Alto | Medio | Basso |
| Widget in focus | Sempre qualità piena | Sempre qualità piena | Qualità piena |

**Qualità foveale**: il widget su cui si trova lo sguardo stimato, il cursore della mano o l'ultima interazione resta in qualità piena; gli altri scalano. L'effetto «wow» resta dove l'utente guarda.

## 5. Renderer GPU condiviso

### 5.1 Un contesto per schermo

Un solo `WebGL2RenderingContext`, o `GPUDevice` WebGPU dove disponibile, per schermo, su un canvas a tutto schermo dietro il DOM. Avatar, particelle, scene three.js dei widget 3D, ologrammi e grafici GPU diventano **scene** registrate nel renderer:

- Ogni scena ha un viewport e uno scissor uguali alla superficie del widget, calcolati dal layout.
- Shader, geometrie e texture comuni vengono condivisi tramite cache con conteggio dei riferimenti.
- Atlas di texture per icone e glifi, per ridurre i cambi di stato.
- Le scene Frozen non vengono disegnate, quelle Hibernated rilasciano le risorse.

### 5.2 Worker di rendering

Dove il browser supporta `OffscreenCanvas` il renderer gira in un Web Worker: il thread principale resta libero per DOM, input e gesti. Il thread principale invia al worker solo superfici e comandi, mai oggetti grandi.

### 5.3 Compatibilità

- I widget `studio_3d` e `viewer_3d` passano a `ctx.scene()` nella fase di migrazione.
- `perf.js` smette di creare un contesto proprio: legge le informazioni GPU dal renderer condiviso.
- Il budget di contesti del browser non viene più raggiunto, perché i contesti sono sempre uno per schermo.

## 6. Scheduler dei frame nel browser

Tre corsie con priorità stretta:

| Corsia | Contenuto | Regola |
|--------|-----------|--------|
| `interactive` | Gesti, cursori, widget sotto la mano, risposta del nucleo | Sempre eseguita per prima, nessun salto |
| `live` | Widget Live visibili | Eseguita se resta budget nel frame |
| `ambient` | Particelle, sfondi, animazioni decorative | Saltata e recuperata al frame successivo se il budget è finito |

Lavoro non urgente (preparazione di traduzioni, decodifica di immagini, pre-caricamento script) va su `requestIdleCallback` o `scheduler.postTask` con priorità `background`.

## 7. Multi-schermo senza moltiplicare la memoria

- Ogni schermo riceve solo il proprio piano e i propri delta (vedi 04), non l'intero stato di tutti.
- Le sorgenti sono condivise nel daemon: il costo di una sorgente non dipende dal numero di schermi.
- Gli schermi in pagina diversa (paginazione di `/screen/pager.js`) tengono i widget non visibili in Frozen o Hibernated.
- Uno schermo che non invia segnali di vita per 30 s (già `ALIVE` in `screens.py`) libera le sue sottoscrizioni nel daemon.
- Lo stesso widget su due schermi condivide dato e decodifica nel daemon; nel browser ciascuno ha la propria scena perché i processi sono separati, ma con qualità scalata se non in focus.

## 8. Quarantena e salute dei widget

| Condizione | Azione |
|------------|--------|
| 3 errori in 60 s dallo stesso widget | Quarantena 5 minuti, superficie liberata, evento nel diario di sistema |
| Tempo di frame p95 del widget oltre 8 ms per 10 s | Declassato alla corsia `ambient` e qualità ridotta |
| Memoria del widget oltre il doppio del costo appreso | Ibernazione forzata e segnalazione |
| Script del widget non caricato | Errore tipizzato al gestore globale, il planner esclude il widget fino alla revisione successiva |

Nessun errore viene ignorato: tutto finisce nel gestore globale con il modulo di origine.

## 9. Interfaccia del crate `display-scheduler`

```rust
pub struct Scheduler<C: Clock> {
    wheel: TimingWheel,
    widgets: WidgetTable,
    budgets: BudgetTable,
    clock: C,
}

impl<C: Clock> Scheduler<C> {
    pub fn admit(&mut self, screen: ScreenId, plan: &ScenePlan) -> Vec<Transition>;
    pub fn tick(&mut self) -> Vec<Due>;
    pub fn observe(&mut self, sample: CostSample) -> Result<(), SchedulerError>;
    pub fn pressure(&mut self, screen: ScreenId, level: Pressure) -> Vec<Transition>;
}
```

Dominio puro: `Clock` iniettato, nessun thread interno, testabile con orologio simulato.
