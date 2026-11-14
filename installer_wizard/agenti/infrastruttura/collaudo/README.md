# Telemetria di collaudo

Un unico flusso di eventi tipizzati (JSON con id di correlazione) che raccoglie Sentinella, ascolto, visione, supervisore, worker, MCP, errori del gestore globale e salute delle risorse, per capire su una macchina reale se il lavoro funziona o c'è un bug.

## Come funziona

- Motore Rust `native/crates/collaudo-core` (binding `RustCollaudo`), con ripiego Python sottile (`pyhub.py`) e test di parità sulla redazione.
- Ogni evento ha: `seq`, `id`, `at_ms`, `domain` (sentinel, ear, vision, supervisor, worker, mcp, error, resource, probe, system), `level`, `kind`, `corr`, `src`, `fields`.
- Zero-Trust: i campi passano da un redattore. Restano solo numeri, booleani e testi brevi in forma di token. Chiavi come nome, voce, volto, allergie, trascrizione, email, telefono, token vengono oscurate. I valori sotto chiavi `*_ref` diventano pseudonimi con chiave. Nei messaggi di errore sono oscurati indirizzi email, numeri lunghi, blob esadecimali e nomi utente nei percorsi.
- Registro su file a rotazione in `/var/lib/nuxiva/collaudo/log` (permessi 0600), con catena MAC per segmento (BLAKE3 con chiave) e indice laterale; `verify` rileva manomissioni.
- Ricezione dagli altri processi (ascolto) tramite socket Unix datagram 0600; nel supervisore l'emissione è diretta.
- Verbosità extra (livelli trace e debug, per esempio il livello del microfono) solo con la modalità collaudo attiva.
- Limitatore: al massimo 200 eventi al secondo per tipo, gli errori non vengono mai scartati.

## Accesso

Nessuna esposizione di rete di default: finché non esiste un token le rotte rispondono 404. Con `sudo nuxivactl collaudo on` si genera un token a 256 bit (salvato solo come hash). Le rotte sono sull'app amministrativa, solo da localhost, con `Authorization: Bearer`, intestazione `X-Nuxiva-Request: 1` sulle scritture e limite ai tentativi sbagliati. Da remoto usare un tunnel SSH (`ssh -L 8080:127.0.0.1:8080`).

## Comandi (`nuxivactl collaudo`)

- `on [--save]`, `off`, `status`, `mode on|off`
- `mark ETICHETTA`: segna un punto nel flusso e restituisce l'id di correlazione
- `events [domain=… min_level=… corr=… kind_prefix=… since_seq=… from_ms=…]`, `stream [filtri]` (SSE)
- `verify`: controlla la catena del registro
- `report [minuti]`, `baseline [minuti]`: rapporto e confronto con la base per trovare regressioni
- `smoke [prova…]`: prove attive sul dispositivo
- `scenario radio_rejected|music_rejected|owner_voice_accepted [secondi]`: osserva l'ascolto mentre si fa partire radio, musica o si parla
- `diagnose`: modalità collaudo, test di fumo, rapporto; codice di uscita 0 pass, 1 warn, 2 fail, 3 dati insufficienti

## Prove attive

services, bus_roundtrip, camera_frame, microphone_level, ear_roundtrip, sentinel_chain, collaudo_chain, mcp_discovery, sandbox_exec, parity.

## Controlli senza strumentazione ancora attiva

voice_first_audio, barge_in e aec_erle risultano `missing` finché i punti di misura non emettono eventi `probe`. I controlli radio e musica usano gli scenari.
