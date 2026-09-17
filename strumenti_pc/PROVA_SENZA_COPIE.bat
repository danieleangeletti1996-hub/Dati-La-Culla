@echo off
setlocal EnableExtensions
title Scansione PC La Culla - PROVA SENZA COPIE
cd /d "%~dp0"
echo Modalita' PROVA: nessuna copia. Vengono prodotti solo inventario e riepilogo (cartella 00_scan).
echo.
call "%~dp0AVVIA_SCANSIONE.bat" --dry-run %*
