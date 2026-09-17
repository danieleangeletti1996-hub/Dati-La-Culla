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
| 4 | Fatture eviivo primi mesi 2026 (conti IRE004252, EVL023556) | ◐ | in posta solo EV00203811 (dic-25) e EV00257418 (set-26, già inviata) → `04_eviivo` | Daniele | verifica portale eviivo gen–ago 2026 |
| 5 | ISA: acquisti 2025 netto IVA carne / sfarinati / vino / birra | ☐ | XML fatture ricevute 2025 (export Studio Dacol o AdE) → `05_fatture_acquisto_xml`; script `scripts/fatturapa/parse_fatture.py` | Studio export, Claude calcolo, Daniele verifica righe dubbie | inviare bozza allo studio |
| 6 | Valore netto IVA beni in affitto (Rifugio Valgrande) + lista | ☐ | lista Moiè 2024 (Drive) + giro video; elenco integrativo da firmare con Germano → `05_ATTREZZATURE/beni_in_affitto` | Claude redige, Daniele + Germano firmano | riprese video Rifugio |
| 7 | ISA EG44U completo (quadri B, C, D, E) | ☐ | PDF "ISA EG44U 2025 - Dati compilati" (email 07/07/2026) da salvare in `08_isa_redditi` | Daniele salva PDF, Claude analizza | Salva in Drive i due PDF di luglio |
| 8 | Rimanenze al 31/12/2025 [Chiara 01/07] | ☐ | fatture dic-25/gen-26, ZMenu, foto dell'epoca → `10_inventario` | Claude propone, Daniele conferma | dopo il giro video |
| 9 | Fatture nel contributo Avepa (cella frigorifera) [Chiara 01/07] | ☐ | decreto Avepa + fatture cella → `01_FISCALE/2025/09_commercialista` | Daniele | indicare fatture |
| 10 | Certificazioni premi Arca Vita 1172122 / Axa France 401618 [Chiara 01/07] | ☐ | email/portali assicurazioni → `02_CONTRATTI/assicurazioni` | Daniele | download certificazione 2025 |
| 11 | Riordino archivio PC + Drive | ◐ | card "Scansiona il PC" (fase 1) → `00_scan` | sessione locale | avviare la card |

## Consegna
Cartella `01_FISCALE/2025/99_da_inviare_studio`: un file per voce, nome `2025_<voce>_<descrizione>.pdf/xlsx`. Bozza email ad Alex preparata da Claude, inviata da Daniele.
