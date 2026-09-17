#!/usr/bin/env python3
"""
export_stripe.py – Estrae da Stripe le balance transactions e i payout di un periodo e produce
un Excel per il commercialista (incassi lordi, rimborsi, commissioni, netto, payout, quadratura).

Chiave: variabile d'ambiente STRIPE_RESTRICTED_KEY (chiave "restricted" in sola lettura).
Rete: serve l'accesso a api.stripe.com.

Uso:
  python scripts/stripe/export_stripe.py --check
  python scripts/stripe/export_stripe.py --from 2025-01-01 --to 2025-12-31 --out output/stripe_2025.xlsx
  python scripts/stripe/export_stripe.py --demo tests/fixtures/stripe_demo.json --from 2025-01-01 --to 2025-12-31 --out /tmp/demo.xlsx

Dipendenze: requests, openpyxl.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

API = "https://api.stripe.com/v1"
TZ = ZoneInfo("Europe/Rome")
HEAD_FILL = PatternFill("solid", fgColor="DDEBF7")


def eur(cents) -> Decimal:
    return (Decimal(int(cents or 0)) / Decimal(100)).quantize(Decimal("0.01"))


def epoch(day: str, end: bool = False) -> int:
    d = dt.date.fromisoformat(day)
    t = dt.time(23, 59, 59) if end else dt.time(0, 0, 0)
    return int(dt.datetime.combine(d, t, tzinfo=TZ).timestamp())


def ts_to_local(ts: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(int(ts), TZ).replace(tzinfo=None)


class StripeClient:
    def __init__(self, key: str):
        import requests  # importato qui: in modalità --demo non serve

        self.s = requests.Session()
        self.s.auth = (key, "")
        self.s.headers["Stripe-Version"] = "2024-06-20"

    def get(self, path: str, **params):
        r = self.s.get(f"{API}/{path}", params=params, timeout=60)
        if r.status_code != 200:
            raise SystemExit(f"[errore] Stripe {r.status_code} su {path}: {r.text[:300]}")
        return r.json()

    def list_all(self, path: str, **params):
        params = {"limit": 100, **params}
        out = []
        while True:
            page = self.get(path, **params)
            out.extend(page.get("data", []))
            if not page.get("has_more") or not page["data"]:
                return out
            params["starting_after"] = page["data"][-1]["id"]


def flatten_params(prefix: str, d: dict) -> dict:
    return {f"{prefix}[{k}]": v for k, v in d.items()}


def fetch(client: StripeClient, start: int, end: int):
    bts = client.list_all("balance_transactions", **flatten_params("created", {"gte": start, "lte": end}))
    payouts = client.list_all("payouts", **flatten_params("created", {"gte": start - 40 * 86400, "lte": end}))
    return bts, payouts


def summarize(bts: list[dict], payouts: list[dict], start: int, end: int):
    months = defaultdict(lambda: defaultdict(Decimal))
    rows = []
    for b in sorted(bts, key=lambda x: x["created"]):
        cat = b.get("reporting_category") or b.get("type")
        when = ts_to_local(b["created"])
        m = when.strftime("%Y-%m")
        amount, fee, net = eur(b["amount"]), eur(b.get("fee", 0)), eur(b["net"])
        d = months[m]
        if cat in ("charge", "payment"):
            d["incassi_lordi"] += amount
            d["commissioni"] += fee
        elif cat == "refund":
            d["rimborsi"] += amount
            d["commissioni"] += fee
        elif cat in ("fee", "stripe_fee"):
            d["commissioni"] += -amount
        elif cat == "payout":
            d["payout"] += -amount
        elif cat in ("dispute", "dispute_reversal"):
            d["contestazioni"] += net
        else:
            d["altro"] += net
        if cat != "payout":
            d["netto"] += net
        rows.append([b["id"], when, cat, b.get("type"), amount, fee, net, b.get("currency", "").upper(),
                     b.get("status"), b.get("description") or "", b.get("source") or ""])

    prow = []
    for p in sorted(payouts, key=lambda x: x.get("arrival_date") or x["created"]):
        if not (start <= p["created"] <= end or start <= (p.get("arrival_date") or 0) <= end):
            continue
        prow.append([p["id"], ts_to_local(p["created"]), ts_to_local(p["arrival_date"]) if p.get("arrival_date") else None,
                     eur(p["amount"]), p.get("currency", "").upper(), p.get("status"), p.get("method"),
                     p.get("statement_descriptor") or "", p.get("description") or ""])
    return months, rows, prow


def write_xlsx(out: Path, months, rows, prow, frm: str, to: str):
    wb = Workbook()
    ws = wb.active
    ws.title = "Mensile"
    cols = ["Mese", "Incassi lordi €", "Rimborsi €", "Commissioni Stripe €", "Contestazioni €", "Altro €",
            "Netto accreditato su saldo €", "Payout verso banca €"]
    ws.append(cols)
    tot = defaultdict(Decimal)
    for m in sorted(months):
        d = months[m]
        vals = [d["incassi_lordi"], d["rimborsi"], d["commissioni"], d["contestazioni"], d["altro"], d["netto"], d["payout"]]
        ws.append([m] + [float(v) for v in vals])
        for k, v in zip(cols[1:], vals):
            tot[k] += v
    ws.append(["TOTALE"] + [float(tot[k]) for k in cols[1:]])
    for c in ws[1]:
        c.font, c.fill = Font(bold=True), HEAD_FILL
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    for i, w in enumerate([10, 16, 12, 20, 16, 10, 26, 20], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws2 = wb.create_sheet("Transazioni")
    ws2.append(["ID", "Data/ora (Roma)", "Categoria", "Tipo", "Importo €", "Commissione €", "Netto €", "Valuta", "Stato", "Descrizione", "Sorgente"])
    for r in rows:
        ws2.append([float(v) if isinstance(v, Decimal) else v for v in r])
    for c in ws2[1]:
        c.font, c.fill = Font(bold=True), HEAD_FILL
    for i, w in enumerate([30, 19, 14, 14, 12, 14, 12, 7, 10, 50, 30], start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w
    ws2.freeze_panes = "A2"

    ws3 = wb.create_sheet("Payout")
    ws3.append(["ID", "Creato", "Data arrivo in banca", "Importo €", "Valuta", "Stato", "Metodo", "Descrizione estratto conto", "Descrizione"])
    for r in prow:
        ws3.append([float(v) if isinstance(v, Decimal) else v for v in r])
    for c in ws3[1]:
        c.font, c.fill = Font(bold=True), HEAD_FILL
    for i, w in enumerate([30, 19, 20, 12, 7, 10, 12, 28, 30], start=1):
        ws3.column_dimensions[get_column_letter(i)].width = w
    ws3.freeze_panes = "A2"

    ws4 = wb.create_sheet("Quadratura")
    netto = tot["Netto accreditato su saldo €"]
    payout = tot["Payout verso banca €"]
    ws4.append(["Periodo", f"{frm} → {to}"])
    ws4.append(["Somma netti accreditati sul saldo Stripe (escl. payout)", float(netto)])
    ws4.append(["Somma payout verso banca nel periodo", float(payout)])
    ws4.append(["Differenza = variazione del saldo Stripe nel periodo", float(netto - payout)])
    ws4.append([])
    ws4.append(["Controllo per lo studio: la somma dei payout deve coincidere con i bonifici 'STRIPE' sull'estratto conto bancario;"])
    ws4.append(["le commissioni Stripe sono la base per il credito d'imposta sulle commissioni dei pagamenti elettronici."])
    ws4.column_dimensions["A"].width = 70
    ws4.column_dimensions["B"].width = 20

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="frm", default="2025-01-01")
    ap.add_argument("--to", default="2025-12-31")
    ap.add_argument("--out", default="output/stripe_export.xlsx")
    ap.add_argument("--check", action="store_true", help="verifica chiave e rete, poi esce")
    ap.add_argument("--demo", help="file JSON con {balance_transactions:[...], payouts:[...]} per test offline")
    args = ap.parse_args(argv)

    start, end = epoch(args.frm), epoch(args.to, end=True)
    if args.demo:
        data = json.loads(Path(args.demo).read_text(encoding="utf-8"))
        bts = [b for b in data["balance_transactions"] if start <= b["created"] <= end]
        payouts = data["payouts"]
    else:
        key = os.environ.get("STRIPE_RESTRICTED_KEY")
        if not key:
            print("[errore] manca la variabile d'ambiente STRIPE_RESTRICTED_KEY (vedi fiscale-2025/STRIPE_SETUP.md)", file=sys.stderr)
            return 2
        client = StripeClient(key)
        if args.check:
            bal = client.get("balance")
            avail = ", ".join(f"{eur(a['amount'])} {a['currency'].upper()}" for a in bal.get("available", []))
            print(f"OK: chiave valida, saldo disponibile {avail or '0'}")
            return 0
        bts, payouts = fetch(client, start, end)

    months, rows, prow = summarize(bts, payouts, start, end)
    out = Path(args.out)
    write_xlsx(out, months, rows, prow, args.frm, args.to)
    print(f"transazioni: {len(rows)}; payout: {len(prow)}; mesi: {len(months)}; output: {out}")
    for m in sorted(months):
        d = months[m]
        print(f"  {m}: lordi {d['incassi_lordi']:.2f}  rimborsi {d['rimborsi']:.2f}  commissioni {d['commissioni']:.2f}  netto {d['netto']:.2f}  payout {d['payout']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
