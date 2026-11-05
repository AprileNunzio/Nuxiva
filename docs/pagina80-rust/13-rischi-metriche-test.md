# 13 · Rischi, metriche e strategia di test

## 1. Registro dei rischi

| # | Rischio | Probabilità | Impatto | Mitigazione | Responsabile |
|---|---------|-------------|---------|-------------|--------------|
| R1 | Regressioni visive migrando avatar, particelle e 3D al renderer condiviso | Alta | Alto | Screenshot di riferimento Playwright per ogni scenario dorato, migrazione per scena, feature flag per tornare al percorso attuale | F2 |
| R2 | Browser del kiosk senza `OffscreenCanvas` o WebGPU | Media | Medio | Rilevamento capacità, renderer sul thread principale come base, WebGL2 come minimo | F2 |
| R3 | Falsi negativi nel riconoscimento che nascondono la scena al proprietario | Media | Medio | Tenuta con voce, isteresi, comando vocale «sono io» con prova, metriche di falso rifiuto | F3 |
| R4 | Falsi positivi che mostrano dati personali a un ospite | Bassa | Molto alto | Asimmetria apri lento e chiudi subito, liveness, `Uncertain` trattato come restrittivo, test avversari | F3 |
| R5 | Matrice permessi troppo restrittiva per l'uso quotidiano | Media | Medio | Matrice modificabile dal proprietario con anteprima, telemetria locale dei rifiuti | F4 |
| R6 | Instabilità del layout percepita come «schermo che balla» | Media | Medio | Isteresi, permanenza minima, costo di spostamento, test di stabilità | F5 |
| R7 | Il learner impara abitudini sbagliate | Media | Basso | Contributo limitato, valutazione offline, reset per persona | F6 |
| R8 | Doppio percorso (Python e Rust) che diverge durante la migrazione | Alta | Medio | Feature flag con durata limitata a due release, test di equivalenza sugli stessi input | F1-F5 |
| R9 | Attributi d'aspetto errati nella Sentinella | Media | Basso | Soglia di confidenza alta, attributo omesso se incerto | F8 |
| R10 | Questioni legali sulla registrazione di ospiti | Media | Alto | Minimizzazione, conservazione breve, avviso agli ospiti, nessuna immagine salvata | F8 |
| R11 | Complessità di build `wasm32` e dimensione del modulo | Media | Basso | `wasm-opt -Oz`, caricamento pigro, budget di dimensione in CI | F7 |
| R12 | Daemon come punto singolo di guasto | Bassa | Alto | Fail-closed con solo nucleo, riavvio systemd, fallback SSE Python durante la migrazione | F1 |

## 2. Metriche e obiettivi

Gli obiettivi sono valori da verificare sul banco di prova; i numeri reali di partenza vengono misurati in F0 e scritti in `docs/pagina80-rust/bench/baseline.md`. Se la base misurata rende un obiettivo irrealistico o banale, l'obiettivo viene ricalibrato e il motivo scritto nello stesso file.

### 2.1 Hardware di riferimento

- **Server di riferimento**: il mini PC di casa che esegue Nuxiva (CPU x86-64 con AVX2, 16 GB RAM, GPU integrata).
- **Schermo di riferimento**: kiosk Chromium 1080p a 60 Hz, più tre schermi aggiuntivi `/screen`.

### 2.2 Obiettivi

