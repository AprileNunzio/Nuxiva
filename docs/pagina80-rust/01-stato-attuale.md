# 01 · Stato attuale e criticità

Audit eseguito su `main` @ `7b49234` il 2026-11-05. Ogni punto indica il file da cui nasce, così chi implementa può verificarlo.

## 1. Mappa della pagina 80 oggi

| Area | Dove vive | Note |
|------|-----------|------|
| Pagina principale | `installer_wizard/web/display/display.html` + 52 script caricati in sequenza | Circa 6.100 righe JS nella sola cartella `display`, tutto su `window` |
| Desktop a widget | `web/display/desk.js` (468 righe), `desk_kit.js`, `desk_touch.js` | Caricamento pigro di `widgets/<id>/widget.js` e CSS per revisione |
| Widget | `installer_wizard/widgets/<id>/` (73 cartelle) | `widget.json` con `priority`, `size`, `ttl`, `refresh`, `chrome:false`, a volte `cost` |
| Schermi aggiuntivi | `web/screen/` (`grid.js`, `pager.js`, `map.js`) | Ruoli `agent`, `work`, `visual`, `person` da `features/desktop/screens.py` |
| Governatore lato browser | `web/display/governor.js` | Tier `full`/`reduced`/`minimal`, budget a pesi, `limit()` chiamato da `desk.js` |
| Governatore lato server | `features/governor/` | Pressione da CPU, RAM, swap, carico; slot per tipo di lavoro |
| Regia del nucleo | `web/display/director.js`, `stage.js`, `voice_strip.js` | Regola del nucleo che si sposta o diventa solo voce alla fine di `desk.js layout()` |
| Effetti | `particles.js` (WebGL2), `avatar.js` (WebGL), `scene/` e `scene/holo/` (three.js), `ambient.js` (2D) | Ogni effetto crea il proprio contesto grafico |
| Mani | `hands.js`, `hands_bridge.js`, `hands_events.js`, `hands_gesture.js` + `native/crates/gesture-core` (incluso `duo.rs` per due mani) | Profilo gesti cifrato in `features/hands/store.py`, `NUXIVA_HANDS_COUNT` |
| Presenza | `features/people/presence.py`, `features/vision/tracks.py`, `features/ear/voiceprint.py` | Volti noti e sconosciuti, voce con punteggio dello speaker |
| Privacy display | `features/desktop/privacy.py` | Chiusura automatica dei dati personali dopo `NUXIVA_PRIVACY_AWAY_S` (10 s) |
| Autorizzazione | `features/authz/` (`risk.py`, `policy.py`, `principal.py`, `heard.py`) | Rischio per tool: INFO, HOME, PERSONAL, FILES, CRITICAL |
| Privacy dei dati verso i modelli | `features/brain/privacy/` | Livelli public, personal, sensitive per persona |
| Stato verso i client | `installer_wizard/backend/snapshot.py` | SSE con snapshot completo |
| Rust già presente | `native/crates/stage-core`, `spatial-core`, `gesture-core`, `vitals-core`, `bus-core`, `admin-os`, `nuxiva-native` (PyO3) | `spatial-core` ha già arbitro, livelli Z, priorità notifiche, governatori |

## 2. Colli di bottiglia misurabili

### 2.1 Snapshot completo per ogni client e per ogni modifica

`backend/snapshot.py:sse()` controlla ogni 0,5 s se `store.version` è cambiata e in quel caso ricalcola `full_snapshot()` per ogni client connesso e serializza l'intero JSON. Con 1 pagina 80 e 3 schermi aggiuntivi lo stesso snapshot viene costruito e serializzato 4 volte per ogni modifica, e trasmesso intero anche se è cambiato un solo campo. Il costo cresce come `client × modifiche × dimensione dello snapshot`.

### 2.2 Eventi una tantum consumati dal primo client

In `full_snapshot()` il campo `holo_action` viene letto e poi cancellato con `delattr(store, "holo_action")`. Con più schermi solo il primo client che ricalcola lo snapshot riceve l'azione olografica, gli altri la perdono. È un difetto funzionale del multi-schermo, non solo di prestazioni.

### 2.3 Troppi contesti grafici

Contesti WebGL creati in modo indipendente: `avatar.js`, `particles.js`, `scene/scene.js`, `widgets/studio_3d`, `widgets/viewer_3d`, più la sonda di `perf.js` che crea un contesto e non lo rilascia (a differenza di `governor.js` che usa `WEBGL_lose_context`). Ogni contesto ha i propri buffer, texture e shader compilati. I browser limitano i contesti attivi (tipicamente 16) e ne perdono il più vecchio quando il limite è superato. Con più widget 3D aperti questo porta a schermate nere e a memoria GPU duplicata.

### 2.4 Nessun ciclo di vita per i widget

`desk.js` monta e smonta il DOM ma non esiste uno stato intermedio: un widget nascosto o fuori dalla pagina corrente di `/screen` non sospende in modo uniforme timer, animazioni e rendering. Gli script dei widget restano caricati e le cadenze `refresh` sono gestite da ciascun widget.

