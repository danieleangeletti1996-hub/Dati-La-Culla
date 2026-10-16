#!/usr/bin/env python3
"""Test di scripts/archivio/avvia_scansione.py: trova l'ARCHIVIO in Google Drive, esclude Drive dalla scansione, fallback."""
import csv
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "archivio"))
import avvia_scansione  # noqa: E402

ARCHIVIO = "LA CULLA – ARCHIVIO"


def caso_drive(td: Path):
    home = td / "home_drive"
    drive = home / "Google Drive" / "Il mio Drive"
    archivio = drive / ARCHIVIO
    (archivio / "01_FISCALE" / "2025").mkdir(parents=True)
    (drive / "altro").mkdir()
    (home / "Download").mkdir(parents=True)
    (home / "Download" / "santander_piano.txt").write_text("Piano di ammortamento contratto 17659937 Santander " * 30)
    (drive / "altro" / "santander_nel_drive.txt").write_text("Santander piano rate " * 100)  # non va scandito
    (archivio / "01_FISCALE" / "2025" / "findomestic_gia_in_archivio.txt").write_text("Findomestic " * 100)  # né questo
    rc = avvia_scansione.main(["--home", str(home), "--no-open"])
    assert rc == 0
    out = archivio / "00_scan"
    inv = list(csv.DictReader((out / "inventario_pc.csv").open(encoding="utf-8"), delimiter=";"))
    nomi = {r["nome"] for r in inv}
    assert "santander_piano.txt" in nomi, nomi
    assert "santander_nel_drive.txt" not in nomi and "findomestic_gia_in_archivio.txt" not in nomi, nomi
    copie = list(archivio.rglob("*santander_piano.txt"))
    assert len(copie) == 1 and "02_finanziamenti" in str(copie[0]), copie
    log = (out / "AVVIO.log").read_text(encoding="utf-8")
    assert "Google Drive:" in log and "sincronizza" in log, log
    assert (out / "RIEPILOGO.md").exists()
    print(f"OK drive: {len(inv)} file inventariati, ARCHIVIO trovato in Drive, Drive escluso dalla scansione")


def caso_fallback(td: Path):
    home = td / "home_nodrive"
    (home / "Documenti").mkdir(parents=True)
    (home / "Desktop").mkdir()
    (home / "Desktop" / "ISA EG44U 2025 - Dati compilati.txt").write_text("quadro D " * 200)
    rc = avvia_scansione.main(["--home", str(home), "--no-open", "--solo-nomi"])
    assert rc == 0
    archivio = home / "Documenti" / ARCHIVIO
    out = archivio / "00_scan"
    log = (out / "AVVIO.log").read_text(encoding="utf-8")
    assert "NON TROVATA" in log and "ATTENZIONE" in log, log
    copie = list(archivio.rglob("*Dati compilati.txt"))
    assert len(copie) == 1 and "08_isa_redditi" in str(copie[0]), copie
    print("OK fallback: ARCHIVIO creato in Documenti con avviso, copia ISA eseguita")


def main():
    with tempfile.TemporaryDirectory() as td:
        caso_drive(Path(td))
        caso_fallback(Path(td))


if __name__ == "__main__":
    main()
