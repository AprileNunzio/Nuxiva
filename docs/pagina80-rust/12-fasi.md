# 12 · Fasi, consegne e definizione di fatto

Ogni fase si chiude con: test verdi in locale (stesso set della CI: `cargo fmt --check`, `cargo clippy --workspace --locked -- -D warnings`, `cargo test --workspace --locked` in `native/`; `python -m unittest discover -s tests -t .` e `pyflakes` in `installer_wizard`; build di `client_web` quando toccato), controllo del limite di 500 righe, nessun testo letterale nei file UI toccati, e un **commit dettagliato in italiano e in inglese pubblicato su `main`**.

## Panoramica

| Fase | Nome | Dipende da | Rischio |
|------|------|------------|---------|
| F0 | Sicurezza immediata, misure di base, guardrail di CI | Nessuna | Basso |
| F1 | Dominio della scena e flusso a delta | F0 | Medio |
| F2 | Scheduler dei widget e renderer condiviso | F1 | Alto |
| F3 | Presenza e visibilità basata sul pubblico | F1 | Medio |
| F4 | Matrice dei permessi e policy ospiti | F0, F3 | Medio |
| F5 | Motore decisionale | F2, F3, F4 | Alto |
| F6 | Apprendimento continuo | F5 | Medio |
| F7 | Interazione a due mani in WASM | F2, F5 | Medio |
| F8 | App Sentinella | F3, F4 | Medio |
| F9 | Multi-schermo avanzato e descrittori di superficie | F1, F5 | Medio |
| F10 | Display immersivi e visore molecolare | F9 | Alto, futuro |

F3 e F4 possono procedere in parallelo a F2. F8 può partire subito dopo F4.

## F0 · Sicurezza immediata, misure di base, guardrail di CI

Implementa: 01 §4, 04 §3 passi 1-3, 08 §7, 13 §3.

| Consegna | File |
|----------|------|
| `ha_call_service` calcola la sensibilità per entità e passa dal percorso di conferma | `installer_wizard/features/home_assistant/tools.py` |
| Valutazione per capacità dei tool HOME generici per `guest` e `anonymous` | `installer_wizard/features/authz/capability.py` nuovo, `gate.py` |
| Conferma legata al parlante con `HeardLog` | `installer_wizard/features/home_assistant/commands.py`, `features/authz/heard.py` |
| Snapshot memoizzato per versione e serializzato una volta | `installer_wizard/backend/snapshot.py` |
| Eventi una tantum con cursore per client al posto di `holo_action` consumato | `installer_wizard/backend/display_events.py` nuovo |
| Errori di sezione registrati, nessun `except: pass` | `installer_wizard/backend/snapshot.py` |
| `perf.js` non crea più un contesto WebGL proprio | `installer_wizard/web/display/perf.js` |
| Script di CI per il limite di 500 righe sui file sorgente | `scripts/ci/line_limit.py`, `.github/workflows/ci.yml` |
| Split di `spatial-core/src/lib.rs` sotto 500 righe | `native/crates/spatial-core/src/` |
| Banco di prova: scenario pagina 80 con 12 widget e 3 schermi, misure di heap, GPU, frame, byte trasmessi | `scripts/bench/page80/` |

Definizione di fatto: test di regressione «ospite chiede sblocco porta all'agente → negato»; due schermi ricevono entrambi un'azione olografica; numeri di base del banco salvati in `docs/pagina80-rust/bench/baseline.md`.

## F1 · Dominio della scena e flusso a delta

Implementa: 02 §3-§5, 04.

| Consegna | File |
|----------|------|
| Crate `display-domain` | `native/crates/display-domain/` |
| Crate `display-stream`: sezioni versionate, delta, broadcast, eventi con cursore | `native/crates/display-stream/` |
| Binario `nuxiva-display` con socket Unix, `SO_PEERCRED`, CBOR, unit systemd con hardening | `native/crates/display-daemon/`, `scripts/os/systemd/nuxiva-display.service` |
| Binding PyO3 modulo `display` | `native/crates/nuxiva-native/src/display.rs` |
| Proxy WebSocket autenticato `nuxiva.display.v1` dietro `NUXIVA_DISPLAY_STREAM` | `installer_wizard/backend/display_stream_api.py` |
| Client browser `transport/` con applicazione dei delta e fallback SSE | `installer_wizard/web/display/transport/` |
| Token di schermo firmati e accoppiamento | `installer_wizard/features/desktop/pairing.py`, `token-core` |

Definizione di fatto: con 4 client i byte trasmessi per modifica scendono rispetto alla base di F0 (obiettivo in 13); test di resync, client lento, versioni sfasate.

## F2 · Scheduler dei widget e renderer condiviso

Implementa: 03.

| Consegna | File |
|----------|------|
| Crate `display-scheduler` con ruota temporale e ciclo di vita | `native/crates/display-scheduler/` |
| Sorgenti condivise tra schermi e coalescenza | `native/crates/display-stream/src/sources/` |
| Kernel browser a corsie, ciclo di vita DOM, ibernazione | `installer_wizard/web/display/kernel/` |
| Renderer condiviso WebGL2 con scene, cache e atlas; worker con `OffscreenCanvas` dove disponibile | `installer_wizard/web/display/renderer/` |
| Migrazione di `avatar.js`, `particles.js`, `scene/` a scene del renderer | `installer_wizard/web/display/nucleus/` |
| Migrazione di `studio_3d` e `viewer_3d` a `ctx.scene()` | `installer_wizard/widgets/studio_3d/`, `viewer_3d/` |
| Misure di costo per widget e qualità foveale | `installer_wizard/web/display/kernel/metrics/` |
| Passaggio di `display.html` a moduli ES con gestore globale degli errori | `installer_wizard/web/display/boot/` |