| Metrica | Obiettivo | Come si misura |
|---------|-----------|----------------|
| Memoria JS pagina 80 con 12 widget live | −40 % rispetto alla base | `measureUserAgentSpecificMemory` nel banco |
| Memoria GPU pagina 80 con 2 widget 3D, avatar e particelle | −35 % rispetto alla base | Contabilità del renderer contro stima base |
| Contesti GPU per schermo | 1 | Contatore del renderer |
| Memoria aggiuntiva per ogni schermo `/screen` in più (lato server) | sotto 5 MB | RSS del daemon con 1 e 4 schermi |
| Byte trasmessi per modifica con 4 schermi | −90 % rispetto alla base | Contatore del trasporto |
| CPU del server per lo stato display con 4 schermi | −70 % rispetto alla base | `perf stat` sul processo durante lo scenario |
| Tempo di frame p95 in tier pieno con 12 widget | sotto 16,6 ms | `perf.js` per widget e pagina |
| Tempo del planner, 4 schermi e 100 candidati | sotto 2 ms p99 | Benchmark `criterion` |
| Otturatore privacy dall'apparizione del volto alla scomparsa dei dati | sotto 300 ms p95 | Banco con flusso video registrato |
| Ripristino della scena al ritorno del proprietario | sotto 1 s | Banco |
| Latenza gesto → cursore | sotto 50 ms p95 | Landmark sintetici con timestamp |
| RSS del daemon `nuxiva-display` | sotto 40 MB | `/proc/self/status` |
| Scrittura evento Sentinella | sotto 200 µs | Benchmark `criterion` |
| Falso accesso di un ospite a capacità 🔒 | 0 nei test avversari | Suite avversaria |

## 3. Strategia di test

### 3.1 Piramide

| Livello | Strumenti | Copertura attesa |
|---------|-----------|------------------|
| Unità Rust | `cargo test`, `proptest` | Dominio e casi d'uso sopra 90 % di righe con `cargo llvm-cov` |
| Proprietà | `proptest` | Invarianti di planner, presenza, accesso |
| Benchmark | `criterion` | Planner, scheduler, delta, Sentinella |
| Fuzzing | `cargo fuzz` | Protocollo CBOR, delta, parser molecolari, matrice permessi |
| Unità Python | `unittest` esistente | Adattatori e API nuove |
| Contratto | Test che confrontano binding PyO3 e schema del protocollo | Tutti i messaggi di `nuxiva.display.v1` |
| WASM | `wasm-bindgen-test` | `gesture-core` e hit-test |
| End-to-end | Playwright con Chromium preinstallato | Scenari dorati e screenshot |
| Conformità widget | Test che carica ogni widget e verifica: nessun contesto WebGL proprio, nessun `setInterval`, chiavi i18n in 4 lingue, `chrome:false`, nessun sfondo o bordo nel CSS | Tutti i 73 widget |
| Sicurezza | Test avversari di 08 §9, controllo dipendenze con `cargo deny` e `pip-audit` | Ogni fase |

### 3.2 Scenari dorati

1. Pagina 80 vuota: solo nucleo `CoreHero`.
2. Proprietario arriva: scena personale completa.
3. Conversazione con meteo e musica: tre widget, nucleo intero.
4. Progetto 3D su schermo `work` con due mani: rotazione e zoom.
5. Ospite entra mentre il proprietario guarda la salute: otturatore.
6. Ospite chiede musica e luci: eseguito; chiede di sbloccare la porta: negato con risposta neutra.
7. Spazio insufficiente: nucleo `FloatingOrb`, poi `AmbientStream`.
8. Takeover video: nucleo `WhisperPill`.
9. Quattro schermi con lo stesso widget meteo: una sola richiesta alla sorgente.
10. Daemon fermato: tutti gli schermi tornano al solo nucleo.

### 3.3 Guardrail di CI aggiunti

- Limite di 500 righe per file sorgente (`scripts/ci/line_limit.py`) con lista di eccezioni temporanee che può solo diminuire.
- Divieto di commenti nei nuovi file Rust, Python, JS e TS del perimetro della pagina 80, controllato da uno script dedicato.
- Divieto di testo letterale nei file UI del perimetro: controllo che le stringhe visibili passino da `ctx.t` o `t()`.
- Regola di dipendenza dei crate di dominio (nessun I/O).
- Dimensione massima del modulo WASM.

## 4. Osservabilità

- Metriche esposte dal daemon in formato testuale su socket Unix, lette dal governatore e dal pannello admin.
- Tracce delle decisioni del planner campionate e conservate 24 ore, senza contenuti dei widget.
- Ogni errore con modulo di origine, codice e correlazione `request_id`, senza dati personali.

## 5. Criteri di uscita del programma

Il programma F0-F9 è concluso quando tutti gli obiettivi di 2.2 sono misurati e rispettati (o ricalibrati con motivazione scritta), i dieci scenari dorati sono verdi in CI, e la Sentinella mostra in modo affidabile presenza, ospiti, accessi e automazioni.
