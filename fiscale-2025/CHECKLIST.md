# Checklist documentazione fiscale 2025 – Studio Dacol

Richiesta di Alex Fontana del 17/09/2026 ("documentazione mancante") + voci residue di Chiara De Villa del 01/07/2026.
Master dei documenti: Google Drive `LA CULLA – ARCHIVIO/01_FISCALE/2025/`. Stato aggiornato a ogni passo.

Legenda stato: ☐ da fare · ◐ in corso · ☑ fatto · ✗ non disponibile (motivo)

| # | Voce richiesta | Stato | Fonte / dove | Chi | Prossima azione |
|---|---|---|---|---|---|
| 1 | Estratto conto / movimenti criptovalute 2025 (Binance, Coinbase, Coinbase Wallet, Revolut) | ☐ | portali (vedi PERCORSI_PORTALI.md) → `07_crypto` | Daniele scarica, Claude consolida | export CSV/PDF 2025 |
| 2a | Piano ammortamento Findomestic (pratica 20221876625345) | ☐ | Area Clienti Findomestic → `02_finanziamenti` | Daniele | download contratto + piano rate |
| 2b | Piano ammortamento Ford Credit (contratto 000401618) | ☐ | ford.it area riservata → `02_finanziamenti` | Daniele | download contratto + documento di sintesi |
| 2c | Piano ammortamento Santander (contratto 17659937) | ☐ | Area Riservata Santander; allegati email 02/05 e 20/05/2025 → `02_finanziamenti` | Daniele | download piano; salvare allegati email in Drive |
| 2d | Contratti noleggio Grenke (12545692) e Rent Foryou (20250131012) [chiesti da Chiara 01/07] | ☐ | allegati email 01/12/2025 (Grenke) e 26/02/2025 (Rent Foryou) → `02_CONTRATTI/noleggi` | Daniele (Salva in Drive) | salvare allegati |
| 3 | Dati "POS" Stripe 2025 (incassi, commissioni, payout) | ☐ | API Stripe (chiave restricted) o Dashboard → `03_pos_stripe_nexi` | Daniele setup chiave, Claude export | vedi STRIPE_SETUP.md |
| 4 | Fatture eviivo primi mesi 2026 (conti IRE004252, EVL023556) | ◐ | 2025 in Gmail: EV00167663 (15/06, IRE), EV00172490 (15/07, EVL), EV00191878 (15/10, EVL), EV00193021 (15/10, IRE), EV00197955 (17/11, EVL), EV00199062 (17/11, IRE), EV00203811 (15/12, EVL). Disdetta conto EVL confermata da eviivo il 07/11/2025 (disattivazione febbraio 2026); conto IRE004252 ancora attivo (EV00257418 del 15/09/2026, già inviata ad Alex). Gen–ago 2026: nessuna fattura in Gmail né nel cestino → bozza a accounts@eviivo.com pronta. Le due .eml 2025 copiate in `04_eviivo` | Daniele invia bozza / portale eviivo | attendere risposta eviivo o scaricare dal portale |
| 5 | ISA: acquisti 2025 netto IVA carne / sfarinati / vino / birra | ☐ | XML fatture ricevute 2025 (export Studio Dacol o AdE) → `05_fatture_acquisto_xml`; script `scripts/fatturapa/parse_fatture.py` | Studio export, Claude calcolo, Daniele verifica righe dubbie | inviare bozza allo studio |
| 6 | Valore netto IVA beni in affitto (Rifugio Valgrande) + lista | ◐ | Bozza elenco creata da Claude dalla lista Moiè 06/2024 (151 voci, valore lista 40.901,20 €; colonna "germano" 8.450 € = lavastoviglie Winterhalter, tavoli entrata/uscita, lavastoviglie bar; colonna "daniele" 15.830 €): Google Sheet `05_ATTREZZATURE/beni_in_affitto/2026-09-18_elenco_beni_valgrande_BOZZA`. Da completare con il giro video (colonne "Presente" e "Proprietà") e da firmare con Germano. L'elenco controfirmato previsto dal contratto non è mai stato redatto. | Claude redige, Daniele + Germano firmano | riprese video Rifugio; email di Germano |
| 7 | ISA EG44U completo (quadri B, C, D, E) | ☐ | PDF "ISA EG44U 2025 - Dati compilati" (email 07/07/2026) da salvare in `08_isa_redditi` | Daniele salva PDF, Claude analizza | Salva in Drive i due PDF di luglio |
| 8 | Rimanenze al 31/12/2025 [Chiara 01/07] | ☐ | fatture dic-25/gen-26, ZMenu, foto dell'epoca → `10_inventario` | Claude propone, Daniele conferma | dopo il giro video |
| 9 | Fatture nel contributo Avepa (cella frigorifera) [Chiara 01/07] | ☐ | decreto Avepa + fatture cella → `01_FISCALE/2025/09_commercialista` | Daniele | indicare fatture |
| 10 | Certificazioni premi Arca Vita 1172122 / Axa France 401618 [Chiara 01/07] | ☐ | email/portali assicurazioni → `02_CONTRATTI/assicurazioni` | Daniele | download certificazione 2025 |
| 11 | Riordino archivio PC + Drive | ◐ | Struttura Drive creata; già copiati in ARCHIVIO: contratto Compass 2021, documento di sintesi Volksbank 2022, bozza contratto affitto azienda (PDF + Doc), lista Moiè, lista fabbisogno attrezzature 2025, 2 .eml eviivo 2025. Scansione PC non ancora eseguita: prompt pronto in Drive `00_PROMPT – Scansione PC` | sessione locale sul PC di Daniele | avviare la sessione locale con il prompt |

## Diario
- 17/09: setup Drive/repo/script; bozza email allo studio (export XML) e a eviivo (fatture 2026) in attesa di conferma di Daniele.
- 18/09 06:30: check-in automatico: nessun nuovo file su Drive, nessuna risposta dallo studio, chiave Stripe non impostata (api.stripe.com bloccato), scansione PC non eseguita. Creata bozza elenco beni Valgrande. Link Quick Share Samsung del 17/09 non raggiungibile dall'ambiente cloud.

## Consegna
Cartella `01_FISCALE/2025/99_da_inviare_studio`: un file per voce, nome `2025_<voce>_<descrizione>.pdf/xlsx`. Bozza email ad Alex preparata da Claude, inviata da Daniele.