Definizione di fatto: un solo contesto GPU per schermo; con 12 widget live la memoria rispetta l'obiettivo di 13; nessuna regressione visiva negli scenari dorati (screenshot Playwright).

## F3 · Presenza e visibilità basata sul pubblico

Implementa: 07.

| Consegna | File |
|----------|------|
| Crate `presence-core` con fusione, isteresi asimmetrica, pubblico per schermo | `native/crates/presence-core/` |
| Adattatori da visione, voce, `HeardLog`, dispositivi | `installer_wizard/features/desktop/presence_bridge.py` |
| Otturatore privacy nel browser | `installer_wizard/web/display/presence/` |
| Scena vuota con solo nucleo e rilascio risorse | `display-scheduler`, `web/display/kernel/` |
| Impostazioni nuove con chiavi i18n | `installer_wizard/features/desktop/feature.json`, `language/` |

Definizione di fatto: tabella di verità di 07 §3 coperta; otturatore entro l'obiettivo di 13; test di guasto fail-closed.

## F4 · Matrice dei permessi e policy ospiti

Implementa: 08.

| Consegna | File |
|----------|------|
| Crate `access-core` con capacità, matrice, verdetti | `native/crates/access-core/` |
| Matrice di default e file firmato | `native/crates/access-core/src/matrix/`, `/etc/nuxiva/access/matrix.json` |
| Integrazione in `features/authz/gate.py` per tutti i tool e i comandi vocali | `installer_wizard/features/authz/` |
| Risposte neutre per ospiti come chiavi i18n | `installer_wizard/features/authz/language/` |
| Pannello di modifica della matrice con anteprima | `client_web/src/apps/...` app autorizzazioni esistente |

Definizione di fatto: test generati da ogni cella della matrice; test avversari di 08 §9 verdi.

## F5 · Motore decisionale

Implementa: 05.

| Consegna | File |
|----------|------|
| Crate `display-planner` completo | `native/crates/display-planner/` |
| Campi `category`, `sensitivity`, `cadence`, `exclusive`, `media` nei `widget.json` e tabella di migrazione per i 73 widget | `installer_wizard/widgets/*/widget.json`, `display-planner/src/migration.rs` |
| Applicazione del piano nel browser con animazioni FLIP e forme del nucleo | `installer_wizard/web/display/layout/`, `nucleus/` |
| Spiegazioni visibili nel pannello del desktop a widget | `installer_wizard/features/desktop/explain_api.py` |
| `governor.js limit()` sostituito dal planner | `installer_wizard/web/display/governor.js` |

Definizione di fatto: proprietà di 05 §6 verificate con proptest; piano entro l'obiettivo di tempo di 13; comportamento del nucleo identico a quello oggi in produzione negli scenari dorati.

## F6 · Apprendimento continuo

Implementa: 06.

| Consegna | File |
|----------|------|
| Crate `display-learner` con bandit, decadimento, guardrail | `native/crates/display-learner/` |
| Archivio sigillato per persona | `native/crates/display-learner/src/store/` |
| Raccolta segnali dal browser | `installer_wizard/web/display/kernel/feedback/` |
| Valutazione offline e metriche nel pannello | `installer_wizard/features/desktop/learning_api.py` |
| Reset per persona dal Gestore Identità | `client_web/src/apps/...` Gestore Identità |

## F7 · Interazione a due mani in WASM

Implementa: 09.

| Consegna | File |
|----------|------|
| `gesture-core` compilato a `wasm32` in `display-wasm` | `native/crates/display-wasm/` |
| Worker di visione e associazione mani-volto | `installer_wizard/web/display/hands/` |
| Hit-test, calibrazione, feedback senza cornici | `installer_wizard/web/display/hands/` |
| Rimozione del percorso landmark via server per gli schermi con WASM | `installer_wizard/features/hands/api.py` |

## F8 · App Sentinella

Implementa: 10.

| Consegna | File |
|----------|------|
| Crate `sentinel-core` | `native/crates/sentinel-core/` |
| Feature backend e collettori | `installer_wizard/features/sentinel/` |
| Attributi d'aspetto locali | `installer_wizard/features/vision/appearance.py` |
| App 8080 | `client_web/src/apps/sentinel/` |
| Ciclo di studio reale per `self.idle_study` collegato all'agenzia e alla memoria | `installer_wizard/features/sentinel/collectors/self_activity.py` e il modulo di apprendimento scelto |

## F9 · Multi-schermo avanzato e descrittori di superficie

Implementa: 04 §5, 11 §1, 11 §5.

| Consegna | File |
|----------|------|
| Crate `surface-core` | `native/crates/surface-core/` |
| Posizione fisica degli schermi e lancio tra schermi | `installer_wizard/features/desktop/screens.py`, `web/screen/` |
| Pubblico per stanza dello schermo | `presence-core` |

## F10 · Display immersivi e visore molecolare

Implementa: 11. Da pianificare in dettaglio dopo F9 con una revisione dedicata.

## Formato dei commit di fase

```
feat(pagina80): Fase N, <titolo in italiano> / Phase N, <title in English>

IT
Cosa cambia, perché, file principali, test eseguiti con i risultati,
limiti noti e passi successivi.

EN
What changes, why, main files, tests run with results,
known limits and next steps.
```
