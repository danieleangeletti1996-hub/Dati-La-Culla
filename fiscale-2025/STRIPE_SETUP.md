# Stripe: export automatico con chiave API in sola lettura (10 minuti, una volta sola)

## 1. Crea la chiave restricted
1. dashboard.stripe.com → Sviluppatori → Chiavi API → "Crea chiave con restrizioni".
2. Nome: `claude-export-readonly`.
3. Permessi, tutti in **Lettura** e nient'altro: Balance transactions (Saldo), Payouts (Bonifici), Charges (Addebiti), Invoices, Reports/Report runs, Customers (solo se serve per riconciliare le prenotazioni). Nessun permesso di scrittura.
4. Copia la chiave (inizia con `rk_live_`). Non incollarla in chat.

## 2. Salvala nell'ambiente Claude Code (non in chat)
1. claude.ai/code → Ambienti → apri l'ambiente di questa sessione → Variabili d'ambiente → aggiungi `STRIPE_RESTRICTED_KEY` = la chiave.
2. Rete → accesso in uscita: aggiungi `api.stripe.com` ai domini consentiti (o scegli l'accesso completo).
3. Salva e riavvia la sessione (o aprine una nuova): Claude eseguirà `scripts/stripe/export_stripe.py --check` per confermare l'accesso.
Documentazione: https://code.claude.com/docs/en/claude-code-on-the-web

## 3. Cosa produce lo script
`scripts/stripe/export_stripe.py --from 2025-01-01 --to 2025-12-31 --out output/stripe_2025.xlsx`
- foglio "Mensile": incassi lordi, rimborsi, commissioni Stripe, netto, payout del mese;
- foglio "Transazioni": tutte le balance transactions con data, tipo, importo, commissione, netto, descrizione;
- foglio "Payout": ogni bonifico con data di arrivo e importo, da riconciliare con l'estratto conto bancario;
- foglio "Quadratura": somma netti − somma payout = saldo residuo.
Le fatture mensili delle commissioni Stripe (PDF) non sono esposte dall'API: si scaricano da Dashboard → Impostazioni → Fatturazione/Documenti.

## Revoca
Quando il lavoro è finito: Sviluppatori → Chiavi API → elimina `claude-export-readonly`.
