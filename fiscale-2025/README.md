# fiscale-2025

Pacchetto di lavoro per la documentazione fiscale 2025 di La Culla di Angeletti Daniele (bilancio 2025, Redditi 2026, ISA EG44U).

- `CHECKLIST.md` – stato di ogni voce richiesta dallo studio, con fonte e prossima azione.
- `PERCORSI_PORTALI.md` – percorsi di download per ogni portale, con piano B.
- `STRIPE_SETUP.md` – chiave API in sola lettura e sblocco rete per l'export automatico.
- `PROTOCOLLO_VIDEO.md` – come riprendere il locale per inventario e beni in affitto.
- `ARCHIVIO_STRUTTURA.md` – struttura unica Drive + PC e regole di riordino.

Script in `../scripts/`:
- `fatturapa/parse_fatture.py` – da XML/P7M FatturaPA a totali per categoria (carne, sfarinati, vino, birra…).
- `stripe/export_stripe.py` – export balance transactions e payout 2025.
- `inventario/frames_from_video.py` – fotogrammi dai video del giro locale.
- `archivio/scan_pc.py` – inventario del PC (solo lettura e copie) per la sessione locale o da riga di comando.
- `archivio/avvia_scansione.py` + `archivio/AVVIA_SCANSIONE.cmd` – avvio a un clic sul PC di Daniele, senza git né Claude: trova da solo la cartella Google Drive per desktop e `LA CULLA – ARCHIVIO`, scandisce profilo utente e altri dischi (mai la cartella Drive), scrive i risultati in `ARCHIVIO/00_scan` e copia i documenti trovati in ARCHIVIO. I tre file stanno anche su Drive in `LA CULLA – ARCHIVIO/00_scan/strumenti/`: con Google Drive per desktop compaiono sul PC e basta un doppio clic su `AVVIA_SCANSIONE.cmd`. Da riga di comando:

  ```
  python scripts\archivio\avvia_scansione.py            (cerca Drive da solo)
  python scripts\archivio\avvia_scansione.py --archivio "D:\percorso\LA CULLA – ARCHIVIO"
  ```

I documenti e i dati restano su Google Drive (`LA CULLA – ARCHIVIO`); in questo repo solo script, template e checklist.
