# Nuxiva: banco riparazioni live / Live repair workbench

Stato verificato il 21 ottobre 2026. Questo documento sostituisce la precedente proposta architetturale: distingue il software implementato dalle prove fisiche ancora necessarie.

## Funzionamento implementato

- Il comando di creazione di un progetto di riparazione seleziona gli specialisti dal catalogo e accoda l'apertura del banco per il proprietario del progetto.
- Il client rileva la richiesta, apre il banco massimizzato e attiva la vista immersiva. Attende il caricamento di progetti e telecamere prima di avviare la sessione. Un errore non genera tentativi di apertura illimitati.
- La telecamera si sceglie fra le sorgenti registrate sul server e le webcam disponibili nel browser. La selezione preferisce una sorgente il cui nome contiene banco o repair. Il nome della sessione è modificabile. Le webcam del browser richiedono un contesto sicuro e il permesso dell'utente; le sorgenti del server usano le API telecamere esistenti.
- Il video locale usa il flusso del browser. Le sorgenti del server usano MJPEG con cattura condivisa; le istantanee sono il ripiego se il flusso non è disponibile. La cattura resta aperta fra le richieste, evitando di rinegoziare ripetutamente il dispositivo e l'autofocus.
- I fotogrammi vengono analizzati periodicamente. Il browser limita le richieste contemporanee; il backend applica un intervallo minimo e sospende l'analisi durante il movimento rilevato.
- Il motore nativo esegue stabilità della scena, tracking IoU, smoothing e verifiche topologiche. In assenza del modulo compilato sono disponibili le controparti Python.
- L'analizzatore visivo restituisce osservazioni strutturate: dossier, componenti, riquadri normalizzati, collegamenti visibili e consigli. I popup vengono posizionati rispetto all'immagine effettiva, tenendo conto delle bande laterali.
- La correzione di un componente aggiorna etichetta e valore conservati nella sessione; non addestra una rete neurale. Le correzioni ripetute restano applicate ai fotogrammi successivi.
- Lo schema è un grafo progressivo delle connessioni proposte dal modello, visualizzato in SVG. Non è uno schema certificato né una ricostruzione completa delle piste nascoste.
- Il solver lineare DC/AC supporta resistenze, condensatori, induttori e sorgenti ideali. Non restituisce tensioni per reti flottanti, conflitti di pin, dispositivi non supportati o sistemi non risolvibili. Le tensioni sono simulazioni del grafo osservato, non misurazioni della scheda.
- La chat interroga lo specialista assegnato con il contesto della sessione e conserva le risposte. Sono disponibili messaggi inter-agente e convocazione di specialisti esistenti o nuovi profili. La creazione di un profilo non garantisce nuove capacità esecutive o strumenti installati.
- Le sessioni sono cifrate e scritte con sostituzione atomica. Occorre mantenere stabile NUXIVA_SECRET_KEY fra i riavvii: cambiarla rende illeggibili le sessioni precedenti. Il fascicolo di progetto conserva campioni dei fotogrammi analizzati, schema, compiti, fonti e registro delle osservazioni.
- Il supervisore espone un proxy limitato alle operazioni del banco. Le API sono dichiarate nel manifest della funzionalità e scoperte all'avvio. Le richieste di modifica richiedono l'intestazione prevista dall'app; il display deve essere autorizzato.

## Mappa dei file

| Area | Posizione |
| --- | --- |
| Interfaccia, API client, lingue, icona | client_web/src/apps/repair_workbench/ |
| Sessioni, pipeline, analizzatore, simulazione | server/features/repair_workbench/ |
| Profili e fabbrica degli specialisti | server/core/agent_registry/ |
| Progetti, messaggi e convocazione | server/features/project_workspace/ |
| Proxy del supervisore e manifest | installer_wizard/features/repair_workbench/ |
| Scoperta API del supervisore | installer_wizard/backend/feature_api_scanner.py |
| Motore spaziale | native/crates/spatial-core/src/workbench_*.rs |
| Bridge Python | native/crates/nuxiva-native/src/workbench.rs |
| Test backend | server/tests/test_repair_workbench.py |
| Test proxy | installer_wizard/tests/test_repair_workbench_proxy.py |
| Test client | client_web/tests/repair-workbench.test.cjs |

## Contratti e configurazione

Le API sono sotto /api/v1/repair-workbench: projects, sessions, sessions/{id}, analyze-frame, teach-component, chat, escalate e launch-requests. Il proxy inoltra projects al gestore progetti del core. Il supervisore usa l'account operativo user_primary del core; la separazione completa degli account fra supervisore e core resta da progettare.

