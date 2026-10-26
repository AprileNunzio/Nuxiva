# Directory Giochi - Nuxiva

Questa directory è dedicata all'inserimento e sviluppo di tutti i giochi autonomi e indipendenti all'interno della suite Nuxiva.

## Architettura e Regole di Isolamento

1. **Directory Propria per Gioco**:
   - Ogni gioco deve essere collocato in una propria sottocartella dedicata (ad esempio: `giochi/<nome-gioco>/`).
   
2. **Totale Indipendenza**:
   - Ogni gioco è autonomo: i relativi file sorgente, risorse grafiche, audio, logica di gioco, dipendenze (`package.json`, `requirements.txt`, ecc.) o file HTML/JS devono risiedere esclusivamente all'interno della directory del gioco stesso.
   - Nessun gioco deve dipendere direttamente dai file interni di un altro gioco.

3. **Struttura Consigliata per Gioco**:
   ```
   giochi/
   └── <nome-gioco>/
       ├── index.html       (oppure main.py / app.js / entrypoint)
       ├── assets/          (immagini, sprite, audio, texture)
       ├── src/             (codice sorgente e logica di gioco)
       └── README.md        (istruzioni di esecuzione, comandi e note)
   ```
