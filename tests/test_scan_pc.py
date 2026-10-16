#!/usr/bin/env python3
"""Test di scripts/archivio/scan_pc.py su una finta cartella utente."""
import csv
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "archivio"))
import scan_pc  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as td:
        home = Path(td) / "home"
        (home / "Download").mkdir(parents=True)
        (home / "Documenti" / "varie").mkdir(parents=True)
        (home / "AppData" / "x").mkdir(parents=True)
        (home / "Download" / "santander_piano.txt").write_text("Piano di ammortamento contratto 17659937 Santander " * 30)
        (home / "Documenti" / "copia_piano.txt").write_text("Piano di ammortamento contratto 17659937 Santander " * 30)
        shutil.copy(ROOT / "tests/fixtures/IT01274580248_00001.xml", home / "Documenti" / "varie")
        (home / "Documenti" / "nota.txt").write_text("appunti della spesa " * 100)
        (home / "Documenti" / "ISA EG44U 2025 - Dati compilati.txt").write_text("quadro D " * 200)
        (home / "AppData" / "x" / "santander.txt").write_text("santander " * 200)  # deve essere ignorato
        out, arch = Path(td) / "scan", Path(td) / "archivio"
        rc = scan_pc.main(["--roots", str(home), "--out", str(out), "--copy-to", str(arch)])
        assert rc == 0
        inv = list(csv.DictReader((out / "inventario_pc.csv").open(encoding="utf-8"), delimiter=";"))
        by_name = {r["nome"]: r for r in inv}
        assert "santander.txt" not in by_name, "AppData va saltata"
        assert by_name["santander_piano.txt"]["voci"] == "02_finanziamenti"
        assert by_name["IT01274580248_00001.xml"]["voci"] == "06_fatture_xml", by_name["IT01274580248_00001.xml"]["voci"]
        assert by_name["ISA EG44U 2025 - Dati compilati.txt"]["voci"] == "07_isa_redditi"
        assert by_name["nota.txt"]["voci"] == "" and by_name["nota.txt"]["cartella_proposta"] == "99_INBOX_DA_SMISTARE"
        assert by_name["ISA EG44U 2025 - Dati compilati.txt"]["cartella_proposta"] == "01_FISCALE/2025/08_isa_redditi"
        dups = list(csv.DictReader((out / "duplicati.csv").open(encoding="utf-8"), delimiter=";"))
        assert len(dups) == 1 and dups[0]["n_copie"] == "2"
        copied = sorted(p.name for p in arch.rglob("*") if p.is_file())
        assert len(copied) == 3, copied  # duplicato copiato una volta sola, nota.txt esclusa
        assert (out / "RIEPILOGO.md").exists() and (out / "proposta_riordino.csv").exists() and (out / "trovati_per_voce.md").exists()
        print(f"OK: inventario {len(inv)} file, 1 gruppo duplicati, {len(copied)} copie in ARCHIVIO")


if __name__ == "__main__":
    main()