La visione usa il servizio di inferenza configurato e NUXIVA_VISION_MODEL, con un modello visivo predefinito se la variabile è assente. La chat usa il gateway e la configurazione del cervello. Un modello visivo deve essere installato e raggiungibile: gli errori sono espliciti, non sostituiti con risultati dimostrativi.

Il frontend mantiene la versione React già usata dal progetto. Le anteprime 3D dei componenti sono forme illustrative parametrizzate, dichiarate come tali. Non sono state introdotte ricostruzioni 3D della scheda osservata, modelli ONNX o simulatori non lineari.

## Verifiche riproducibili

```text
python -m pytest server/tests/test_repair_workbench.py
python -m unittest server.tests.test_repair_workbench
cd installer_wizard
python -m unittest tests.test_repair_workbench_proxy
cd ../client_web
npm run build
cd ../native
cargo fmt --all --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
```

I test API impiegano un analizzatore controllato: verificano il flusso applicativo senza dipendere da una webcam o da un modello installato. Non misurano l'accuratezza del riconoscimento di una scheda fisica.

## Prova sul banco

1. Installare la revisione e verificare il completamento dell'aggiornamento.
2. Controllare che la sorgente nominata del banco mostri la scheda e sia selezionata nell'app.
3. Creare un progetto di riparazione, verificare l'apertura immersiva e avviare la sessione.
4. Verificare dossier e popup su una scena ferma; muovere un oggetto per controllare la sospensione e la ripresa.
5. Correggere un componente e controllare la persistenza ai fotogrammi successivi.
6. Aprire lo schema parziale, interrogare gli specialisti e provare una convocazione.
7. Registrare problemi, tempi effettivi e risultati osservati senza dichiarare una diagnosi elettrica verificata dalla sola immagine.

## Attività successive

- Validare il riconoscimento su immagini reali, componenti piccoli, riflessi, fronte/retro e cambi di inquadratura.
- Collegare un eventuale estrattore locale di caratteristiche attraverso VisionAnalyzer, con modello e distribuzione verificati separatamente.
- Introdurre una revisione umana dei collegamenti e un livello di confidenza prima delle simulazioni complesse.
- Integrare un ciclo vocale continuo dedicato al banco; al momento sono presenti l'intento dell'assistente e la chat testuale.
- Rendere espliciti durata, ripresa, chiusura e pulizia delle sessioni in memoria.
- Completare l'identità multiutente e l'isolamento dei profili dinamici fra proprietari.

## Fascicoli, squadra parallela e ripresa

Ogni progetto mantiene una directory autonoma sotto `DATA_DIR/repair_workbench/projects/{owner}/{project}/repair/`, con sottodirectory `images`, `sessions`, `schematics`, `tasks`, `sources` e `logs`. I contenuti sono cifrati. I fotogrammi automatici vengono deduplicati, distanziati di almeno 30 secondi e limitati ai primi 60 campioni: le prove già registrate non vengono eliminate automaticamente. Il registro conserva osservazioni, risposte, ipotesi dichiarate e sezioni cambiate, senza pretendere di esporre ragionamenti interni privati.

L'archivio elenca più progetti aperti e chiusi. Riprendere un progetto aperto restituisce l'ultima sessione con note, correzioni, schema, problemi e compiti. Le risposte tardive di una sessione precedente non sostituiscono il fascicolo più recente. La chiusura impedisce nuove modifiche e riaperture implicite. Il riconoscimento automatico della stessa scheda mediante immagine non è implementato: la ripresa usa un identificatore esplicito, per evitare di confondere esemplari simili.

La squadra esegue in concorrenza identificazione, ricerca schemi, diagnosi, componenti 3D e ricerca prezzi. I compiti si avviano in background dopo una prima osservazione significativa o nuovi problemi; contesto, intervallo minimo e richieste accorpate evitano nuove ricerche a ogni movimento. Il coordinatore ordina i problemi per priorità e registra chi lavora, risultati, fonti e impedimenti. L'operatore può risolvere o riaprire un problema con una nota.

La ricerca online usa lo strumento web già disponibile, a partire da sigle leggibili o corrette dall'operatore. I collegamenti restituiti sono piste di ricerca: non attestano che un PDF sia lo schema della scheda, né che un prezzo o una compatibilità siano verificati. Senza identificatori utilizzabili il compito viene indicato come bloccato. La diagnosi usa lo specialista assegnato; il ricostruttore 3D della scheda non è collegato e resta esplicitamente non disponibile. L'anteprima illustrativa del singolo componente è una funzione distinta.

