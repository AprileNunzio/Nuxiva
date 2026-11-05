# Pagina 80 · Piano di potenziamento Rust

Versione del piano: 1.0 · 2026-11-05 · base: `main` @ `7b49234`

Questo piano descrive come portare la pagina 80 (schermo principale e schermi aggiuntivi `/screen`) a un motore Rust modulare, capace di mostrare più widget live contemporaneamente con meno memoria, senza rinunciare a 3D, ologrammi ed effetti, e di decidere da solo cosa mostrare, dove e a chi.

Nessuna riga di codice applicativo viene scritta prima dell'approvazione delle fasi.

## Indice dei documenti

| # | Documento | Contenuto |
|---|-----------|-----------|
| 01 | [Stato attuale e criticità](01-stato-attuale.md) | Audit del codice su `main`, colli di bottiglia misurabili, debiti tecnici e falle di sicurezza trovate |
| 02 | [Architettura obiettivo](02-architettura.md) | Strati Clean Architecture, crate Rust, daemon, contratti tra moduli, regole di colocation |
| 03 | [Scheduler dei processi e dei widget](03-scheduler-widget.md) | Ciclo di vita dei widget, cadenze di aggiornamento, budget memoria/GPU, renderer condiviso, multi-schermo |
| 04 | [Trasporto dati e multi-schermo](04-trasporto-multischermo.md) | Flusso a delta versionato, fan-out unico, eventi una tantum, schermi e ruoli |
| 05 | [Motore decisionale dei widget](05-motore-decisionale.md) | Quanti widget, dove, conflitti, categorie, priorità, nucleo che si rimpicciolisce o diventa flusso vocale |
| 06 | [Apprendimento continuo del layout](06-apprendimento.md) | Feedback impliciti, bandit contestuale, guardrail, cifratura, reset |
| 07 | [Presenza e visibilità](07-presenza-visibilita.md) | Chi c'è davanti allo schermo, macchina a stati del pubblico, modalità solo nucleo |
| 08 | [Policy ospiti](08-policy-ospiti.md) | Matrice dei permessi per voce non riconosciuta, ospiti, familiari, proprietario |
| 09 | [Interazione a due mani](09-due-mani.md) | Pipeline webcam, gesti, hit-test sul layout, privacy dei fotogrammi |
| 10 | [App Sentinella](10-sentinella.md) | Diario degli eventi, schema, narrazione i18n, cifratura, conservazione, UI |
| 11 | [Display immersivi e visione biomolecolare](11-immersivo.md) | Meta Quest, proiettori olografici come display, visore molecolare |
| 12 | [Fasi, consegne e definizione di fatto](12-fasi.md) | Roadmap in fasi con file, test e commit per fase |
| 13 | [Rischi, metriche e strategia di test](13-rischi-metriche-test.md) | Registro dei rischi, obiettivi misurabili, banco di prova, CI |

## Principi non negoziabili

1. Clean Architecture: dominio puro senza I/O, casi d'uso che dipendono solo da porte (trait), adattatori ai bordi.
2. SoC e SRP: ogni crate, modulo e file ha una sola ragione per cambiare.
3. Codice puro: nessun commento nel codice. La documentazione vive in `docs/` e nei README delle feature.
4. Limite strutturale: nessun file oltre 500 righe, test compresi. Il controllo diventa un passo di CI.
5. UI responsive mobile e desktop, nessun testo letterale: solo chiavi di traduzione in `it`, `en`, `es`, `fr`.
6. Zero-Trust: ogni richiesta autenticata e autorizzata, input validati al confine, dati sensibili cifrati a riposo, minimo privilegio, fail-closed.
7. Errori: `Result` tipizzati in Rust, `try`/`except` solo su I/O, rete e storage in Python e JavaScript, gestore globale, nessun errore soppresso in silenzio.
8. Colocation per funzionalità: una directory per modulo con vista, logica, stili, tipi, traduzioni e test.
9. Estetica: widget senza sfondo e senza bordi. Il nucleo (avatar) resta centrato e intero finché i widget non lo coprono, poi si rimpicciolisce e, se lo spazio non basta, diventa un flusso vocale lineare.
10. Onestà: nessun confronto con il cervello umano e nessuna promessa non misurabile. Ogni obiettivo di prestazione è un valore da verificare sul banco di prova.

## Glossario

| Termine | Significato |
|---------|-------------|
| Nucleo | L'assistente al centro della pagina 80: avatar intero, avatar ridotto, sfera, flusso vocale lineare |
| Superficie | Un rettangolo assegnato a un widget su uno schermo, con livello Z |
| Schermo | Un client che disegna: pagina 80, `/screen?n=N`, visore XR, proiettore olografico |
| Pubblico | Chi è presente davanti a uno schermo in un dato istante: nessuno, ospiti, autorizzati, misto |
| Candidato | Un widget che vorrebbe essere mostrato, con priorità, categoria, costo e sensibilità |
| Piano di scena | L'output del motore decisionale: quali candidati, su quale schermo, in quale superficie |
| Budget | Il tetto di memoria GPU, memoria JS e CPU che uno schermo può spendere |
| Delta | La differenza tra due versioni dello stato inviata ai client al posto dello stato completo |
| Capacità | Un'azione atomica autorizzabile, per esempio `home.light.toggle` |

## Come leggere il piano

Chi deve approvare legge 01, 05, 07, 08, 10 e 12. Chi deve implementare legge tutto in ordine. Ogni fase in 12 rimanda ai paragrafi dei documenti tecnici che implementa.
