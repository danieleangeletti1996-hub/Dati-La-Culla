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
- `archivio/scan_pc.py` – inventario del PC per la sessione locale. Si può lanciare anche senza Claude, sul PC di Daniele, da un prompt dei comandi nella cartella del repo (branch `claude/fiscal-docs-2025-2026-efw5bg`):

  ```
  python scripts\archivio\scan_pc.py --roots "%USERPROFILE%" --out "G:\Il mio Drive\LA CULLA – ARCHIVIO\00_scan" --copy-to "G:\Il mio Drive\LA CULLA – ARCHIVIO"
  ```
  Se la cartella Drive locale non è in `G:\Il mio Drive`, sostituire il percorso con quello reale (o con `%USERPROFILE%\Documenti\LA CULLA – ARCHIVIO`). Solo lettura e copie: non sposta né cancella nulla.

I documenti e i dati restano su Google Drive (`LA CULLA – ARCHIVIO`); in questo repo solo script, template e checklist.