Le nuove API comprendono `projects/archive`, `projects/{id}/resume`, `projects/{id}/close`, `sessions/{id}/team`, `sessions/{id}/team/run`, `sessions/{id}/issues` e `sessions/{id}/issues/{issue}/status`. Sono incluse nella lista limitata del proxy del supervisore. Il frontend aggiorna sessione e squadra anche quando una risposta arriva dall'assistente principale.

## Studio necessario per tracking, doppio lato e 8K

La vista densa mostra contorni selezionabili e un solo pannello informativo. Le rilevazioni perse non lasciano riquadri disegnati; i contorni vengono nascosti quando il motore segnala movimento. IoU e smoothing non costituiscono un inseguimento geometrico affidabile durante rotazioni, ribaltamenti, occlusioni o saldature. Non dichiarare questa parte completata.

Per evolvere servono: calibrazione ottica e scala; identificazione del piano della scheda; punti caratteristici e trasformazioni geometriche fra fotogrammi; soglie per dichiarare perso il riferimento; viste fronte/retro separate; associazioni confermate fra i lati; gestione di mano, utensile, fumo e riflessi; acquisizioni mirate prima e dopo un intervento. Le piste nascoste e gli strati interni richiedono documentazione o misure: una fotografia non li rende osservabili.

Il flusso di anteprima e i fotogrammi di analisi sono attualmente ridimensionati: non conservano il dettaglio nativo 8K. La futura pipeline deve separare anteprima fluida, inseguimento geometrico e ritagli alla risoluzione originale, registrando origine, lato, posizione e momento di ogni ritaglio. Qualità ottica, illuminazione, distanza e compressione restano parte della verifica. Nessun test su telecamera IP 8K è stato eseguito.

## English update

Projects now have independent encrypted dossiers, sampled images, circuit snapshots, tasks, sources and an observable evidence log. Open projects can be resumed with their latest session; closed projects reject implicit changes. Resume currently uses an explicit project identifier, not visual board recognition.

Concurrent background work orders cover board identification, schematic search, diagnosis, 3D and pricing. Search links are unverified leads; missing identifiers or executors are reported as blocked. Component 3D previews are illustrative shapes, not reconstructions. Camera streams and snapshots share a persistent capture process. Dense overlays show selectable outlines with a single detail panel.

Robust board pose tracking, front/back registration, native-resolution 8K crops, verified price extraction, complete observed-board reconstruction and continuous voice control remain separate work items. Do not infer their completion from passing software tests.

## English handover

The implemented baseline includes named camera selection, immersive launch, periodic frame analysis, stabilized overlays, saved label/value corrections, a partial connectivity graph, guarded linear simulation, specialist chat and recruitment, encrypted session storage, and a bounded supervisor proxy discovered from its feature manifest.

Automated API tests use a controlled vision analyzer. Physical camera recognition, continuous voice interaction, neural few-shot learning, hidden-trace reconstruction, nonlinear simulation and complete multi-account isolation must not be described as verified or complete. Maintain a stable installation secret for encrypted session recovery. Record actual server test results separately from automated checks.

## Integrazione della pagina principale e prova reale

La prima prova fisica del 21 ottobre ha mostrato che il connettore dei progetti generici intercettava il comando prima del core: il messaggio annunciava un progetto ma il banco non si apriva. La correzione introduce un connettore del banco dichiarato nel manifest e scoperto prima dei progetti generici. Crea progetto e sessione sulla telecamera nominata, apre il widget dedicato e incorpora la medesima applicazione React tramite /repair-workbench. Le domande tecniche successive vengono inoltrate alla sessione attiva.

Il banco usa ora, per impostazione predefinita, il selettore visivo del supervisore: modelli configurati compatibili con immagini e modelli locali disponibili, con tentativi successivi in caso di errore o risultato strutturato invalido. Un valore esplicito di NUXIVA_VISION_MODEL mantiene il percorso locale dedicato. Il modello effettivamente usato viene riportato nella sessione e nell'interfaccia. Questa selezione non costituisce una misura di accuratezza elettronica: la precisione deve essere valutata su osservazioni e misure reali.

La modalità Nuxiva 6.5-auto è un selettore di strategie cognitive, distinto dal modello di inferenza. Attualmente le sue regole considerano complessità testuale e stato del motore; non attestano automaticamente l'affidabilità diagnostica di ogni modello. Il banco deve distinguere ipotesi visive, simulazioni e misure confermate.

È stato inoltre corretto il ripristino delle impostazioni grafiche della pagina principale: la scena 3D inizializzata deve conservare display:block, il nucleo leggero viene inizializzato quando necessario e la vista del cervello resta accessibile. I relativi controlli sono coperti da una regressione del client.