### 2.5 Sorgenti dati duplicate tra schermi

Ogni schermo chiede i propri dati: se lo stesso widget meteo o la stessa telecamera sono su due schermi, la sorgente viene interrogata o decodificata due volte.

### 2.6 Governatore senza memoria reale

`governor.js` stima il budget da pesi dichiarati (`weight`, `cost`) e dal numero di apparizioni. Non misura memoria JS reale (`performance.measureUserAgentSpecificMemory` dove disponibile), memoria GPU per contesto o tempo di frame per widget. `perf.js` misura FPS e p95 ma a livello di pagina, non di singolo widget.

## 3. Debiti tecnici rispetto alle direttive

| Debito | Dove | Azione nel piano |
|--------|------|------------------|
| File oltre 500 righe | `native/crates/spatial-core/src/lib.rs` (521) e altri fuori dalla pagina 80 (`client_web/src/apps/music/View.tsx` 1788, `iptv/View.tsx` 1476, `widgets/lavagna/widget.js` 688) | Fase 0: controllo di CI sul limite, split di `spatial-core/lib.rs`; gli altri restano in un registro dedicato |
| Errori soppressi in silenzio | `backend/snapshot.py` (`except Exception: pass` su `display_settings`, `except Exception` su suoni e particelle) | Sostituiti dal nuovo assemblatore di stato con errori registrati e campo di salute per sezione |
| Testi letterali in Python e JS | `features/people/presence.py` (`describe`, saluti), messaggi di `perf.js` e `governor.js` | Chiavi i18n nei moduli toccati dalle fasi |
| Tutto su `window` | 52 script globali in `display.html` | Moduli ES con registro dei servizi, vedi 02 |

## 4. Falle di sicurezza da chiudere subito

### 4.1 Comandi Home Assistant sensibili senza conferma dal percorso dell'agente

`features/home_assistant/tools.py:ha_call_service` costruisce il piano con `"sensitive": False` fisso e chiama `brain.execute()` direttamente. Il percorso vocale classico (`commands.py`) invece usa `is_sensitive()` e chiede conferma per `lock.unlock`, `lock.open`, `alarm_control_panel.alarm_disarm`, coperture sensibili e valvole. Dal percorso dell'agente quindi un'apertura serratura non passa dalla conferma.

### 4.2 Gli ospiti e le voci anonime hanno tetto HOME

In `features/authz/policy.py` `DEFAULT_CEILING` assegna `Risk.HOME` a `guest` e `anonymous`, e `Risk.HOME` non richiede prova (`Strength.NONE`). Nel gruppo HOME ci sono `ha_call_service`, `run_automation`, `toggle_automation`, `emit_event`, `agent_tell`, `ceo_delegate`, `show_model`. Unito a 4.1, una voce non riconosciuta può chiedere all'agente un servizio Home Assistant qualsiasi, compreso lo sblocco di una serratura.

### 4.3 La conferma vocale non è legata a chi ha chiesto

In `features/home_assistant/commands.py` la conferma (`self.pending`, metodo `handle(text)`) accetta «conferma» entro la finestra guardando solo il testo: a questo livello non viene verificato che la voce sia la stessa che ha chiesto il comando.

Queste tre correzioni sono la prima consegna della Fase 0 (vedi 12) e vengono trattate in dettaglio in 08. Il principio: il rischio non si valuta solo per tool, ma per capacità concreta (dominio, servizio, entità, stanza), e le capacità sensibili richiedono una persona autorizzata con prova forte.

## 5. Punti di forza da riusare

- `spatial-core`: `PriorityArbiter`, `ZLayer` Z0-Z4, `SafeZone`, `AssistantMorphology`, `resource_governor`, `task_governor`. Sono la base del motore decisionale.
- `stage-core/director.rs`: stati `Shown`/`Min`/`Hidden` con soglie e isteresi per le superfici della regia.
- `gesture-core`: landmark, smoothing, pose, `duo.rs` con scala, rotazione e pan a due mani, profili.
- `token-core`: HMAC e codifica per token firmati, utile per l'accoppiamento di schermi e visori.
- `features/authz`: modello `Principal` con `Strength` e `HeardLog` per legare un comando alla voce che l'ha detto.
- `features/brain/privacy`: livelli di sensibilità per persona, già fail-closed.
- `features/desktop/screens.py`: ruoli degli schermi e assegnazione per tipo di widget.
- Lint di workspace già severi: `unsafe_code = "forbid"`, `unwrap_used`, `expect_used`, `panic`, `indexing_slicing`, `arithmetic_side_effects` vietati.

## 6. Conclusione dell'audit

Il collo di bottiglia principale non è il linguaggio ma la forma: stato completo ricalcolato per client, contesti grafici moltiplicati, assenza di ciclo di vita e di sorgenti condivise. Portare a Rust la parte decisionale e di distribuzione dello stato, e unificare il rendering nel browser, dà il guadagno di memoria richiesto senza togliere effetti. Il resto del piano parte da qui.
