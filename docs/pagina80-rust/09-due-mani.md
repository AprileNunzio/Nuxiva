# 09 · Interazione a due mani via webcam

Si attiva solo se l'utente l'ha abilitata nelle impostazioni (feature `hands`, oggi `NUXIVA_HANDS_COUNT` e profilo gesti sigillato in `features/hands/store.py`). L'obiettivo è un'interazione completa e affidabile su tutti i widget, il nucleo, le scene 3D e gli schermi multipli.

## 1. Pipeline attuale

```
webcam ─▶ MediaPipe HandLandmarker nel browser (hands.js)
       ─▶ landmark via WebSocket /api/hands/ws (hands_bridge.js)
       ─▶ gesture-core in Python tramite binding (features/hands/native.py)
       ─▶ eventi gesto via WebSocket ─▶ hands_events.js ─▶ widget
```

Limiti: un viaggio di andata e ritorno verso il server per ogni frame di landmark, latenza variabile, carico sul server proporzionale agli schermi con mani attive. In `hands_bridge.js` gli errori del socket e i messaggi non validi vengono ignorati in silenzio (`onerror` vuoto, `catch` che ritorna), da sostituire con il gestore globale.

## 2. Pipeline obiettivo

```
webcam ─▶ Worker di visione: HandLandmarker (GPU delegate) + selezione delle mani
       ─▶ display-wasm: gesture-core compilato a wasm32 (smoothing, pose, duo, pointer)
       ─▶ kernel: hit-test sul piano di scena corrente (display-wasm)
       ─▶ corsia interactive: cursori, feedback, azioni sul widget
       ─▶ input aggregato al daemon (solo eventi semantici, mai landmark)
```

- Tutto il riconoscimento resta nel browser dello schermo: latenza minima, nessun fotogramma e nessun landmark esce dal dispositivo.
- Il profilo gesti resta sigillato nel server e viene consegnato allo schermo autenticato all'avvio e a ogni revisione (`revision` già presente in `store.py`).
- `gesture-core` è lo stesso crate in Python, in WASM e nei test: una sola implementazione delle regole.

## 3. Chi può comandare con le mani

- Le mani vengono associate a una persona tramite la vicinanza tra il polso e la traccia del volto (box del volto da `features/vision/tracks.py` proiettato nello spazio della webcam dello schermo).
- Solo le mani di un membro autorizzato al display producono azioni. Le mani di un ospite possono usare solo comandi `public` (per esempio volume della musica, se la matrice lo consente, vedi 08).
- Con pubblico `Empty` o `GuestOnly` la pipeline delle mani scende a bassa frequenza (5 fps) solo per rilevare l'arrivo, poi torna piena quando arriva un autorizzato.

## 4. Vocabolario dei gesti

### 4.1 Una mano

| Gesto | Azione |
|-------|--------|
| Indice puntato | Cursore sul widget, evidenziazione morbida senza bordi (bagliore del testo e leggero ingrandimento) |
| Pizzico breve | Seleziona o attiva |
| Pizzico tenuto e trascinamento | Sposta il widget; il planner registra la posizione come preferenza |
| Palmo aperto verso lo schermo, fermo 0,6 s | Pausa (musica, video, scena 3D) |
| Spinta in avanti del palmo | Chiudi il widget sotto il cursore |
| Swipe orizzontale | Pagina successiva o precedente su `/screen` (`pager.js`), scorrimento nelle liste |
| Lancio verso un bordo | Sposta il widget sullo schermo fisicamente in quella direzione (04 §5.3) |
| Pugno chiuso tenuto 1 s | Annulla l'ultima azione |

### 4.2 Due mani (`duo.rs`)

| Gesto | Azione |
|-------|--------|
| Due pizzichi che si allontanano o si avvicinano | Ingrandisci o riduci widget e scene 3D |
| Due pizzichi che ruotano | Ruota modello 3D o ologramma sull'asse di vista |
| Due pizzichi che traslano insieme | Pan della scena |
| Una mano tiene, l'altra ruota | Orbita della camera attorno al modello |
| Mani aperte che si allargano | Apri il widget a tutto schermo (takeover) |
| Mani che si chiudono verso il centro | Torna alla scena normale, il nucleo riprende la forma decisa dal planner |

I gesti sono legati alle azioni tramite il profilo (`bindings`), modificabile dall'utente. I nomi delle azioni sono chiavi i18n.

## 5. Hit-test e coordinate

- Calibrazione per schermo: quattro punti indicati con l'indice al primo avvio, salvati nel profilo sigillato. In assenza di calibrazione si usa la mappatura lineare attuale.
- Il kernel mantiene un indice spaziale (R-tree piccolo) delle superfici del piano corrente; `display-wasm` risponde all'hit-test in microsecondi.
- Isteresi del cursore: il bersaglio cambia solo se il cursore resta 80 ms sul nuovo widget, per evitare tremolii al bordo.
- Area di cattura più grande dei widget piccoli (minimo 64 px logici), per accessibilità.

## 6. Feedback visivo senza cornici

- Cursore: piccolo punto luminoso con scia breve, colore del tema, nessun cerchio di contorno.
- Pizzico in corso: il punto si contrae; trascinamento con ombra morbida del widget, senza bordo.
- Scene 3D: gizmo minimale di rotazione che compare solo durante il gesto a due mani.
- Riconoscimento perso: il cursore svanisce in 200 ms, nessun messaggio a schermo.

## 7. Risorse e qualità

| Stato | Frequenza visione | Modello |
|-------|-------------------|---------|
| Mani disattivate | 0 | Non caricato |
| Nessun autorizzato | 5 fps | Leggero |
| Autorizzato presente, nessuna mano | 15 fps | Leggero |
| Mano rilevata | 30 fps, o 60 se la GPU lo permette | Completo |

Il worker di visione dichiara il proprio costo allo scheduler (03 §4), così il planner tiene conto della visione nel budget dello schermo.

## 8. Privacy e sicurezza

- Fotogrammi elaborati solo in memoria nel worker, mai salvati, mai inviati.
- Al daemon arrivano solo eventi semantici (`select`, `move`, `close`, `scale`), con identificatore della persona già pseudonimizzato.
- Lo stream della webcam si apre solo con l'impostazione attiva e viene chiuso quando la pagina non è visibile.
- Indicatore discreto vicino al nucleo quando la webcam è attiva per le mani.

## 9. Test

- `gesture-core`: i test esistenti (`engine_tests.rs`) girano anche sul target wasm32 in CI con `wasm-bindgen-test`.
- Registrazioni di landmark anonime (solo coordinate) come fixture per test di regressione dei gesti a due mani.
- Test end-to-end con Playwright e landmark sintetici iniettati nel worker: sposta, ridimensiona, ruota un modello 3D, lancia un widget su un altro schermo.
- Prestazioni: dalla posa della mano all'aggiornamento del cursore sotto 50 ms al 95° percentile sull'hardware di riferimento (vedi 13).
