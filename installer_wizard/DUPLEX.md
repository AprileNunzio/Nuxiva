# Voce full-duplex e interruzione a voce / Full-duplex voice and voice barge-in

## Attivazione / Enabling

Di default `NUXIVA_DUPLEX=legacy`: la voce funziona come prima e l'interruzione a voce è spenta. Non si accende da sola.
By default `NUXIVA_DUPLEX=legacy`: voice works as before and voice barge-in is off. It never turns itself on.

Per attivarla / To enable it:

1. Imposta `NUXIVA_DUPLEX=rust` nell'ambiente del backend e del servizio ear, poi riavvia entrambi. / Set `NUXIVA_DUPLEX=rust` in the backend and ear service environment, then restart both.
2. Verifica la voce `duplex` delle statistiche dell'ear (`mode`, `voice_cuts`). / Check the `duplex` entry of the ear stats (`mode`, `voice_cuts`).
3. Per tornare indietro rimetti `legacy`. / To roll back set `legacy` again.

L'interruzione a voce scatta solo con cancellazione dell'eco attiva sul microfono del browser (`echo_cancelled`) e con le impronte vocali pronte.
Voice barge-in only fires with browser echo cancellation active on the microphone (`echo_cancelled`) and voiceprints ready.

## Protocollo audio / Audio protocol

Il browser invia `{"type":"hello","version":1,"pcm":true}` all'apertura di `/api/voice/duplex/ws`. Con `pcm` il server invia, per ogni blocco di testo, un messaggio JSON `chunk` (`gen`, `seq`, `rate`, `frames`, `ms`) seguito da frame binari: `kind=1` (1 byte), `gen` (u32 big endian), `seq` (u32 big endian), PCM 16 bit mono little endian da 40 ms. Senza `hello` resta il formato precedente (WAV per blocco).
The browser sends `{"type":"hello","version":1,"pcm":true}` when opening `/api/voice/duplex/ws`. With `pcm` the server sends, per text chunk, a `chunk` JSON message (`gen`, `seq`, `rate`, `frames`, `ms`) followed by binary frames: `kind=1` (1 byte), `gen` (u32 big endian), `seq` (u32 big endian), 40 ms of 16-bit mono little-endian PCM. Without `hello` the previous format (one WAV per chunk) is kept.

Il pacer in Rust (`duplex-core`, `pacer.rs`) tiene in volo al massimo 240 ms di audio davanti alla riproduzione: al taglio i frame in coda vengono scartati tutti insieme e il client sfuma l'audio già schedulato in 30 ms.
The Rust pacer (`duplex-core`, `pacer.rs`) keeps at most 240 ms of audio in flight ahead of playback: on a cut every queued frame is dropped at once and the client fades already scheduled audio in 30 ms.

## Verdetto del parlante / Speaker verdict

Ogni finestra da 250 ms riceve un verdetto (`known`, `broadcast`, `uncertain`). Per tagliare servono 3 finestre `known` consecutive con margine minimo e **lo stesso parlante** riconosciuto (`AttributionChain`, `gate.rs`). Musica o programma rilevati mettono in quarantena per 8 finestre ogni verdetto `known`; frame non finiti, parlanti diversi, slug non validi, eco non cancellata o punteggi non finiti danno sempre `uncertain`. Il comportamento è nel crate Rust con ripiego Python in `window_gate.py` e test di parità.
Every 250 ms window gets a verdict (`known`, `broadcast`, `uncertain`). Cutting needs 3 consecutive `known` windows with minimum margin and the **same recognised speaker** (`AttributionChain`, `gate.rs`). Detected music or programme audio quarantines every `known` verdict for 8 windows; non-finite frames, different speakers, invalid slugs, uncancelled echo or non-finite scores always give `uncertain`. The behaviour lives in the Rust crate with a Python fallback in `window_gate.py` and parity tests.

## Non provato senza audio reale / Not proven without real audio

- Soglie e latenza con microfoni, altoparlanti e stanze reali. / Thresholds and latency with real microphones, speakers and rooms.
- Qualità della cancellazione eco del browser su ogni dispositivo. / Browser echo-cancellation quality on every device.
- Tempo reale tra voce dell'utente e silenzio di Nuxiva (il taglio passa dal browser). / End-to-end time between the user's voice and Nuxiva going silent (the cut goes through the browser).
- Riproduzione gapless del flusso PCM su Safari e Firefox. / Gapless playback of the PCM stream on Safari and Firefox.
